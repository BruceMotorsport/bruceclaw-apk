#!/usr/bin/env python3
"""
BruceClaw Remote Phone Control Bot
Runs in Termux. HTTP server on port 8080.
Controls phone via input commands, screenshots, mic, calls.
Includes chat with MiMo brain on port 9999.
"""

import os
import sys
import json
import time
import subprocess
import threading
import base64
import socket
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote

PORT = 8080
MIMO_PORT = 9999
HOME = os.path.expanduser("~")

# ============ PHONE CONTROL ============

def run(cmd, timeout=10):
    """Run a shell command and return output."""
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.stdout + r.stderr
    except subprocess.TimeoutExpired:
        return "TIMEOUT"
    except Exception as e:
        return f"ERROR: {e}"

def screenshot():
    """Take screenshot, return base64 encoded PNG."""
    path = f"{HOME}/screen_{int(time.time())}.png"
    run(f"screencap -p {path}")
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        os.remove(path)
        return data
    return None

def tap(x, y):
    """Tap screen at coordinates."""
    return run(f"input tap {x} {y}")

def swipe(x1, y1, x2, y2, duration=300):
    """Swipe between two points."""
    return run(f"input swipe {x1} {y1} {x2} {y2} {duration}")

def type_text(text):
    """Type text. Handles special characters."""
    # Escape special shell characters
    escaped = text.replace("'", "'\\''")
    return run(f"input text '{escaped}'")

def press_key(key):
    """Press a key: home, back, enter, tab, delete, volumeup, volumedown."""
    key_map = {
        "home": "3", "back": "4", "call": "5", "endcall": "6",
        "power": "26", "camera": "27", "enter": "66", "delete": "67",
        "tab": "61", "space": "62", "up": "19", "down": "20",
        "left": "21", "right": "22", "volumeup": "24", "volumedown": "25",
        "menu": "82", "search": "84", "media_play_pause": "85",
        "media_stop": "86", "media_next": "87", "media_previous": "88",
    }
    code = key_map.get(key.lower(), key)
    return run(f"input keyevent {code}")

def scroll(direction):
    """Scroll up or down."""
    w, h = get_screen_size()
    cx = w // 2
    if direction == "down":
        return swipe(cx, int(h * 0.7), cx, int(h * 0.3), 400)
    else:
        return swipe(cx, int(h * 0.3), cx, int(h * 0.7), 400)

def get_screen_size():
    """Get screen dimensions."""
    out = run("wm size")
    # Output: "Physical size: 1080x2400"
    try:
        size = out.split(":")[-1].strip()
        w, h = size.split("x")
        return int(w), int(h)
    except:
        return 1080, 2400

def answer_call():
    """Answer incoming call."""
    return run("input keyevent 5")

def hangup_call():
    """Hang up current call."""
    return run("input keyevent 6")

def reject_call():
    """Reject incoming call."""
    return run("input keyevent 6")

def call_state():
    """Check if phone is in a call."""
    out = run("dumpsys telephony.registry | grep mCallState")
    return out.strip()

def record_audio(duration=5):
    """Record audio clip from mic."""
    path = f"{HOME}/mic_{int(time.time())}.wav"
    run(f"termux-microphone-record -l {duration} -f {path}", timeout=duration + 5)
    if os.path.exists(path):
        with open(path, "rb") as f:
            data = base64.b64encode(f.read()).decode()
        size = os.path.getsize(path)
        os.remove(path)
        return {"base64": data, "size": size, "path": path}
    return None

