#!/usr/bin/env python3
"""
BruceClaw Chat + Phone Control
Single file. Port 8080. Talks to MiMo on port 9999.
"""
import os, json, time, subprocess, socket, base64
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import unquote

PORT = 8080
HOME = os.path.expanduser("~")

# Auto-start MiMo brain if not running
def ensure_mimo():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("127.0.0.1", 9999))
        s.close()
        print("[OK] MiMo already running on port 9999")
        return
    except:
        pass
    print("[START] Starting MiMo brain on port 9999...")
    mimo_dir = os.path.join(HOME, "bruceclaw")
    if os.path.exists(os.path.join(mimo_dir, "bruceclaw.py")):
        subprocess.Popen(
            ["python3", "bruceclaw.py"],
            cwd=mimo_dir,
            stdout=open(os.devnull, "w"),
            stderr=open(os.devnull, "w"),
            start_new_session=True
        )
        time.sleep(3)
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(2)
            s.connect(("127.0.0.1", 9999))
            s.close()
            print("[OK] MiMo started on port 9999")
        except:
            print("[WARN] MiMo started but not responding yet on port 9999")
    else:
        print("[ERROR] bruceclaw.py not found in", mimo_dir)

def run(cmd, t=10):
    try: return subprocess.run(cmd,shell=True,capture_output=True,text=True,timeout=t).stdout
    except: return "error"

def mimo_chat(msg):
    """Talk to MiMo by running bruceclaw.py with the message as input."""
    mimo_dir = os.path.join(HOME, "bruceclaw")
    bruceclaw_py = os.path.join(mimo_dir, "bruceclaw.py")
    if not os.path.exists(bruceclaw_py):
        return "bruceclaw.py not found at " + bruceclaw_py
    try:
        result = subprocess.run(
            ["python3", "bruceclaw.py"],
            input=msg + "\nquit\n",
            capture_output=True,
            text=True,
            timeout=30,
            cwd=mimo_dir
        )
        output = result.stdout + result.stderr
        # Extract bot responses (lines after "bot> ")
        lines = output.split("\n")
        replies = []
        for line in lines:
            line = line.strip()
            if line.startswith("bot> "):
                replies.append(line[5:])
            elif line.startswith("you>") or line.startswith("~/") or not line:
                continue
            elif "LLM" in line or "Connected" in line or "Error" in line or "APK" in line:
                continue
            elif line in ("Hey, I'm BruceClaw.", "Say my name or type a command. Type 'help' for what I can do.",
                         "I can control your phone — open apps, tap, type, scroll, swipe.",
                         "Goodbye."):
                continue
            elif replies:  # Only add non-system lines after we have replies
                replies.append(line)
        return "\n".join(replies) if replies else output.strip()[-500:]
    except subprocess.TimeoutExpired:
        return "MiMo timed out (30s)"
    except Exception as e:
        return f"Error: {e}"

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
            self.js({"ok":True,"screen":sz})
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
#c{flex:1;overflow-y:auto;padding:10px;display:flex;flex-direction:column;gap:8px}
.m{max-width:85%;padding:10px 14px;border-radius:12px;font-size:16px;line-height:1.4;white-space:pre-wrap;word-wrap:break-word}
.mu{align-self:flex-end;background:#ff6600;color:#fff}
.mb{align-self:flex-start;background:#222;color:#eee;border:1px solid #333}
.me{border-color:#f44;color:#f88;font-size:13px}
.mi{border-color:#0f8;color:#0f8;font-size:13px}
#i{padding:8px;background:#181818;border-top:2px solid #ff6600;display:flex;gap:6px}
#i input{flex:1;background:#222;border:1px solid #444;color:#fff;padding:10px;border-radius:10px;font-size:16px}
#i button{background:#ff6600;color:#fff;border:none;padding:10px 18px;border-radius:10px;font-size:15px;font-weight:700}
#n{display:flex;background:#111;border-top:1px solid #333}
#n a{flex:1;text-align:center;padding:10px;color:#666;text-decoration:none;font-size:13px;font-weight:700}
#n a.on{color:#ff6600}
#ctl{padding:8px;background:#181818;display:flex;flex-wrap:wrap;gap:6px;justify-content:center;display:none}
.b{background:#222;color:#ff6600;border:1px solid #ff6600;padding:8px 12px;border-radius:8px;font-size:12px;font-weight:700;cursor:pointer}
#si{width:100%;border-radius:8px;border:1px solid #333;display:none;margin-bottom:8px}
</style></head><body>
<div id="h"><h1>BRUCECLAW</h1><span class="st" id="st">...</span></div>
<div id="c"><div class="mb">Type below to talk to MiMo.</div></div>
<div id="i"><input id="m" placeholder="Message..." onkeydown="if(event.key==='Enter')send()"><button onclick="send()">SEND</button></div>
<div id="ctl"><img id="si"><button class="b" onclick="ss()">SCREEN</button><button class="b" onclick="go('/answer')">ANSWER</button><button class="b" onclick="go('/hangup')">HANGUP</button><button class="b" onclick="go('/home')">HOME</button><button class="b" onclick="go('/back')">BACK</button><button class="b" onclick="go('/scroll/down')">SCROLL DN</button></div>
<div id="n"><a href="/" class="on">CHAT</a><a href="/?phone=1">PHONE</a></div>
<script>
var phone=location.search.includes("phone=1");
if(phone){document.getElementById("n").children[0].className="";document.getElementById("n").children[1].className="on";document.getElementById("ctl").style.display="flex";document.getElementById("si").style.display="block";}
function add(t,c){var d=document.createElement("div");d.className="m "+c;d.textContent=t;document.getElementById("c").appendChild(d);document.getElementById("c").scrollTop=99999;}
function send(){var m=document.getElementById("m").value.trim();if(!m)return;add(m,"mu");document.getElementById("m").value="";add("Thinking...","mi");
fetch("/chat",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({message:m})}).then(r=>r.json()).then(d=>{var c=document.getElementById("c");if(c.lastChild)c.removeChild(c.lastChild);add(d.reply||"No response","mb");}).catch(e=>{var c=document.getElementById("c");if(c.lastChild)c.removeChild(c.lastChild);add("Error: "+e,"me");});}
function go(u){fetch(u).then(r=>r.json()).then(d=>add(JSON.stringify(d),"mi"));}
function ss(){fetch("/screenshot").then(r=>r.json()).then(d=>{if(d.img){var i=document.getElementById("si");i.src="data:image/png;base64,"+d.img;i.style.display="block";}});}
fetch("/status").then(r=>r.json()).then(d=>{document.getElementById("st").textContent="OK "+d.screen;}).catch(()=>{document.getElementById("st").textContent="OFFLINE";});
</script></body></html>"""

if __name__ == "__main__":
    print("BruceClaw Chat + Phone Control")
    print(f"Chat: http://localhost:{PORT}")
    print(f"Phone: http://localhost:{PORT}?phone=1")
    ensure_mimo()  # Check if MiMo is running, start if not
    HTTPServer(("0.0.0.0",PORT),H).serve_forever()
