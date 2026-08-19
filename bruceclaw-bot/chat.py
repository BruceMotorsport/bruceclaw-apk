#!/usr/bin/env python3
"""
BruceClaw Chat + Phone Control
Imports MiMo brain directly, no subprocess piping.
Port 8080. Talks to bruceclaw.py's brain in-process.
"""
import os, sys, json, time, subprocess, base64, threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote

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
        return brain.handle_input(msg)
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
        elif p == "/type":
            txt = d.get("text","").replace("'","'\\''")
            run(f"input text '{txt}'")
            self.js({"ok":True})
        elif p == "/tts": run(f"termux-tts-speak '{d.get('text','')}'"); self.js({"ok":True})
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
<div id="i"><input id="m" placeholder="Message..." onkeydown="if(event.key==='Enter')send()"><button onclick="send()">SEND</button></div>
<script>
function add(t,c){var d=document.createElement("div");d.className="m "+c;d.textContent=t;document.getElementById("c").appendChild(d);document.getElementById("c").scrollTop=99999;}
function send(){var m=document.getElementById("m").value.trim();if(!m)return;add(m,"mu");document.getElementById("m").value="";add("Thinking...","mi");
fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:m})}).then(r=>r.json()).then(d=>{var c=document.getElementById("c");if(c.lastChild)c.removeChild(c.lastChild);add(d.reply||"No response","mb");}).catch(e=>{var c=document.getElementById("c");if(c.lastChild)c.removeChild(c.lastChild);add("Error: "+e,"me");});}
function checkStatus(){fetch("/status").then(r=>r.json()).then(d=>{var s=document.getElementById("st");if(d.mimo){s.textContent="MiMo READY";s.className="st";}else{s.textContent="MiMo starting...";s.className="st off";setTimeout(checkStatus,3000);}}).catch(()=>{document.getElementById("st").textContent="OFFLINE";});}
fetch("/status").then(r=>r.json()).then(d=>{document.getElementById("c").innerHTML="";if(d.mimo){add("MiMo ready. Type a message.","mb");document.getElementById("st").textContent="MiMo READY";document.getElementById("st").className="st";}else{add("MiMo is loading the LLM... this takes a few seconds.","mi");checkStatus();}});
</script></body></html>"""

if __name__ == "__main__":
    print("BruceClaw Chat + Phone Control")
    print(f"Chat: http://localhost:{PORT}")
    print("Loading MiMo brain...")
    t = threading.Thread(target=init_brain, daemon=True)
    t.start()
    print(f"Server starting on port {PORT}")
    HTTPServer(("0.0.0.0",PORT),H).serve_forever()
