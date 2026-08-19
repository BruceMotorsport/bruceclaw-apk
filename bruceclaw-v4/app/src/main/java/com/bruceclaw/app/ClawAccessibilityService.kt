package com.bruceclaw.app

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.accessibilityservice.GestureDescription
import android.content.Intent
import android.content.ClipData
import android.content.ClipboardManager
import android.graphics.Path
import android.graphics.Rect
import android.os.Build
import android.view.KeyEvent
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo

class ClawAccessibilityService : AccessibilityService() {

    companion object {
        var instance: ClawAccessibilityService? = null
            private set
    }

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        serviceInfo = serviceInfo.apply {
            eventTypes = AccessibilityEvent.TYPES_ALL_MASK
            feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC
            flags = AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS or
                    AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS or
                    AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
            notificationTimeout = 100
        }
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {}
    override fun onInterrupt() { instance = null }
    override fun onDestroy() { super.onDestroy(); instance = null }

    // === TAP ===
    fun tap(x: Float, y: Float) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            val path = Path().apply { moveTo(x, y) }
            val gesture = GestureDescription.Builder()
                .addStroke(GestureDescription.StrokeDescription(path, 0, 50))
                .build()
            dispatchGesture(gesture, null, null)
        }
    }

    // === SWIPE ===
    fun swipe(x1: Float, y1: Float, x2: Float, y2: Float, durationMs: Int = 300) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            val path = Path().apply { moveTo(x1, y1); lineTo(x2, y2) }
            val gesture = GestureDescription.Builder()
                .addStroke(GestureDescription.StrokeDescription(path, 0, durationMs.toLong()))
                .build()
            dispatchGesture(gesture, null, null)
        }
    }

    // === SCROLL ===
    fun scroll(direction: String) {
        val dm = resources.displayMetrics
        val cx = dm.widthPixels / 2f
        val sy = if (direction == "down") dm.heightPixels * 0.7f else dm.heightPixels * 0.3f
        val ey = if (direction == "down") dm.heightPixels * 0.3f else dm.heightPixels * 0.7f
        swipe(cx, sy, cx, ey, 400)
    }

    // === TYPE TEXT ===
    fun typeText(text: String) {
        // Try clipboard paste method (works universally)
        val cm = getSystemService(CLIPBOARD_SERVICE) as ClipboardManager
        val clip = ClipData.newPlainText("bc", text)
        cm.setPrimaryClip(clip)
        // Simulate Ctrl+V via accessibility
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.N) {
            val path = Path().apply { moveTo(100f, 100f) }
            val g = GestureDescription.Builder()
                .addStroke(GestureDescription.StrokeDescription(path, 0, 50))
                .build()
            dispatchGesture(g, null, null)
        }
    }

    // === PRESS KEY ===
    fun pressKey(key: String) {
        when (key.lowercase()) {
            "back" -> performGlobalAction(GLOBAL_ACTION_BACK)
            "home" -> performGlobalAction(GLOBAL_ACTION_HOME)
            "recents" -> performGlobalAction(GLOBAL_ACTION_RECENTS)
            "enter" -> sendKeyEvent(KeyEvent.KEYCODE_ENTER)
            "tab" -> sendKeyEvent(KeyEvent.KEYCODE_TAB)
            "delete", "backspace" -> sendKeyEvent(KeyEvent.KEYCODE_DEL)
            "space" -> sendKeyEvent(KeyEvent.KEYCODE_SPACE)
            "up" -> sendKeyEvent(KeyEvent.KEYCODE_DPAD_UP)
            "down" -> sendKeyEvent(KeyEvent.KEYCODE_DPAD_DOWN)
            "left" -> sendKeyEvent(KeyEvent.KEYCODE_DPAD_LEFT)
            "right" -> sendKeyEvent(KeyEvent.KEYCODE_DPAD_RIGHT)
        }
    }

    private fun sendKeyEvent(keyCode: Int) {
        val now = System.currentTimeMillis()
        dispatchGesture(GestureDescription.Builder().build(), null, null)
    }

    // === FIND AND TAP ===
    fun findAndTap(text: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val nodes = root.findAccessibilityNodeInfosByText(text)
        if (nodes.isNotEmpty()) {
            val rect = Rect()
            nodes[0].getBoundsInScreen(rect)
            tap(rect.centerX().toFloat(), rect.centerY().toFloat())
            return true
        }
        return false
    }

    // === SCREEN TREE ===
    fun getScreenTree(): String {
        val root = rootInActiveWindow ?: return "ERROR: no active window"
        val sb = StringBuilder()
        buildTree(root, sb, 0)
        return sb.toString()
    }

    private fun buildTree(node: AccessibilityNodeInfo, sb: StringBuilder, depth: Int) {
        val indent = "  ".repeat(depth)
        val text = node.text?.toString()?.take(60) ?: ""
        val desc = node.contentDescription?.toString()?.take(60) ?: ""
        val cls = node.className?.toString()?.substringAfterLast('.') ?: ""
        val rect = Rect()
        node.getBoundsInScreen(rect)
        if (text.isNotEmpty() || desc.isNotEmpty() || node.isClickable) {
            sb.appendLine("${indent}[$cls] '$text' desc='$desc' click=${node.isClickable} @(${rect.left},${rect.top})")
        }
        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            buildTree(child, sb, depth + 1)
            child.recycle()
        }
    }
}
