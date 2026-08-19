#!/usr/bin/env python3
"""
BruceClaw Chat + Phone Control
Imports MiMo brain directly, no subprocess piping.
Port 8080. Talks to bruceclaw.py's brain in-process.
"""
import os, sys, json, time, subprocess, base64, threading, re
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from urllib.parse import unquote

class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True

PORT = 8080
HOME = os.path.expanduser("~")

# ============ PHONE CONTROL ============
def run(cmd, t=10):
    try: return subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=t).stdout
    except: return "error"

# ============ MIMO BRAIN (imported directly) ============
sys.path.insert(0, os.path.join(HOME, "bruceclaw"))
brain = None
brain_ready = False

def init_brain():
    global brain, brain_ready
    try:
        # Change to bruceclaw directory so config.json is found
        mimo_dir = os.path.join(HOME, "bruceclaw")
        os.chdir(mimo_dir)
        from bruceclaw import BruceClawBrain
        brain = BruceClawBrain()
        # Wait for LLM to connect (up to 15 seconds)
        for i in range(15):
            if brain.llm_ready:
                brain_ready = True
                print("[OK] MiMo LLM connected")
                return
            time.sleep(1)
        # LLM didn't connect in time, but brain still works with local commands
        brain_ready = True
        print("[WARN] MiMo LLM not connected yet, local commands only")
    except Exception as e:
        print(f"[ERROR] Failed to load MiMo brain: {e}")

def mimo_chat(msg):
    global brain, brain_ready
    if not brain:
        return "MiMo brain not loaded"
    if not brain_ready:
        return "MiMo is starting up, try again in a few seconds"
    try:
        reply = brain.handle_input(msg)
        # Strip think tags before action detection
        clean = re.sub(r'<think>.*?</think>\n?\n?', '', reply, flags=re.DOTALL).strip()
        # Execute actions MiMo mentions
        lower = clean.lower()
        action_done = ""
        # Open app
        m = re.search(r'open(?:ing)?\s+(youtube|chrome|whatsapp|telegram|settings|camera|maps|phone|gallery|files|play store)', lower)
        if m:
            apps = {"youtube":"com.google.android.youtube","chrome":"com.android.chrome","whatsapp":"com.whatsapp","telegram":"org.telegram.messenger","settings":"com.android.settings","camera":"com.android.camera","maps":"com.google.android.apps.maps","phone":"com.google.android.dialer","gallery":"com.google.android.apps.photos","files":"com.google.android.apps.nbu.files","play store":"com.android.vending"}
            pkg = apps.get(m.group(1).strip(), m.group(1).strip())
            run(f"monkey -p {pkg} -c android.intent.category.LAUNCHER 1")
            action_done = "\n✅ Opened " + m.group(1)
        elif "answer" in lower and ("call" in lower or "phone" in lower):
            run("input keyevent 5")
            action_done = "\n✅ Answered call"
        elif "hang" in lower and "up" in lower:
            run("input keyevent 6")
            action_done = "\n✅ Hung up"
        elif "go home" in lower:
            run("input keyevent 3")
            action_done = "\n✅ Home"
        elif "go back" in lower:
            run("input keyevent 4")
            action_done = "\n✅ Back"
        elif re.search(r'scroll\s+(up|down)', lower):
            d = re.search(r'scroll\s+(up|down)', lower).group(1)
            w,h = 1080,2400
            try:
                out = run("wm size")
                w,h = [int(x) for x in out.split(":")[-1].strip().split("x")]
            except: pass
            cy = int(h*0.7) if d=="down" else int(h*0.3)
            ey = int(h*0.3) if d=="down" else int(h*0.7)
            run(f"input swipe {w//2} {cy} {w//2} {ey} 400")
            action_done = f"\n✅ Scrolled {d}"
        elif "take a photo" in lower or "open camera" in lower:
            run("am start -a android.media.action.STILL_IMAGE_CAMERA")
            action_done = "\n✅ Camera opened"
        elif re.search(r'search\s+(?:for\s+)?(.+)', lower):
            q = re.search(r'search\s+(?:for\s+)?(.+)', lower).group(1).strip()
            run(f"am start -a android.intent.action.VIEW -d 'https://www.google.com/search?q={q}'")
            action_done = f"\n✅ Searching: {q}"
        elif re.search(r'call\s+(\d+)', lower):
            num = re.search(r'call\s+(\d+)', lower).group(1)
            run(f"am start -a android.intent.action.DIAL -d tel:{num}")
            action_done = f"\n✅ Calling {num}"
        return reply + action_done
    except Exception as e:
        return f"Error: {e}"

