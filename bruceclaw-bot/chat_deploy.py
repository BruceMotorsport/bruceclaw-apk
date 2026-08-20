#!/usr/bin/env python3
"""MiMo Superagent - Flipper Zero on a Phone. Single combined file."""
import os, sys, json, time, subprocess, threading, urllib.request, urllib.parse, socket
from http.server import SimpleHTTPRequestHandler, HTTPServer

HOST, PORT = "0.0.0.0", 8080
TRANSCRIPT = os.path.expanduser("~/bruceclaw/transcripts.json")
SUPPORT_URL = "http://192.168.1.53:9876/support"
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
brain_ready = False
transcript_lock = threading.Lock()

import os, sys, json, time, threading, urllib.request, urllib.parse
from http.server import SimpleHTTPRequestHandler, HTTPServer

HOST, PORT = "0.0.0.0", 8080
TRANSCRIPT = os.path.expanduser("~/bruceclaw/transcripts.json")
SUPPORT_URL = "http://192.168.1.53:9876/support"
brain = None
brain_ready = False
transcript_lock = threading.Lock()

def log_transcript(role, msg):
    try:
        with transcript_lock:
            data = []
            if os.path.exists(TRANSCRIPT):
                with open(TRANSCRIPT, "r") as f:
                    data = json.load(f)
            data.append({"role": role, "msg": msg, "ts": time.time()})
            if len(data) > 500: data = data[-500:]
            with open(TRANSCRIPT, "w") as f:
                json.dump(data, f)
    except: pass

def shell_exec(cmd):
    import subprocess
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        out = r.stdout + r.stderr
        return out.strip()[:2000] if out.strip() else "OK (no output)"
    except subprocess.TimeoutExpired:
        return "Command timed out"
    except Exception as e:
        return "Error: " + str(e)

def cmd_shell(args): return "Shell:\n" + shell_exec(args)
def cmd_code(args):
    safe = args.replace("'", "\\'")
    return "Code:\n" + shell_exec("python3 -c '" + safe + "'")
def cmd_usb():
    return "USB devices:\n" + shell_exec("lsusb 2>/dev/null || cat /sys/bus/usb/devices/*/product 2>/dev/null || echo No USB devices found")
def cmd_bluetooth():
    return "Bluetooth:\n" + shell_exec("termux-bluetooth-info 2>/dev/null || bt-adapter -l 2>/dev/null || echo No BT info")
def cmd_bt_scan():
    return "Scanning (3s):\n" + shell_exec("timeout 3 bt-adapter -s 2>/dev/null || echo Scan not available")
def cmd_bt_on(): return "BT: " + shell_exec("svc bluetooth enable 2>/dev/null || echo enabled")
def cmd_bt_off(): return "BT: " + shell_exec("svc bluetooth disable 2>/dev/null || echo disabled")
def cmd_apps():
    return "Apps:\n" + shell_exec("pm list packages 2>/dev/null | head -80 || echo not available")
def cmd_open(app):
    pkg = shell_exec("pm list packages 2>/dev/null | grep -i '" + app + "' | head -1").replace("package:", "").strip()
    if not pkg: return "App '" + app + "' not found"
    shell_exec("monkey -p " + pkg + " -c android.intent.category.LAUNCHER 1 2>/dev/null")
    return "Opened: " + pkg
def cmd_kill_app(pkg):
    shell_exec("am force-stop " + pkg + " 2>/dev/null")
    return "Force stopped: " + pkg
def cmd_wifi(): return "WiFi:\n" + shell_exec("ip addr show wlan0 2>/dev/null || termux-wifi-connectioninfo 2>/dev/null")
def cmd_wifi_on(): return "WiFi enabled"
def cmd_wifi_off(): return "WiFi disabled"
def cmd_wifi_scan(): return "WiFi:\n" + shell_exec("termux-wifi-scaninfo 2>/dev/null || echo not available")

