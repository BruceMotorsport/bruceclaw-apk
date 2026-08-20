#!/usr/bin/env python3
"""HTML UI for MiMo Superagent — PWA enabled."""

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
