package com.bruceclaw.app

import android.Manifest
import android.annotation.SuppressLint
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.BitmapFactory
import android.net.Uri
import android.os.*
import android.provider.MediaStore
import android.util.Base64
import android.util.Log
import android.webkit.*
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import androidx.core.content.FileProvider
import org.json.JSONObject
import java.io.*
import java.net.ServerSocket
import java.net.Socket
import java.text.SimpleDateFormat
import java.util.*
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private var bridgeServer: ServerSocket? = null
    private var bridgeRunning = false
    private var photoUri: Uri? = null
    private val handler = Handler(Looper.getMainLooper())

    companion object {
        const val TAG = "BruceClaw"
        const val BRIDGE_PORT = 9999
        const val CAMERA_PERMISSION = 100
        const val FILE_CHOOSER = 101
    }

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        webView = WebView(this)
        setContentView(webView)

        webView.settings.apply {
            javaScriptEnabled = true
            domStorageEnabled = true
            allowFileAccess = true
            allowContentAccess = true
            mediaPlaybackRequiresUserGesture = false
            mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW
            loadWithOverviewMode = true
            useWideViewPort = true
            setSupportMultipleWindows(false)
        }

        webView.webChromeClient = object : WebChromeClient() {
            override fun onShowFileChooser(view: WebView, callback: ValueCallback<Array<Uri>>, params: FileChooserParams): Boolean {
                val intent = params.createIntent()
                try {
                    startActivityForResult(intent, FILE_CHOOSER)
                } catch (e: Exception) {
                    Log.e(TAG, "File chooser error: ${e.message}")
                    return false
                }
                return true
            }
        }

        webView.webViewClient = WebViewClient()

        // Register JS interface
        webView.addJavascriptInterface(Tools(), "Tools")

        // Load the chat UI from assets
        webView.loadUrl("file:///android_asset/index.html")

        // Start Termux relay bridge on port 9999
        startBridge()
    }

    // ============ KOTLIN BRIDGE — Called from JavaScript ============
    inner class Tools {

        @JavascriptInterface
        fun callAI(provider: String, apiKey: String, endpoint: String, model: String, messagesJson: String): String {
            return try {
                val url = endpoint
                val body = JSONObject().apply {
                    put("model", model)
                    put("messages", org.json.JSONArray(messagesJson))
                    put("temperature", 0.7)
                    put("max_tokens", 1024)
                }

                val conn = java.net.URL(url).openConnection() as java.net.HttpURLConnection
                conn.requestMethod = "POST"
                conn.setRequestProperty("Content-Type", "application/json")
                conn.setRequestProperty("Authorization", "Bearer $apiKey")
                conn.setRequestProperty("User-Agent", "BruceClaw/4.0")
                conn.doOutput = true
                conn.connectTimeout = 30000
                conn.readTimeout = 30000
                conn.outputStream.write(body.toString().toByteArray())

                val responseCode = conn.responseCode
                val stream = if (responseCode in 200..299) conn.inputStream else conn.errorStream
                val response = stream.bufferedReader().readText()
                conn.disconnect()

                val json = JSONObject(response)
                if (json.has("choices")) {
                    json.getJSONArray("choices").getJSONObject(0)
                        .getJSONObject("message").getString("content")
                } else if (json.has("candidates")) {
                    json.getJSONArray("candidates").getJSONObject(0)
                        .getJSONObject("content").getJSONArray("parts")
                        .getJSONObject(0).getString("text")
                } else {
                    "Error: Unexpected response format"
                }
            } catch (e: Exception) {
                "Error: ${e.message}"
            }
        }

        @JavascriptInterface
        fun ttsSpeak(text: String) {
            handler.post {
                val cleaned = text.replace(Regex("[#/\\\\@<>{}|~`\\u{1F000}-\\u{1FFFF}]"), "")
                val tts = android.speech.tts.TextToSpeech(this@MainActivity) { status ->
                    if (status == android.speech.tts.TextToSpeech.SUCCESS) {
                        tts?.speak(cleaned, android.speech.tts.TextToSpeech.QUEUE_FLUSH, null, "ttsUtterance")
                    }
                }
            }
        }

        private var tts: android.speech.tts.TextToSpeech? = null
        private var ttsInitialized = false

        @JavascriptInterface
        fun ttsStop() {
            handler.post {
                tts?.stop()
            }
        }

        @JavascriptInterface
        fun shell(command: String): String {
            return try {
                val process = Runtime.getRuntime().exec(arrayOf("sh", "-c", command))
                val output = process.inputStream.bufferedReader().readText()
                val errors = process.errorStream.bufferedReader().readText()
                process.waitFor(10, java.util.concurrent.TimeUnit.SECONDS)
                (output.ifEmpty { errors }).take(2000)
            } catch (e: Exception) {
                "Error: ${e.message}"
            }
        }

        @JavascriptInterface
        fun takePhoto(): String {
            return try {
                val timeStamp = SimpleDateFormat("yyyyMMdd_HHmmss", Locale.getDefault()).format(Date())
                val photoFile = File(cacheDir, "IMG_$timeStamp.jpg")
                photoUri = FileProvider.getUriForFile(
                    this@MainActivity,
                    "${packageName}.fileprovider",
                    photoFile
                )
                val intent = Intent(MediaStore.ACTION_IMAGE_CAPTURE)
                intent.putExtra(MediaStore.EXTRA_OUTPUT, photoUri)
                startActivityForResult(intent, CAMERA_PERMISSION)
                photoFile.absolutePath
            } catch (e: Exception) {
                "Error: ${e.message}"
            }
        }

        @JavascriptInterface
        fun getScreenSize(): String {
            val dm = resources.displayMetrics
            return "${dm.widthPixels}x${dm.heightPixels}"
        }

        @JavascriptInterface
        fun screenshot(): String {
            return try {
                val process = Runtime.getRuntime().exec(arrayOf("screencap", "-p", "/sdcard/screen.png"))
                process.waitFor(5, java.util.concurrent.TimeUnit.SECONDS)
                val file = File("/sdcard/screen.png")
                if (file.exists()) {
                    val bytes = file.readBytes()
                    Base64.encodeToString(bytes, Base64.NO_WRAP)
                } else {
                    "Error: screenshot failed"
                }
            } catch (e: Exception) {
                "Error: ${e.message}"
            }
        }

        @JavascriptInterface
        fun tap(x: Int, y: Int) {
            val service = ClawAccessibilityService.instance
            service?.tap(x.toFloat(), y.toFloat())
        }

        @JavascriptInterface
        fun swipe(x1: Int, y1: Int, x2: Int, y2: Int, duration: Int) {
            val service = ClawAccessibilityService.instance
            service?.swipe(x1.toFloat(), y1.toFloat(), x2.toFloat(), y2.toFloat(), duration)
        }

        @JavascriptInterface
        fun scroll(direction: String) {
            val service = ClawAccessibilityService.instance
            service?.scroll(direction)
        }

        @JavascriptInterface
        fun pressKey(key: String) {
            val service = ClawAccessibilityService.instance
            service?.pressKey(key)
        }

        @JavascriptInterface
        fun findAndTap(text: String): Boolean {
            val service = ClawAccessibilityService.instance
            return service?.findAndTap(text) ?: false
        }

        @JavascriptInterface
        fun screenTree(): String {
            val service = ClawAccessibilityService.instance
            return service?.getScreenTree() ?: "ERROR: Accessibility service not running"
        }

        @JavascriptInterface
        fun sendToTermux(message: String) {
            // Send message to Termux Python bot via bridge
            thread {
                try {
                    val socket = Socket("127.0.0.1", BRIDGE_PORT)
                    val output = socket.getOutputStream().bufferedWriter()
                    output.write(message)
                    output.newLine()
                    output.flush()
                    val input = socket.getInputStream().bufferedReader()
                    val response = input.readLine() ?: ""
                    socket.close()
                    handler.post {
                        webView.evaluateJavascript("onTermuxReply('${response.replace("'", "\\'")}')", null)
                    }
                } catch (e: Exception) {
                    handler.post {
                        webView.evaluateJavascript("onTermuxReply('Error: ${e.message}')", null)
                    }
                }
            }
        }
    }

    // ============ TERMUX RELAY BRIDGE ============
    private fun startBridge() {
        bridgeRunning = true
        thread {
            try {
                bridgeServer = ServerSocket(BRIDGE_PORT)
                Log.d(TAG, "Bridge started on port $BRIDGE_PORT")
                while (bridgeRunning) {
                    val client = bridgeServer?.accept() ?: break
                    thread { handleBridgeClient(client) }
                }
            } catch (e: Exception) {
                Log.e(TAG, "Bridge error: ${e.message}")
            }
        }
    }

    private fun handleBridgeClient(client: Socket) {
        try {
            val input = client.getInputStream().bufferedReader()
            val output = client.getOutputStream().bufferedWriter()
            val line = input.readLine() ?: return
            Log.d(TAG, "Bridge received: ${line.take(100)}")
            // Forward to WebView
            handler.post {
                webView.evaluateJavascript("onTermuxMessage('${line.replace("'", "\\'")}')", null)
            }
            output.write("OK\n")
            output.flush()
            client.close()
        } catch (e: Exception) {
            Log.e(TAG, "Bridge client error: ${e.message}")
        }
    }

    // ============ LIFECYCLE ============
    override fun onBackPressed() {
        if (webView.canGoBack()) {
            webView.goBack()
        } else {
            super.onBackPressed()
        }
    }

    override fun onDestroy() {
        bridgeRunning = false
        try { bridgeServer?.close() } catch (_: Exception) {}
        super.onDestroy()
    }

    override fun onActivityResult(requestCode: Int, resultCode: Int, data: Intent?) {
        super.onActivityResult(requestCode, resultCode, data)
        if (requestCode == FILE_CHOOSER && resultCode == RESULT_OK) {
            val result = data?.data ?: return
            webView.evaluateJavascript("onFileSelected('${result}')", null)
        }
    }
}