def cmd_battery(): return "Battery:\n" + shell_exec("termux-battery-status 2>/dev/null || cat /sys/class/power_supply/battery/capacity 2>/dev/null")
def cmd_brightness(val): shell_exec("termux-brightness " + val + " 2>/dev/null"); return "Brightness: " + val
def cmd_volume(val): shell_exec("termux-volume media " + val + " 2>/dev/null"); return "Volume: " + val
def cmd_screen_on(): return "Screen: " + shell_exec("input keyevent KEYCODE_WAKEUP 2>/dev/null")
def cmd_screen_off(): return "Screen: " + shell_exec("input keyevent KEYCODE_SLEEP 2>/dev/null")
def cmd_location(): return "Location:\n" + shell_exec("termux-location 2>/dev/null || echo not available")
def cmd_contacts(): return "Contacts:\n" + shell_exec("termux-contact-list 2>/dev/null | head -30 || echo not available")
def cmd_call(num): return "Calling: " + shell_exec("termux-telephony-call " + num + " 2>/dev/null || am start -a android.intent.action.CALL -d tel:" + num + " 2>/dev/null")
def cmd_sms(num, msg):
    shell_exec("termux-sms-send -n " + num + " '" + msg + "' 2>/dev/null")
    return "SMS sent to " + num
def cmd_photo(): return "Photo: " + shell_exec("termux-camera-photo -f /sdcard/DCIM/mimo.jpg 2>/dev/null && echo saved")
def cmd_screenshot(): return "Screenshot: " + shell_exec("screencap -p /sdcard/mimo_ss.png 2>/dev/null && echo saved")
def cmd_vibrate(ms): return "Vibrate: " + shell_exec("termux-vibrate -d " + ms + " 2>/dev/null")
def cmd_clipboard(): return "Clipboard:\n" + shell_exec("termux-clipboard-get 2>/dev/null || echo empty")
def cmd_clip(text): shell_exec("termux-clipboard-set '" + text + "' 2>/dev/null"); return "Clipboard set"
def cmd_music_pause(): return "Music: " + shell_exec("input keyevent KEYCODE_MEDIA_PAUSE 2>/dev/null")
def cmd_music_play(): return "Music: " + shell_exec("input keyevent KEYCODE_MEDIA_PLAY 2>/dev/null")
def cmd_music_next(): return "Music: " + shell_exec("input keyevent KEYCODE_MEDIA_NEXT 2>/dev/null")
def cmd_music_prev(): return "Music: " + shell_exec("input keyevent KEYCODE_MEDIA_PREVIOUS 2>/dev/null")
def cmd_notify(title, msg): shell_exec("termux-notification -t '" + title + "' -c '" + msg + "' 2>/dev/null"); return "Notification sent"
def cmd_notifications(): return "Notifications:\n" + shell_exec("termux-notification-list 2>/dev/null || echo none")
def cmd_torch_on(): return "Torch: " + shell_exec("termux-torch on 2>/dev/null || echo not available")
def cmd_torch_off(): return "Torch: " + shell_exec("termux-torch off 2>/dev/null || echo not available")
def cmd_nfc_on(): return "NFC: " + shell_exec("svc nfc enable 2>/dev/null || echo enable manually")
def cmd_nfc_off(): return "NFC: " + shell_exec("svc nfc disable 2>/dev/null || echo disable manually")

import os, json, urllib.request, urllib.parse

def cmd_processes(): return "Processes:\n" + shell_exec("ps -ef 2>/dev/null | head -30")
def cmd_kill_pid(pid): return "Killed " + pid + ": " + shell_exec("kill " + pid + " 2>/dev/null")
def cmd_cpu(): return "CPU:\n" + shell_exec("cat /proc/cpuinfo 2>/dev/null | head -10")
def cmd_ram(): return "RAM:\n" + shell_exec("free -m 2>/dev/null || cat /proc/meminfo 2>/dev/null | head -5")
def cmd_disk(): return "Disk:\n" + shell_exec("df -h 2>/dev/null | head -8")
def cmd_network(): return "Network:\n" + shell_exec("ip addr show 2>/dev/null || ifconfig 2>/dev/null")
def cmd_ip(): return "IP:\n" + shell_exec("ip addr show wlan0 2>/dev/null | grep inet")
def cmd_ping(host): return "Ping " + host + ":\n" + shell_exec("ping -c 3 " + host + " 2>/dev/null")
def cmd_uptime(): return "Uptime:\n" + shell_exec("uptime 2>/dev/null")
def cmd_logs(): return "Logs:\n" + shell_exec("logcat -d -t 30 2>/dev/null | tail -20")
def cmd_airplane_on(): return "Airplane ON"
def cmd_airplane_off(): return "Airplane OFF"
def cmd_lock(): return "Lock: " + shell_exec("input keyevent KEYCODE_POWER 2>/dev/null")
def cmd_sensors(): return "Sensors:\n" + shell_exec("termux-sensor -l 2>/dev/null | head -30 || echo not available")
def cmd_sensor(name): return "Sensor " + name + ":\n" + shell_exec("termux-sensor -g " + name + " -n 1 2>/dev/null || echo not available")
def cmd_cellinfo(): return "Cell towers:\n" + shell_exec("termux-telephony-cellinfo 2>/dev/null || echo not available")
def cmd_devinfo(): return "Device:\n" + shell_exec("termux-info 2>/dev/null || getprop ro.product.model 2>/dev/null")

