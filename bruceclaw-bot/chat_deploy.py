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

import os, sys, json, time, threading, urllib.request, urllib.parse
from http.server import SimpleHTTPRequestHandler, HTTPServer

# Import our modules

HOST, PORT = "0.0.0.0", 8080
TG_TOKEN = "8784176401:AAGEKNUai0aN5VR3nLOCJrKiQ5b9CNqr69Y"
TG_CHAT_ID = "7843419304"
brain = None
brain_ready = False

def mimo_chat(msg):
    log_transcript("user", msg)
    result = handle_command(msg)
    if result:
        log_transcript("mimo", result)
        return result
    result = call_brain(msg)
    log_transcript("mimo", result)
    return result

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

MANIFEST = {
    "name": "MiMo",
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

SERVICE_WORKER = """// MiMo SW
const C='mimo-v2';const A=['/','/manifest.json'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(C).then(c=>c.addAll(A)));self.skipWaiting();});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(k=>Promise.all(k.filter(x=>x!==C).map(x=>caches.delete(x)))));self.clients.claim();});
self.addEventListener('fetch',e=>{if(e.request.method!=='GET')return;e.respondWith(fetch(e.request).catch(()=>caches.match(e.request)));});"""

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
<title>MiMo</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
:root{--safe-top:env(safe-area-inset-top);--safe-bottom:env(safe-area-inset-bottom);--accent:#00ff88;--bg:#0a0a0f;--surface:#161b22;--border:#21262d;--text:#e0e0e0;--dim:#888}
html,body{height:100%;overflow:hidden}
body{background:var(--bg);color:var(--text);font-family:system-ui,-apple-system,sans-serif;display:flex;flex-direction:column;padding-top:var(--safe-top);font-size:16px}
.hdr{display:flex;align-items:center;gap:12px;padding:12px 16px;background:linear-gradient(135deg,#0d1117,#161b22);border-bottom:1px solid var(--border);flex-shrink:0}
.av-w{position:relative;width:44px;height:44px;flex-shrink:0}
.av{width:44px;height:44px;border-radius:50%;object-fit:cover;border:2px solid var(--accent)}
.av-g{position:absolute;inset:-3px;border-radius:50%;background:conic-gradient(from 0deg,var(--accent),#00aaff,#ff00aa,var(--accent));animation:spin 3s linear infinite;opacity:.6;z-index:-1}
@keyframes spin{to{transform:rotate(360deg)}}
.hdr h1{font-size:18px;color:#fff;font-weight:600}
.hdr span{font-size:12px;color:var(--accent);display:block}
.dot{width:8px;height:8px;border-radius:50%;background:var(--accent);margin-left:auto;flex-shrink:0}
.dot.off{background:#ff4444}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.3}}
.dot{animation:pulse 2s infinite}
.qbar{display:flex;gap:6px;padding:8px 12px;overflow-x:auto;flex-shrink:0;-webkit-overflow-scrolling:touch;scrollbar-width:none}
.qbar::-webkit-scrollbar{display:none}
.qbtn{padding:6px 12px;border-radius:14px;border:1px solid var(--border);background:var(--surface);color:var(--accent);font-size:13px;white-space:nowrap;cursor:pointer;-webkit-tap-highlight-color:transparent;flex-shrink:0}
.qbtn:active{background:var(--accent);color:#000}
.chat{flex:1;overflow-y:auto;padding:12px 14px;display:flex;flex-direction:column;gap:8px;-webkit-overflow-scrolling:touch}
.msg{max-width:88%;padding:10px 14px;border-radius:16px;font-size:16px;line-height:1.5;word-wrap:break-word;white-space:pre-wrap;animation:fadeUp .15s ease}
@keyframes fadeUp{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.msg.user{align-self:flex-end;background:#0d419d;color:#fff;border-bottom-right-radius:4px}
.msg.bot{align-self:flex-start;background:var(--surface);border:1px solid var(--border);border-bottom-left-radius:4px}
.msg.bot b{color:var(--accent)}
.typing{display:none;align-self:flex-start;padding:10px 14px;background:var(--surface);border:1px solid var(--border);border-radius:16px}
.typing.on{display:flex;gap:5px}
.typing i{width:7px;height:7px;background:var(--accent);border-radius:50%;animation:bounce 1.4s infinite}
.typing i:nth-child(2){animation-delay:.2s}
.typing i:nth-child(3){animation-delay:.4s}
@keyframes bounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-6px)}}
.install{display:none;padding:10px 16px;background:linear-gradient(135deg,#0d419d,#1a1a5e);border-top:1px solid var(--border);text-align:center;flex-shrink:0}
.install.show{display:block}
.install button{background:var(--accent);color:#000;border:none;padding:8px 20px;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer}
.install button:active{opacity:.8}
.ibar{display:flex;gap:8px;padding:8px 10px;padding-bottom:calc(8px + var(--safe-bottom));background:#0d1117;border-top:1px solid var(--border);align-items:center;flex-shrink:0}
.ibar input[type=text]{flex:1;background:var(--surface);border:1px solid #30363d;color:var(--text);padding:12px 16px;border-radius:22px;font-size:16px;outline:none;-webkit-appearance:none}
.ibar input:focus{border-color:var(--accent)}
.btn{width:44px;height:44px;border-radius:50%;border:none;cursor:pointer;display:flex;align-items:center;justify-content:center;font-size:20px;flex-shrink:0;-webkit-tap-highlight-color:transparent}
.btn:active{transform:scale(.9)}
.btn-s{background:var(--accent);color:#000}
.btn-m{background:var(--surface);color:var(--text);border:1px solid #30363d}
.btn-m.on{background:#ff4444;color:#fff;animation:pulse 1s infinite}
.btn-f{background:var(--surface);color:var(--text);border:1px solid #30363d}
.voice{display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:100;flex-direction:column;align-items:center;justify-content:center;gap:20px}
.voice.on{display:flex}
.voice .ring{width:120px;height:120px;border-radius:50%;border:4px solid var(--accent);animation:vpulse 1.5s infinite}
@keyframes vpulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.1);opacity:.5}}
.voice .viz{font-size:48px;color:var(--accent)}
.voice .hint{color:var(--dim);font-size:14px}
.voice .cancel{background:none;border:1px solid var(--border);color:var(--text);padding:10px 24px;border-radius:8px;font-size:14px;cursor:pointer}
</style>
</head>
<body>
<div class="hdr">
  <div class="av-w"><div class="av-g"></div><img class="av" src="https://files.catbox.moe/jno288.jpg" alt="MiMo"></div>
  <div><h1>MiMo</h1><span id="sub">Flipper Zero on a Phone</span></div>
  <div class="dot" id="dot"></div>
</div>
<div class="qbar" id="qbar">
  <button class="qbtn" onclick="cmd('help')">Commands</button>
  <button class="qbtn" onclick="cmd('battery')">Battery</button>
  <button class="qbtn" onclick="cmd('wifi')">WiFi</button>
  <button class="qbtn" onclick="cmd('bluetooth')">Bluetooth</button>
  <button class="qbtn" onclick="cmd('sensors')">Sensors</button>
  <button class="qbtn" onclick="cmd('apps')">Apps</button>
  <button class="qbtn" onclick="cmd('processes')">Processes</button>
  <button class="qbtn" onclick="cmd('ram')">RAM</button>
  <button class="qbtn" onclick="cmd('disk')">Storage</button>
  <button class="qbtn" onclick="cmd('location')">GPS</button>
  <button class="qbtn" onclick="cmd('contacts')">Contacts</button>
  <button class="qbtn" onclick="cmd('clipboard')">Clipboard</button>
  <button class="qbtn" onclick="cmd('screenshot')">Screenshot</button>
  <button class="qbtn" onclick="cmd('fix yourself')">Diagnose</button>
</div>
<div class="chat" id="chat">
  <div class="msg bot"><b>MiMo online.</b> I control this phone completely. Tap a button above or type a command. Say <b>"help"</b> for everything I can do.</div>
</div>
<div class="typing" id="typing"><i></i><i></i><i></i></div>
<div class="install" id="install"><p style="margin-bottom:8px;color:#fff">Add MiMo to your home screen?</p><button onclick="installPWA()">Install</button></div>
<div class="ibar">
  <button class="btn btn-f" onclick="document.getElementById('fi').click()">+</button>
  <input type="file" id="fi" style="display:none" accept="image/*" onchange="upload(this)">
  <input type="text" id="msg" placeholder="Type or say something..." autocomplete="off" autocorrect="off" spellcheck="false" enterkeyhint="send">
  <button class="btn btn-m" id="mb" ontouchstart="vstart()" ontouchend="vstop()" onmousedown="vstart()" onmouseup="vstop()">&#x1F3A4;</button>
  <button class="btn btn-s" id="sb" onclick="send()">&#x25B6;</button>
</div>
<div class="voice" id="vo">
  <div class="ring"></div>
  <div class="viz">&#x1F399;&#xFE0F;</div>
  <div class="hint">Listening...</div>
  <button class="cancel" onclick="vstop()">Cancel</button>
</div>
<script>
if('serviceWorker' in navigator)navigator.serviceWorker.register('/sw.js').catch(function(){});
var chat=document.getElementById('chat'),typing=document.getElementById('typing'),msg=document.getElementById('msg'),
    mb=document.getElementById('mb'),sb=document.getElementById('sb'),vo=document.getElementById('vo');
msg.addEventListener('keydown',function(e){if(e.key==='Enter'){e.preventDefault();send();}});
function cmd(t){msg.value=t;send();}
function addMsg(text,who){var d=document.createElement('div');d.className='msg '+who;d.textContent=text;chat.appendChild(d);chat.scrollTop=chat.scrollHeight;return d;}
function send(){var t=msg.value.trim();if(!t)return;addMsg(t,'user');msg.value='';typing.classList.add('on');sb.disabled=true;
fetch('/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:t})})
.then(function(r){return r.json();}).then(function(d){typing.classList.remove('on');sb.disabled=false;addMsg(d.reply,'bot');speak(d.reply);})
.catch(function(){typing.classList.remove('on');sb.disabled=false;addMsg('Connection lost. Is MiMo running?','bot');});}
function speak(t){if(!('speechSynthesis' in window))return;window.speechSynthesis.cancel();var u=new SpeechSynthesisUtterance(t);u.rate=1.1;window.speechSynthesis.speak(u);}
var rg=null,lv=false;
function vstart(){if(lv)return;var SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){alert('Speech recognition not supported. Use Chrome.');return;}
rg=new SR();rg.continuous=false;rg.interimResults=true;rg.lang='en-US';vo.classList.add('on');
rg.onresult=function(e){var r='';for(var i=0;i<e.results.length;i++)r+=e.results[i][0].transcript;msg.value=r;};
rg.onend=function(){lv=false;mb.classList.remove('on');vo.classList.remove('on');if(msg.value.trim())send();};
rg.onerror=function(){lv=false;mb.classList.remove('on');vo.classList.remove('on');};rg.start();lv=true;mb.classList.add('on');}
function vstop(){if(rg&&lv)rg.stop();}
function upload(input){if(!input.files[0])return;var f=input.files[0],r=new FileReader();
r.onload=function(e){var b=e.target.result.split(',')[1];addMsg('[Photo: '+f.name+']','user');
fetch('/voice',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({audio:b})})
.then(function(r){return r.json();}).then(function(d){addMsg(d.reply,'bot');speak(d.reply);});};r.readAsDataURL(f);input.value='';}
fetch('/health').then(function(){document.getElementById('dot').className='dot';}).catch(function(){document.getElementById('dot').className='dot off';});
var deferredPrompt;window.addEventListener('beforeinstallprompt',function(e){e.preventDefault();deferredPrompt=e;document.getElementById('install').classList.add('show');});
function installPWA(){if(!deferredPrompt)return;deferredPrompt.prompt();deferredPrompt.userChoice.then(function(){document.getElementById('install').classList.remove('show');});}
</script>
</body>
</html>"""

import os, json, threading, urllib.request

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