def open_app(app_name):
    """Open an app by name."""
    packages = {
        "chrome": "com.android.chrome",
        "camera": "com.android.camera",
        "settings": "com.android.settings",
        "calculator": "com.android.calculator2",
        "maps": "com.google.android.apps.maps",
        "youtube": "com.google.android.youtube",
        "whatsapp": "com.whatsapp",
        "telegram": "org.telegram.messenger",
        "gallery": "com.google.android.apps.photos",
        "files": "com.google.android.apps.nbu.files",
        "phone": "com.google.android.dialer",
        "contacts": "com.google.android.contacts",
        "messages": "com.google.android.apps.messaging",
        "play store": "com.android.vending",
    }
    pkg = packages.get(app_name.lower(), app_name)
    return run(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1")

def tts_speak(text):
    """Speak text using termux-tts-speak."""
    cleaned = text.replace("#", "").replace("*", "").replace("/", "")
    return run(f"termux-tts-speak '{cleaned}'")

def battery_status():
    """Get battery status."""
    out = run("termux-battery-status")
    try:
        d = json.loads(out)
        return f"{d.get('percentage', '?')}% at {d.get('voltage', 0)/1000:.1f}V"
    except:
        return out

def notification(text):
    """Send a notification."""
    return run(f"termux-notification -t 'BruceClaw' -c '{text}'")

def shell_exec(command):
    """Run any shell command."""
    return run(command, timeout=30)

def chat_with_mimo(message):
    """Send message to MiMo brain on port 9999 and get response."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(30)
        s.connect(("127.0.0.1", MIMO_PORT))
        # Read greeting
        s.recv(4096)
        # Send message
        s.sendall((message + "\n").encode())
        time.sleep(0.5)
        # Read response
        response = b""
        s.settimeout(15)
        while True:
            try:
                chunk = s.recv(4096)
                if not chunk:
                    break
                response += chunk
                # Check if we got a complete response
                text = response.decode(errors="ignore")
                if text.strip().endswith("you>") or text.strip().endswith("bot>"):
                    break
            except socket.timeout:
                break
        s.close()
        text = response.decode(errors="ignore").strip()
        # Clean up — remove prompts and extra whitespace
        lines = text.split("\n")
        clean = []
        for line in lines:
            line = line.strip()
            if line and not line.startswith("you>") and not line.startswith("bot>") and not line.startswith("~/"):
                clean.append(line)
        return "\n".join(clean) if clean else text
    except ConnectionRefusedError:
        return "ERROR: MiMo brain not running on port 9999. Start it with: cd ~/bruceclaw && python3 bruceclaw.py"
    except Exception as e:
        return f"ERROR: {e}"

# ============ HTTP SERVER ============

class BotHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = unquote(self.path)

        # === HTML UI ===
        if path == "/" or path == "/index.html":
            self.send_html(UI_HTML)
            return

        # === SCREENSHOT ===
        if path == "/screenshot":
            data = screenshot()
            if data:
                self.send_json({"status": "ok", "base64": data})
            else:
                self.send_json({"status": "error", "message": "screenshot failed"})
            return

        # === SCREEN SIZE ===
        if path == "/screen_size":
            w, h = get_screen_size()
            self.send_json({"status": "ok", "width": w, "height": h})
            return

        # === TAP ===
        if path.startswith("/tap/"):
            parts = path.split("/")
            if len(parts) >= 4:
                x, y = int(parts[2]), int(parts[3])
                tap(x, y)
                self.send_json({"status": "ok", "action": "tap", "x": x, "y": y})
            else:
                self.send_json({"status": "error", "message": "usage: /tap/x/y"})
            return

        # === SWIPE ===
        if path.startswith("/swipe/"):
            parts = path.split("/")
            if len(parts) >= 6:
                x1, y1, x2, y2 = int(parts[2]), int(parts[3]), int(parts[4]), int(parts[5])
                swipe(x1, y1, x2, y2)
                self.send_json({"status": "ok", "action": "swipe"})
            else:
                self.send_json({"status": "error", "message": "usage: /swipe/x1/y1/x2/y2"})
            return

        # === SCROLL ===
        if path.startswith("/scroll/"):
            direction = path.split("/")[2] if len(path.split("/")) > 2 else "down"
            scroll(direction)
            self.send_json({"status": "ok", "action": "scroll", "direction": direction})
            return

        # === PRESS KEY ===
        if path.startswith("/press/"):
            key = path.split("/")[2]
            press_key(key)
            self.send_json({"status": "ok", "action": "press", "key": key})
            return

        # === ANSWER CALL ===
        if path == "/answer":
            answer_call()
            self.send_json({"status": "ok", "action": "answer"})
            return

        # === HANGUP ===
        if path == "/hangup":
            hangup_call()
            self.send_json({"status": "ok", "action": "hangup"})
            return

        # === CALL STATE ===
        if path == "/call_state":
            state = call_state()
            self.send_json({"status": "ok", "state": state})
            return

        # === BATTERY ===
        if path == "/battery":
            bat = battery_status()
            self.send_json({"status": "ok", "battery": bat})
            return

        # === SCREEN TREE ===
        if path == "/screen_tree":
            # Dump UI hierarchy via uiautomator
            out = shell_exec("uiautomator dump /dev/tty 2>/dev/null || dumpsys activity top | grep -A 50 'View Hierarchy'")
            self.send_json({"status": "ok", "tree": out[:5000]})
            return

        # === OPEN APP ===
        if path.startswith("/open/"):
            app = path.split("/")[2]
            open_app(app)
            self.send_json({"status": "ok", "action": "open", "app": app})
            return

        # === SHELL ===
        if path.startswith("/shell/"):
            cmd = path[7:]  # Remove "/shell/"
            out = shell_exec(cmd)
            self.send_json({"status": "ok", "output": out[:3000]})
            return

        # === MIC ===
        if path.startswith("/mic/"):
            duration = int(path.split("/")[2]) if len(path.split("/")) > 2 else 5
            data = record_audio(duration)
            if data:
                self.send_json({"status": "ok", "size": data["size"]})
            else:
                self.send_json({"status": "error", "message": "recording failed"})
            return

        # === STATUS ===
        if path == "/status":
            w, h = get_screen_size()
            bat = battery_status()
            state = call_state()
            self.send_json({
                "status": "ok",
                "screen": f"{w}x{h}",
                "battery": bat,
                "call_state": state,
                "port": PORT,
            })
            return

        # === HOME ===
        if path == "/home":
            press_key("home")
            self.send_json({"status": "ok", "action": "home"})
            return

        # === BACK ===
        if path == "/back":
            press_key("back")
            self.send_json({"status": "ok", "action": "back"})
            return

        # === CHAT WITH MIMO ===
        if path == "/chat":
            # GET /chat returns the chat UI page
            self.send_html(CHAT_HTML)
            return

        # === 404 ===
        self.send_json({"status": "error", "message": f"Unknown endpoint: {path}"}, 404)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        path = unquote(self.path)

        try:
            data = json.loads(body) if body else {}
        except:
            data = {}

        # === TYPE TEXT ===
        if path == "/type":
            text = data.get("text", "")
            type_text(text)
            self.send_json({"status": "ok", "action": "type", "text": text})
            return

        # === TAP (JSON body) ===
        if path == "/tap":
            x = data.get("x", 0)
            y = data.get("y", 0)
            tap(x, y)
            self.send_json({"status": "ok", "action": "tap", "x": x, "y": y})
            return

        # === SHELL (JSON body) ===
        if path == "/shell":
            cmd = data.get("command", "")
            out = shell_exec(cmd)
            self.send_json({"status": "ok", "output": out[:3000]})
            return

        # === TTS ===
        if path == "/tts":
            text = data.get("text", "")
            tts_speak(text)
            self.send_json({"status": "ok", "action": "tts"})
            return

        # === CHAT WITH MIMO ===
        if path == "/chat":
            message = data.get("message", "").strip()
            if not message:
                self.send_json({"status": "error", "message": "No message"})
                return
            response = chat_with_mimo(message)
            self.send_json({"status": "ok", "reply": response})
            return

        # === NOTIFICATION ===
        if path == "/notify":
            text = data.get("text", "")
            notification(text)
            self.send_json({"status": "ok", "action": "notify"})
            return

        # === COMMAND (batch) ===
        if path == "/command":
            commands = data.get("commands", [])
            results = []
            for cmd in commands:
                action = cmd.get("action", "")
                if action == "tap":
                    r = tap(cmd["x"], cmd["y"])
                elif action == "swipe":
                    r = swipe(cmd["x1"], cmd["y1"], cmd["x2"], cmd["y2"])
                elif action == "type":
                    r = type_text(cmd["text"])
                elif action == "press":
                    r = press_key(cmd["key"])
                elif action == "scroll":
                    r = scroll(cmd.get("direction", "down"))
                elif action == "open":
                    r = open_app(cmd["app"])
                elif action == "shell":
                    r = shell_exec(cmd["command"])
                else:
                    r = f"Unknown: {action}"
                results.append({"action": action, "result": r[:200]})
            self.send_json({"status": "ok", "results": results})
            return

        self.send_json({"status": "error", "message": "Unknown POST endpoint"}, 404)

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def send_html(self, html):
        self.send_response(200)
        self.send_header("Content-Type", "text/html")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(html.encode())

    def log_message(self, *a):
        pass  # Silent logs

# ============ BUILT-IN UI ============

UI_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>BruceClaw</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:sans-serif;background:#0a0a0a;color:#fff;height:100vh;display:flex;flex-direction:column;overflow:hidden}
#hdr{background:#181818;padding:8px 12px;display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid #ff6600}
#hdr h1{font-size:20px;color:#ff6600}
#hdr .st{font-size:11px;color:#0f8;background:#1a1a2e;padding:3px 8px;border-radius:8px}
#screen{flex:1;overflow-y:auto;padding:8px;display:flex;flex-direction:column;gap:8px}
#screen img{width:100%;border-radius:8px;border:1px solid #333}
#ctl{padding:8px;background:#181818;border-top:2px solid #ff6600;display:flex;flex-wrap:wrap;gap:6px;justify-content:center}
.btn{background:#222;color:#ff6600;border:1px solid #ff6600;padding:8px 14px;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer}
.btn:active{background:#ff6600;color:#000}
.btn.big{flex:1;min-width:80px}
.log{font-size:12px;color:#0f8;padding:2px 8px;font-family:monospace}
#inp{display:flex;background:#181818;padding:6px;gap:4px}
#inp input{flex:1;background:#222;border:1px solid #444;color:#fff;padding:8px;border-radius:8px;font-size:16px}
#inp button{background:#ff6600;color:#fff;border:none;padding:8px 16px;border-radius:8px;font-weight:700}
</style>
</head>
<body>
<div id="hdr">
<h1>BRUCECLAW</h1>
<span class="st" id="status">Connecting...</span>
</div>
<div id="screen">
<div class="log">Tap SCREENSHOT to see phone screen. Tap anywhere on image to tap that point.</div>
</div>
<div id="ctl">
<button class="btn big" onclick="getScreenshot()">SCREENSHOT</button>
<button class="btn" onclick="send('/answer')">ANSWER</button>
<button class="btn" onclick="send('/hangup')">HANGUP</button>
<button class="btn" onclick="send('/home')">HOME</button>
<button class="btn" onclick="send('/back')">BACK</button>
<button class="btn" onclick="send('/scroll/up')">SCROLL UP</button>
<button class="btn" onclick="send('/scroll/down')">SCROLL DN</button>
<button class="btn" onclick="getMic()">MIC 5s</button>
<button class="btn" onclick="send('/battery')">BATTERY</button>
</div>
<div id="inp">
<input id="cmd" placeholder="Shell command...">
<button onclick="runShell()">RUN</button>
</div>
<script>
var imgEl=null,realW=0,realH=0;
function api(url,cb){fetch(url).then(r=>r.json()).then(d=>{document.getElementById("status").textContent="OK";if(cb)cb(d);}).catch(e=>{document.getElementById("status").textContent="ERROR";});}
function send(url){api(url,d=>log(JSON.stringify(d)));}
function log(t){var d=document.createElement("div");d.className="log";d.textContent="> "+t;document.getElementById("screen").appendChild(d);document.getElementById("screen").scrollTop=99999;}
function getScreenshot(){
api("/screen_size",function(s){realW=s.width;realH=s.height;});
api("/screenshot",function(d){
if(d.base64){
var s=document.getElementById("screen");
if(imgEl)imgEl.remove();
imgEl=document.createElement("img");
imgEl.src="data:image/png;base64,"+d.base64;
imgEl.onclick=function(e){
var r=imgEl.getBoundingClientRect();
var x=Math.round((e.clientX-r.left)/r.width*realW);
var y=Math.round((e.clientY-r.top)/r.height*realH);
api("/tap/"+x+"/"+y,function(r){log("Tapped "+x+","+y);});
};
s.appendChild(imgEl);
s.scrollTop=99999;
}else{log("Screenshot failed");}
});
}
function getMic(){api("/mic/5",function(d){log("Recorded: "+JSON.stringify(d));});}
function runShell(){
var c=document.getElementById("cmd").value.trim();
if(!c)return;
api("/shell/"+encodeURIComponent(c),function(d){log(d.output||JSON.stringify(d));});
document.getElementById("cmd").value="";
}
api("/status",function(d){document.getElementById("status").textContent="Connected — "+d.screen+" — "+d.battery;});
</script>
</body>
</html>"""

CHAT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>BruceClaw Chat</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:sans-serif;background:#0a0a0a;color:#fff;height:100vh;display:flex;flex-direction:column;overflow:hidden}
#hdr{background:#181818;padding:10px 12px;display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid #ff6600}
#hdr h1{font-size:20px;color:#ff6600}
.st{font-size:11px;color:#0f8;background:#1a1a2e;padding:3px 8px;border-radius:8px}
#chat{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px}
.m{max-width:85%;padding:10px 14px;border-radius:12px;font-size:16px;line-height:1.4;white-space:pre-wrap;word-wrap:break-word}
.mu{align-self:flex-end;background:#ff6600;color:#fff}
.mb{align-self:flex-start;background:#222;color:#eee;border:1px solid #333}
.me{border-color:#f44;color:#f88;font-size:13px}
.mi{border-color:#0f8;color:#0f8;font-size:13px}
#inp{padding:8px;background:#181818;border-top:2px solid #ff6600;display:flex;gap:6px}
#inp input{flex:1;background:#222;border:1px solid #444;color:#fff;padding:10px;border-radius:10px;font-size:16px}
#inp button{background:#ff6600;color:#fff;border:none;padding:10px 18px;border-radius:10px;font-size:15px;font-weight:700}
#nav{display:flex;background:#111;border-top:1px solid #333}
#nav a{flex:1;text-align:center;padding:10px;color:#666;text-decoration:none;font-size:13px;font-weight:700}
#nav a.on{color:#ff6600}
</style>
</head>
<body>
<div id="hdr">
<h1>BRUCECLAW</h1>
<span class="st" id="status">Connecting...</span>
</div>
<div id="chat">
<div class="mb">Talk to MiMo. Type anything below.</div>
</div>
<div id="inp">
<input id="msg" placeholder="Message to MiMo..." onkeydown="if(event.key==='Enter')sendMsg()">
<button onclick="sendMsg()">SEND</button>
</div>
<div id="nav">
<a href="/" class="">PHONE</a>
<a href="/chat" class="on">CHAT</a>
</div>
<script>
function addMsg(t,c){
var d=document.createElement("div");
d.className="m "+c;
d.textContent=t;
document.getElementById("chat").appendChild(d);
document.getElementById("chat").scrollTop=99999;
}
function sendMsg(){
var m=document.getElementById("msg").value.trim();
if(!m)return;
addMsg(m,"mu");
document.getElementById("msg").value="";
addMsg("Thinking...","mi");
fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:m})})
.then(r=>r.json())
.then(d=>{
var chat=document.getElementById("chat");
if(chat.lastChild)chat.removeChild(chat.lastChild);
if(d.reply){addMsg(d.reply,"mb");}
else{addMsg("No response","me");}
})
.catch(e=>{
var chat=document.getElementById("chat");
if(chat.lastChild)chat.removeChild(chat.lastChild);
addMsg("Error: "+e,"me");
});
}
fetch("/status").then(r=>r.json()).then(d=>{
document.getElementById("status").textContent="Connected — "+d.screen;
}).catch(e=>{
document.getElementById("status").textContent="Offline";
document.getElementById("status").className="st";
document.getElementById("status").style.color="#f44";
});
</script>
</body>
</html>"""

# ============ MAIN ============

if __name__ == "__main__":
    print("=" * 50)
    print("  BRUCECLAW REMOTE PHONE CONTROL")
    print(f"  Port: {PORT}")
    print(f"  UI: http://localhost:{PORT}")
    print(f"  Screen: {get_screen_size()}")
    print("=" * 50)
    print()
    print("Endpoints:")
    print("  GET /screenshot     — Screenshot (base64)")
    print("  GET /tap/x/y        — Tap coordinates")
    print("  GET /swipe/x1/y1/x2/y2 — Swipe")
    print("  GET /scroll/up|down — Scroll")
    print("  GET /press/key      — Press key")
    print("  GET /answer         — Answer call")
    print("  GET /hangup         — Hang up")
    print("  GET /mic/5          — Record audio")
    print("  GET /battery        — Battery status")
    print("  GET /open/appname   — Open app")
    print("  GET /shell/cmd      — Run shell command")
    print("  GET /status         — Full status")
    print("  POST /type {text}   — Type text")
    print("  POST /tts {text}    — Speak text")
    print()
    print("Open http://localhost:8080 on any device on same network")
    print()

    server = HTTPServer(("0.0.0.0", PORT), BotHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.server_close()