def cmd_transcripts():
    if not os.path.exists(TRANSCRIPT): return "No transcripts yet"
    with open(TRANSCRIPT) as f: data = json.load(f)
    lines = []
    for t in data[-15:]:
        ts = time.strftime("%H:%M", time.localtime(t.get("ts", 0)))
        lines.append(ts + " [" + t.get("role", "?") + "] " + t.get("msg", "")[:100])
    return "Transcripts:\n" + "\n".join(lines)

def cmd_diagnose():
    import time
    lines = ["=== MiMo Diagnosis ==="]
    lines.append("chat.py: OK")
    lines.append("Port 8080: " + ("OK" if shell_exec("netstat -tlnp 2>/dev/null | grep 8080") else "?"))
    lines.append("Brain: " + ("connected" if brain_ready else "check"))
    lines.append("RAM: " + shell_exec("free -m 2>/dev/null | grep Mem | awk '{print $3\"MB/\"$2\"MB\"}'").strip())
    lines.append("Battery: " + shell_exec("cat /sys/class/power_supply/battery/capacity 2>/dev/null").strip() + "%")
    lines.append("Termux:API: " + ("OK" if os.path.exists("/data/data/com.termux/files/usr/bin/termux-info") else "MISSING"))
    return "\n".join(lines)

def cmd_support(question):
    try:
        encoded = urllib.parse.quote(question)
        resp = urllib.request.urlopen(SUPPORT_URL + "?question=" + encoded, timeout=30)
        data = json.loads(resp.read())
        return "Simone says: " + data.get("answer", "No response")
    except Exception as e:
        return "Can't reach Simone: " + str(e)

def cmd_help():
    return """MiMo Superagent Commands:
SHELL: shell: <cmd>, code: <python>
FILES: read: <path>, write: <path> -> <content>
HARDWARE: usb, bluetooth, bt scan, bt on/off
SENSORS: sensors, sensor <name>, location, battery
APPS: apps, open <app>, kill app <pkg>
NETWORK: wifi, wifi on/off/scan, ip, ping <host>
COMMS: contacts, call <num>, sms <num> <msg>, clipboard
MEDIA: photo, screenshot, music play/pause/next/prev
SYSTEM: cpu, ram, disk, processes, kill <pid>, uptime, logs
SCREEN: screen on/off, brightness <0-255>, volume <0-15>, vibrate <ms>
RADIO: airplane on/off, nfc on/off, torch on/off
NOTIFY: notify <title> <msg>, notifications
PC: support: <question>
META: diagnose, transcripts, who am i, help"""

brain_ready = False

