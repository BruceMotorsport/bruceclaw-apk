#!/usr/bin/env python3
"""HTML UI for MiMo Superagent — PWA enabled. HTML is inlined."""

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
