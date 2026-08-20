#!/usr/bin/env python3
"""HTML UI for MiMo Superagent — PWA enabled."""

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

# Read the standalone HTML file
import os
_html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "mimo_pwa.html")
with open(_html_path, "r", encoding="utf-8") as _f:
    HTML_PAGE = _f.read()