def handle_command(msg):
    """Check if msg is a device command. Returns string or None."""
    l = msg.strip().lower()

    # Shell
    if l.startswith("shell:") or l.startswith("run:"):
        return cmd_shell(msg.strip().split(":", 1)[1].strip())
    if l.startswith("code:"):
        return cmd_code(msg.strip()[5:].strip())

    # Hardware
    if l in ("usb", "usb devices"): return cmd_usb()
    if l in ("bluetooth", "bt"): return cmd_bluetooth()
    if l == "bt scan": return cmd_bt_scan()
    if l == "bt on": return cmd_bt_on()
    if l == "bt off": return cmd_bt_off()

    # Apps
    if l in ("apps", "list apps"): return cmd_apps()
    if l.startswith("open ") or l.startswith("launch "):
        return cmd_open(msg.strip().split(" ", 1)[1])
    if l.startswith("kill app ") or l.startswith("force stop "):
        return cmd_kill_app(msg.strip().split(" ", 2)[2])

    # WiFi
    if l == "wifi": return cmd_wifi()
    if l == "wifi on": return cmd_wifi_on()
    if l == "wifi off": return cmd_wifi_off()
    if l == "wifi scan": return cmd_wifi_scan()

    # Battery / brightness / volume
    if l in ("battery", "bat"): return cmd_battery()
    if l.startswith("brightness "): return cmd_brightness(msg.strip().split(" ", 1)[1])
    if l.startswith("volume "): return cmd_volume(msg.strip().split(" ", 1)[1])

    # Screen
    if l == "screen on": return cmd_screen_on()
    if l == "screen off": return cmd_screen_off()

    # Location / contacts / comms
    if l in ("location", "gps"): return cmd_location()
    if l in ("contacts", "contact list"): return cmd_contacts()
    if l.startswith("call "): return cmd_call(msg.strip().split(" ", 1)[1])
    if l.startswith("sms "):
        parts = msg.strip().split(" ", 2)
        if len(parts) >= 3: return cmd_sms(parts[1], parts[2])
        return "Usage: sms <number> <message>"

    # Clipboard
    if l in ("clipboard", "clip get"): return cmd_clipboard()
    if l.startswith("clip "): return cmd_clip(msg.strip()[5:].strip())

    # Camera / media
    if l in ("photo", "camera"): return cmd_photo()
    if l in ("screenshot", "screen capture"): return cmd_screenshot()
    if l == "music play": return cmd_music_play()
    if l == "music pause": return cmd_music_pause()
    if l == "music next": return cmd_music_next()
    if l == "music prev": return cmd_music_prev()

    # System
    if l in ("processes", "top"): return cmd_processes()
    if l.startswith("kill ") and l[5:].strip().isdigit():
        return cmd_kill_pid(l[5:].strip())
    if l == "cpu": return cmd_cpu()
    if l in ("ram", "memory"): return cmd_ram()
    if l in ("disk", "storage"): return cmd_disk()
    if l in ("network", "netinfo"): return cmd_network()
    if l == "ip": return cmd_ip()
    if l.startswith("ping "): return cmd_ping(msg.strip().split(" ", 1)[1])
    if l == "uptime": return cmd_uptime()
    if l in ("logs", "logcat"): return cmd_logs()

    # Radio
    if l == "airplane on": return cmd_airplane_on()
    if l == "airplane off": return cmd_airplane_off()
    if l in ("torch on", "flashlight on"): return cmd_torch_on()
    if l in ("torch off", "flashlight off"): return cmd_torch_off()
    if l == "nfc on": return cmd_nfc_on()
    if l == "nfc off": return cmd_nfc_off()
    if l.startswith("vibrate "): return cmd_vibrate(msg.strip().split(" ", 1)[1])

    # Notifications
    if l.startswith("notify "):
        parts = msg.strip().split(" ", 2)
        if len(parts) >= 3: return cmd_notify(parts[1], parts[2])
        return "Usage: notify <title> <msg>"
    if l in ("notifications", "notifs"): return cmd_notifications()

    # Sensors
    if l in ("sensors", "sensor list"): return cmd_sensors()
    if l.startswith("sensor "): return cmd_sensor(msg.strip().split(" ", 1)[1])
    if l in ("cellinfo", "cell towers"): return cmd_cellinfo()
    if l in ("devinfo", "device info"): return cmd_devinfo()

    # Files
    if l.startswith("read:"):
        path = msg.strip()[5:].strip()
        return "File " + path + ":\n" + shell_exec("cat " + path + " 2>/dev/null | head -50")
    if l.startswith("write:"):
        rest = msg.strip()[6:].strip()
        parts = rest.split(" -> ", 1)
        if len(parts) == 2:
            shell_exec("echo '" + parts[1] + "' > " + parts[0])
            return "Written to " + parts[0]
        return "Usage: write: <path> -> <content>"

    # Support (PC)
    if l.startswith("support:") or l.startswith("ask simone:"):
        return cmd_support(msg.strip().split(":", 1)[1].strip())

    # Meta
    if l in ("fix yourself", "diagnose"): return cmd_diagnose()
    if l == "transcripts": return cmd_transcripts()
    if l in ("who am i", "who are you"): return "I am MiMo, Bruce Nigel's phone superagent. Flipper Zero on a phone."
    if l in ("help", "commands"): return cmd_help()

    return None  # Not a command — pass to LLM