# ============ HTTP SERVER ============
class H(BaseHTTPRequestHandler):
    def do_GET(self):
        p = unquote(self.path)
        if p == "/chat" or p == "/":
            self.send_response(200)
            self.send_header("Content-Type","text/html")
            self.send_header("Access-Control-Allow-Origin","*")
            self.end_headers()
            self.wfile.write(CHAT.encode())
        elif p == "/remote":
            remote_path = os.path.join(HOME, "chat.py_remote.html")
            if not os.path.exists(remote_path):
                # Serve inline
                self.send_response(200)
                self.send_header("Content-Type","text/html")
                self.send_header("Access-Control-Allow-Origin","*")
                self.end_headers()
                self.wfile.write(REMOTE_HTML.encode())
            else:
                with open(remote_path,"rb") as f:
                    self.send_response(200)
                    self.send_header("Content-Type","text/html")
                    self.send_header("Access-Control-Allow-Origin","*")
                    self.end_headers()
                    self.wfile.write(f.read())
        elif p == "/screen_size":
            out = run("wm size")
            try:
                w,h = [int(x) for x in out.split(":")[-1].strip().split("x")]
                self.js({"ok":True,"width":w,"height":h})
            except: self.js({"ok":True,"width":1080,"height":2400})
        elif p == "/screenshot":
            path = f"{HOME}/sc.png"
            run(f"screencap -p {path}")
            if os.path.exists(path):
                with open(path,"rb") as f: d = base64.b64encode(f.read()).decode()
                os.remove(path)
                self.js({"ok":True,"img":d})
            else: self.js({"ok":False})
        elif p.startswith("/tap/"):
            parts = p.split("/")
            if len(parts)>=4: run(f"input tap {parts[2]} {parts[3]}")
            self.js({"ok":True})
        elif p.startswith("/scroll/"):
            d = p.split("/")[2] if len(p.split("/"))>2 else "down"
            w,h = 1080,2400
            try:
                out = run("wm size")
                w,h = [int(x) for x in out.split(":")[-1].strip().split("x")]
            except: pass
            cy = int(h*0.7) if d=="down" else int(h*0.3)
            ey = int(h*0.3) if d=="down" else int(h*0.7)
            run(f"input swipe {w//2} {cy} {w//2} {ey} 400")
            self.js({"ok":True})
        elif p == "/answer": run("input keyevent 5"); self.js({"ok":True})
        elif p == "/hangup": run("input keyevent 6"); self.js({"ok":True})
        elif p == "/home": run("input keyevent 3"); self.js({"ok":True})
        elif p == "/back": run("input keyevent 4"); self.js({"ok":True})
        elif p == "/battery":
            out = run("termux-battery-status")
            try: self.js({"ok":True,"bat":json.loads(out)})
            except: self.js({"ok":True,"bat":out})
        elif p.startswith("/mic/"):
            d = int(p.split("/")[2]) if len(p.split("/"))>2 else 5
            path = f"{HOME}/mic.wav"
            run(f"termux-microphone-record -l {d} -f {path}", d+5)
            self.js({"ok":True,"path":path})
        elif p.startswith("/open/"): run(f"monkey -p {p.split('/')[2]} -c android.intent.category.LAUNCHER 1"); self.js({"ok":True})
        # === BROWSER CONTROL ===
        elif p.startswith("/go/"):
            url = p[4:]
            run(f"am start -a android.intent.action.VIEW -d '{url}'")
            time.sleep(2)
            self.js({"ok":True,"url":url})
        elif p.startswith("/google/"):
            q = p[8:]
            run(f"am start -a android.intent.action.VIEW -d 'https://www.google.com/search?q={q}'")
            time.sleep(3)
            self.js({"ok":True,"query":q})
        elif p == "/page":
            # Get current page text via accessibility tree
            out = run("uiautomator dump /dev/tty 2>/dev/null || echo 'no uiautomator'")
            self.js({"ok":True,"html":out[:5000]})
        elif p.startswith("/form/"):
            # /form/field_name/value — fill form field by accessibility text
            parts = p.split("/")
            if len(parts) >= 4:
                field = parts[2]
                value = parts[3]
                # Try to find and fill the field using accessibility
                self.js({"ok":True,"field":field,"value":value,"note":"Use /tap then /type instead"})
            else:
                self.js({"err":"usage: /form/field/value"})
        elif p.startswith("/js/"):
            # Run JavaScript in Chrome via accessibility
            js_code = p[4:]
            self.js({"ok":True,"note":"JS execution not supported via ADB, use /tap and /type"})
        elif p == "/apps":
            out = run("pm list packages -3 | head -30")
            self.js({"ok":True,"apps":out})
        elif p.startswith("/shell/"): self.js({"ok":True,"out":run(p[7:],30)[:2000]})
        elif p == "/status":
            out = run("wm size")
            try: sz = out.split(":")[-1].strip()
            except: sz = "?"
            self.js({"ok":True,"screen":sz,"mimo":brain_ready})
        else: self.js({"err":"unknown"},404)

    def do_POST(self):
        ln = int(self.headers.get("Content-Length",0))
        body = self.rfile.read(ln) if ln else b""
        try: d = json.loads(body)
        except: d = {}
        p = unquote(self.path)
        if p == "/chat":
            msg = d.get("message","").strip()
            if not msg: self.js({"err":"empty"}); return
            reply = mimo_chat(msg)
            self.js({"ok":True,"reply":reply})
        # === BROWSER POST ===
        elif p == "/browse":
            url = d.get("url","").strip()
            action = d.get("action","go")
            if action == "go" and url:
                run(f"am start -a android.intent.action.VIEW -d '{url}'")
                time.sleep(3)
                # Take screenshot after loading
                sc = f"{HOME}/sc.png"
                run(f"screencap -p {sc}")
                img = ""
                if os.path.exists(sc):
                    with open(sc,"rb") as f: img = base64.b64encode(f.read()).decode()
                    os.remove(sc)
                self.js({"ok":True,"url":url,"img":img})
            elif action == "google":
                q = d.get("query","").strip()
                run(f"am start -a android.intent.action.VIEW -d 'https://www.google.com/search?q={q}'")
                time.sleep(3)
                sc = f"{HOME}/sc.png"
                run(f"screencap -p {sc}")
                img = ""
                if os.path.exists(sc):
                    with open(sc,"rb") as f: img = base64.b64encode(f.read()).decode()
                    os.remove(sc)
                self.js({"ok":True,"query":q,"img":img})
            elif action == "fill":
                field = d.get("field","").strip()
                value = d.get("value","").strip()
                # Tap the field by text, then type
                run(f"input tap $(dumpsys window | grep -o 'mCurrentFocus' | head -1)")
                time.sleep(0.5)
                run(f"input text '{value}'")
                self.js({"ok":True,"field":field,"value":value})
            elif action == "scrape":
                # Get current screen content via uiautomator
                out = run("uiautomator dump /dev/tty 2>/dev/null", 10)
                self.js({"ok":True,"content":out[:5000]})
            else:
                self.js({"err":"unknown browse action"})
        elif p == "/type":
            txt = d.get("text","").replace("'","'\\''")
            run(f"input text '{txt}'")
            self.js({"ok":True})
        elif p == "/tts": run(f"termux-tts-speak '{d.get('text','')}'"); self.js({"ok":True})
        # === VOICE ENDPOINT ===
        elif p == "/voice":
            # Browser sends recorded audio (webm blob as base64)
            audio_b64 = d.get("audio", "")
            if not audio_b64:
                self.js({"err":"no audio"}); return
            # Save audio to temp file
            audio_path = f"{HOME}/voice_input.webm"
            try:
                import base64 as b64
                audio_bytes = b64.b64decode(audio_b64)
                with open(audio_path, "wb") as f:
                    f.write(audio_bytes)
                # Transcribe with Groq Whisper
                whisper_key = brain.config.get("api_key", "")
                cmd = [
                    "curl", "-s", "--max-time", "30",
                    "-X", "POST", "https://api.groq.com/openai/v1/audio/transcriptions",
                    "-H", "Authorization: Bearer " + whisper_key,
                    "-F", "file=@" + audio_path,
                    "-F", "model=whisper-large-v3-turbo",
                    "-F", "language=en"
                ]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
                transcript = ""
                if r.returncode == 0:
                    try:
                        transcript = json.loads(r.stdout).get("text", "")
                    except: transcript = r.stdout[:200]
                os.remove(audio_path)
                if not transcript:
                    self.js({"ok":True,"transcript":"","reply":"Couldn't understand the audio"}); return
                # Send transcript to MiMo
                reply = mimo_chat(transcript)
                # Speak the response
                clean_reply = re.sub(r'<think>.*?</think>\n?\n?', '', reply, flags=re.DOTALL).strip()
                if clean_reply:
                    run(f"termux-tts-speak '{clean_reply[:200]}'")
                self.js({"ok":True,"transcript":transcript,"reply":reply})
            except Exception as e:
                self.js({"err":str(e)})
        else: self.js({"err":"unknown"},404)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin","*")
        self.send_header("Access-Control-Allow-Methods","POST,GET,OPTIONS")
        self.send_header("Access-Control-Allow-Headers","Content-Type")
        self.end_headers()

    def js(self, d, code=200):
        self.send_response(code)
        self.send_header("Content-Type","application/json")
        self.send_header("Access-Control-Allow-Origin","*")
        self.end_headers()
        self.wfile.write(json.dumps(d).encode())

    def log_message(self,*a): pass

CHAT = """<!DOCTYPE html>
<html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no"><title>BruceClaw</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:sans-serif;background:#0a0a0a;color:#fff;height:100vh;display:flex;flex-direction:column;overflow:hidden}
#h{background:#181818;padding:10px;display:flex;align-items:center;justify-content:space-between;border-bottom:3px solid #ff6600}
#h h1{font-size:20px;color:#ff6600}
.st{font-size:11px;color:#0f8;background:#1a1a2e;padding:3px 8px;border-radius:8px}
.st.off{color:#f44}
#c{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px}
.m{max-width:85%;padding:10px 14px;border-radius:12px;font-size:16px;line-height:1.4;white-space:pre-wrap;word-wrap:break-word}
.mu{align-self:flex-end;background:#ff6600;color:#fff}
.mb{align-self:flex-start;background:#222;color:#eee;border:1px solid #333}
.me{border-color:#f44;color:#f88;font-size:13px}
.mi{border-color:#0f8;color:#0f8;font-size:13px}
#i{padding:8px;background:#181818;border-top:2px solid #ff6600;display:flex;gap:6px}
#i input{flex:1;background:#222;border:1px solid #444;color:#fff;padding:10px;border-radius:10px;font-size:16px}
#i button{background:#ff6600;color:#fff;border:none;padding:10px 18px;border-radius:10px;font-size:15px;font-weight:700}
</style></head><body>
<div id="h"><h1>BRUCECLAW</h1><span class="st off" id="st">Loading MiMo...</span></div>
<div id="c"><div class="mb">Connecting to MiMo...</div></div>
<div id="i"><input id="m" placeholder="Message..." onkeydown="if(event.key==='Enter')send()"><button onclick="send()">SEND</button><button id="micbtn" onclick="startVoice()">🎤</button><button id="contbtn" onclick="toggleContinuous()" style="font-size:11px">🔄</button></div>
<script>
function add(t,c){var d=document.createElement("div");d.className="m "+c;d.textContent=t;document.getElementById("c").appendChild(d);document.getElementById("c").scrollTop=99999;}
function send(){var m=document.getElementById("m").value.trim();if(!m)return;add(m,"mu");document.getElementById("m").value="";add("Thinking...","mi");
fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:m})}).then(r=>r.json()).then(d=>{var c=document.getElementById("c");if(c.lastChild)c.removeChild(c.lastChild);add(d.reply||"No response","mb");}).catch(e=>{var c=document.getElementById("c");if(c.lastChild)c.removeChild(c.lastChild);add("Error: "+e,"me");});}
function checkStatus(){fetch("/status").then(r=>r.json()).then(d=>{var s=document.getElementById("st");if(d.mimo){s.textContent="MiMo READY";s.className="st";}else{s.textContent="MiMo starting...";s.className="st off";setTimeout(checkStatus,3000);}}).catch(()=>{document.getElementById("st").textContent="OFFLINE";});}
fetch("/status").then(r=>r.json()).then(d=>{document.getElementById("c").innerHTML="";if(d.mimo){add("MiMo ready. Type a message or tap 🎤 to talk.","mb");document.getElementById("st").textContent="MiMo READY";document.getElementById("st").className="st";}else{add("MiMo is loading the LLM... this takes a few seconds.","mi");checkStatus();}});
var mediaRecorder=null;var audioChunks=[];var continuousMode=false;var stream=null;
function startVoice(){var btn=document.getElementById("micbtn");
if(mediaRecorder&&mediaRecorder.state==="recording"){mediaRecorder.stop();btn.textContent="🎤";btn.style.background="";return;}
navigator.mediaDevices.getUserMedia({audio:true}).then(function(s){
stream=s;mediaRecorder=new MediaRecorder(s);audioChunks=[];
mediaRecorder.ondataavailable=function(e){audioChunks.push(e.data);};
mediaRecorder.onstop=function(){processAudio();};
mediaRecorder.start();btn.textContent="⏹";btn.style.background="#f44";
}).catch(function(e){add("Mic access denied: "+e,"me");});}
function processAudio(){stream.getTracks().forEach(function(t){t.stop();});
var blob=new Blob(audioChunks,{type:"audio/webm"});var reader=new FileReader();
reader.onload=function(){var b64=reader.result.split(",")[1];
fetch("/voice",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({audio:b64})})
.then(function(r){return r.json();}).then(function(d){
if(d.transcript){var t=d.transcript.toLowerCase();
if(t.includes("stop listening")||t.includes("stop listening")){continuousMode=false;document.getElementById("contbtn").style.background="";add("🔇 Stopped listening","mi");return;}
if(t.includes("start listening")){continuousMode=true;document.getElementById("contbtn").style.background="#0f8";add("🎤 Listening...","mi");setTimeout(function(){startVoice();},1000);return;}
add("You said: "+d.transcript,"mu");}
if(d.reply){add(d.reply,"mb");}
if(continuousMode){setTimeout(function(){startVoice();},1500);}
else{document.getElementById("micbtn").textContent="🎤";document.getElementById("micbtn").style.background="";}
}).catch(function(e){add("Voice error: "+e,"me");
if(continuousMode){setTimeout(function(){startVoice();},2000);}
});};reader.readAsDataURL(blob);}
function toggleContinuous(){continuousMode=!continuousMode;var btn=document.getElementById("contbtn");
if(continuousMode){btn.style.background="#0f8";add("🎤 Continuous mode ON — say 'stop listening' to pause","mi");startVoice();}
else{btn.style.background="";add("🔇 Continuous mode OFF","mi");
if(mediaRecorder&&mediaRecorder.state==="recording"){mediaRecorder.stop();document.getElementById("micbtn").textContent="🎤";document.getElementById("micbtn").style.background="";}}}
</script></body></html>"""

if __name__ == "__main__":
    print("BruceClaw Chat + Phone Control")
    print(f"Chat: http://localhost:{PORT}")
    print("Loading MiMo brain...")
    t = threading.Thread(target=init_brain, daemon=True)
    t.start()
    print(f"Server starting on port {PORT}")
    ThreadedHTTPServer(("0.0.0.0",PORT),H).serve_forever()