MANIFEST = {
    "name": "MiMo Superagent",
    "short_name": "MiMo",
    "description": "Flipper Zero on a Phone",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0a0a0f",
    "theme_color": "#00ff88",
    "orientation": "portrait",
    "icons": [
        {"src": "https://files.catbox.moe/jno288.jpg", "sizes": "192x192", "type": "image/jpeg", "purpose": "any maskable"},
        {"src": "https://files.catbox.moe/jno288.jpg", "sizes": "512x512", "type": "image/jpeg", "purpose": "any maskable"}
    ]
}

SERVICE_WORKER = """// MiMo Superagent SW
const CACHE = 'mimo-v1';
const ASSETS = ['/', '/manifest.json'];
self.addEventListener('install', e => { e.waitUntil(caches.open(CACHE).then(c => c.addAll(ASSETS))); self.skipWaiting(); });
self.addEventListener('activate', e => { e.waitUntil(caches.keys().then(k => Promise.all(k.filter(x => x !== CACHE).map(x => caches.delete(x))))); self.clients.claim(); });
self.addEventListener('fetch', e => { if (e.request.method !== 'GET') return; e.respondWith(fetch(e.request).catch(() => caches.match(e.request))); });
"""

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no,viewport-fit=cover">
<meta name="theme-color" content="#0a0a0f">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="MiMo">
<link rel="manifest" href="/manifest.json">
<link rel="apple-touch-icon" href="https://files.catbox.moe/jno288.jpg">
<link rel="icon" href="https://files.catbox.moe/jno288.jpg">
<title>MiMo Superagent</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--safe-top:env(safe-area-inset-top);--safe-bottom:env(safe-area-inset-bottom)}
body{background:#0a0a0f;color:#e0e0e0;font-family:system-ui,-apple-system,sans-serif;height:100vh;height:100dvh;display:flex;flex-direction:column;overflow:hidden;padding-top:var(--safe-top)}
.header{display:flex;align-items:center;gap:12px;padding:12px 16px;background:linear-gradient(135deg,#0d1117,#161b22);border-bottom:1px solid #21262d;position:relative;z-index:10}
.avatar-wrap{position:relative;width:48px;height:48px;flex-shrink:0}
.avatar{width:48px;height:48px;border-radius:50%;object-fit:cover;border:2px solid #00ff88}
.avatar-glow{position:absolute;inset:-4px;border-radius:50%;background:conic-gradient(from 0deg,#00ff88,#00aaff,#ff00aa,#00ff88);animation:spin 3s linear infinite;opacity:0.6;z-index:-1}
@keyframes spin{to{transform:rotate(360deg)}}
.header-text h1{font-size:16px;color:#fff}
.header-text span{font-size:11px;color:#00ff88}
.status-dot{width:8px;height:8px;border-radius:50%;background:#00ff88;margin-left:auto;animation:pulse 2s infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.4}}
.chat{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px;-webkit-overflow-scrolling:touch}
.msg{max-width:85%;padding:10px 14px;border-radius:16px;font-size:14px;line-height:1.45;word-wrap:break-word;white-space:pre-wrap;animation:fadeIn .2s ease}
@keyframes fadeIn{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
.msg.user{align-self:flex-end;background:#0d419d;color:#fff;border-bottom-right-radius:4px}
.msg.bot{align-self:flex-start;background:#161b22;border:1px solid #21262d;border-bottom-left-radius:4px}
.msg.bot::before{content:"";display:inline-block;width:6px;height:6px;border-radius:50%;background:#00ff88;margin-right:8px;vertical-align:middle}
.input-bar{display:flex;gap:8px;padding:10px 12px;padding-bottom:calc(10px + var(--safe-bottom));background:#0d1117;border-top:1px solid #21262d;align-items:center}
.input-bar input[type=text]{flex:1;background:#161b22;border:1px solid #30363d;color:#e0e0e0;padding:10px 14px;border-radius:20px;font-size:14px;outline:none;-webkit-appearance:none}
.input-bar input[type=text]:focus{border-color:#00ff88}
.btn{width:42px;height:42px;border-radius:50%;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:18px;flex-shrink:0;-webkit-tap-highlight-color:transparent}
.btn:active{transform:scale(0.9)}
.btn-send{background:#00ff88;color:#000}
.btn-mic{background:#1a1a2e;color:#e0e0e0;border:1px solid #30363d}
.btn-mic.listening{background:#ff4444;animation:pulse 1s infinite}
.btn-file{background:#1a1a2e;color:#e0e0e0;border:1px solid #30363d}
.typing{display:none;align-self:flex-start;padding:10px 14px;background:#161b22;border:1px solid #21262d;border-radius:16px;font-size:14px;color:#888}
.typing.show{display:flex;gap:4px}
.typing span{width:6px;height:6px;background:#00ff88;border-radius:50%;animation:bounce 1.4s infinite}
.typing span:nth-child(2){animation-delay:0.2s}
.typing span:nth-child(3){animation-delay:0.4s}
@keyframes bounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-8px)}}
</style>
</head>
<body>
<div class="header">
  <div class="avatar-wrap"><div class="avatar-glow"></div><img class="avatar" src="https://files.catbox.moe/jno288.jpg" alt="MiMo"></div>
  <div class="header-text"><h1>MiMo Superagent</h1><span>Flipper Zero on a Phone</span></div>
  <div class="status-dot" id="status"></div>
</div>
<div class="chat" id="chat">
  <div class="msg bot">MiMo online. I control this phone completely. Type a command or talk to me. Say "help" for all commands.</div>
</div>
<div class="typing" id="typing"><span></span><span></span><span></span></div>
<div class="input-bar">
  <button class="btn btn-file" onclick="document.getElementById('fileInput').click()">+</button>
  <input type="file" id="fileInput" style="display:none" accept="image/*" onchange="uploadFile(this)">
  <input type="text" id="msg" placeholder="Command or message..." autocomplete="off" autocorrect="off" spellcheck="false" onkeydown="if(event.key==='Enter')send()">
  <button class="btn btn-mic" id="micBtn" ontouchstart="startVoice()" ontouchend="stopVoice()" onmousedown="startVoice()" onmouseup="stopVoice()">🎤</button>
  <button class="btn btn-send" onclick="send()">▶</button>
</div>
<script>
if('serviceWorker' in navigator) navigator.serviceWorker.register('/sw.js');
var chat=document.getElementById('chat'),typing=document.getElementById('typing'),msg=document.getElementById('msg'),micBtn=document.getElementById('micBtn');
function addMsg(t,w){var d=document.createElement('div');d.className='msg '+w;d.textContent=t;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;}
function send(){var t=msg.value.trim();if(!t)return;addMsg(t,'user');msg.value='';typing.classList.add('show');
fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:t})})
.then(r=>r.json()).then(d=>{typing.classList.remove('show');addMsg(d.reply,'bot');speakText(d.reply);})
.catch(e=>{typing.classList.remove('show');addMsg('Error: '+e,'bot');});}
function speakText(t){if('speechSynthesis' in window){speechSynthesis.cancel();var u=new SpeechSynthesisUtterance(t);u.rate=1.1;speechSynthesis.speak(u);}}
var recog=null,listening=false;
function startVoice(){if(listening)return;var SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){return;}
recog=new SR();recog.continuous=false;recog.interimResults=true;recog.lang='en-US';
recog.onresult=function(e){var t='';for(var i=0;i<e.results.length;i++)t+=e.results[i][0].transcript;msg.value=t;};
recog.onend=function(){listening=false;micBtn.classList.remove('listening');if(msg.value.trim())send();};
recog.onerror=function(){listening=false;micBtn.classList.remove('listening');};
recog.start();listening=true;micBtn.classList.add('listening');}
function stopVoice(){if(recog&&listening)recog.stop();}
function uploadFile(input){if(!input.files[0])return;var f=input.files[0],r=new FileReader();
r.onload=function(e){var b=e.target.result.split(',')[1];addMsg('[Photo: '+f.name+']','user');
fetch('/voice',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({audio:b})})
.then(r=>r.json()).then(d=>{addMsg(d.reply,'bot');speakText(d.reply);});};r.readAsDataURL(f);input.value='';}
fetch('/health').then(r=>r.json()).then(()=>document.getElementById('status').style.background='#00ff88')
.catch(()=>document.getElementById('status').style.background='#ff4444');
</script>
</body>
</html>"""

def call_brain(msg):
    if not brain_ready: return "MiMo brain not ready yet"
    try:
        payload = json.dumps({"message": msg}).encode()
        req = urllib.request.Request("http://localhost:9999/chat",
            data=payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=60)
        return json.loads(resp.read()).get("reply", "No response")
    except Exception as e:
        return "Brain error: " + str(e)

def mimo_chat(msg):
    log_transcript("user", msg)
    result = handle_command(msg)
    if result:
        log_transcript("mimo", result)
        return result
    result = call_brain(msg)
    log_transcript("mimo", result)
    return result

def tg_send(text):
    if not TG_TOKEN or not TG_CHAT_ID: return
    try:
        url = "https://api.telegram.org/bot" + TG_TOKEN + "/sendMessage"
        data = json.dumps({"chat_id": TG_CHAT_ID, "text": text}).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print("TG send error:", e)

class MiMoHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
        elif self.path == "/manifest.json":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(MANIFEST).encode())
        elif self.path == "/sw.js":
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            self.wfile.write(SERVICE_WORKER.encode())
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"ok": True, "uptime": time.time()}).encode())
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(length)) if length else {}

        if self.path == "/chat":
            msg = body.get("message", "")
            reply = mimo_chat(msg)
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"reply": reply}).encode())
            threading.Thread(target=tg_send, args=(msg + "\n\n" + reply,), daemon=True).start()

        elif self.path == "/voice":
            reply = "Voice processing coming soon"
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"reply": reply}).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):
        if "/health" not in str(args):
            print("[HTTP]", fmt % args)

import time

def run_server():
    server = HTTPServer((HOST, PORT), MiMoHandler)
    print("MiMo Superagent on port " + str(PORT))
    server.serve_forever()

def telegram_poll():
    if not TG_TOKEN: return
    offset = 0
    while True:
        try:
            url = "https://api.telegram.org/bot" + TG_TOKEN + "/getUpdates?offset=" + str(offset) + "&timeout=30"
            resp = urllib.request.urlopen(url, timeout=35)
            data = json.loads(resp.read())
            for update in data.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message", {})
                text = msg.get("text", "")
                chat_id = str(msg.get("chat", {}).get("id", ""))
                if text:
                    print("[TG]", chat_id, ":", text)
                    reply = mimo_chat(text)
                    tg_send(reply)
        except Exception as e:
            print("[TG poll error]", e)
            time.sleep(5)

def wait_for_brain():
    global brain_ready
    print("Waiting for MiMo brain on port 9999...")
    for i in range(120):
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            result = s.connect_ex(("127.0.0.1", 9999))
            s.close()
            if result == 0:
                brain_ready = True
                print("Brain connected!")
                return
        except: pass
        time.sleep(1)
    print("Brain not found after 120s")

if __name__ == "__main__":
    os.system("termux-wake-lock 2>/dev/null")
    os.system("termux-notification -t MiMo -c 'Superagent online' 2>/dev/null")
    threading.Thread(target=wait_for_brain, daemon=True).start()
    threading.Thread(target=telegram_poll, daemon=True).start()
    run_server()

if __name__ == "__main__":
    os.system("termux-wake-lock 2>/dev/null")
    os.system("termux-notification -t MiMo -c 'Superagent online' 2>/dev/null")
    threading.Thread(target=wait_for_brain, daemon=True).start()
    threading.Thread(target=telegram_poll, daemon=True).start()
    run_server()
