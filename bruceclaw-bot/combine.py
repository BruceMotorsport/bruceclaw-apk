#!/usr/bin/env python
"""Combine all MiMo modules into one chat.py for phone deployment."""
import re

parts = []

# Read each module in order
files = [
    "mimo_base.py",
    "mimo_cmds1.py", 
    "mimo_cmds2.py",
    "mimo_cmds3.py",
    "mimo_dispatch.py",
]

for f in files:
    with open(f) as fh:
        content = fh.read()
    # Remove shebang and docstring
    content = re.sub(r'^#!/.*\n', '', content)
    content = re.sub(r'^"""[^"]*"""', '', content, flags=re.DOTALL)
    # Remove imports (they'll be at the top)
    content = re.sub(r'^from mimo_\w+ import.*\n', '', content, flags=re.MULTILINE)
    content = re.sub(r'^import os\n', '', content, flags=re.MULTILINE)
    parts.append(content.strip())

# Read mimo_html.py for HTML, MANIFEST, SERVICE_WORKER
with open("mimo_html.py") as fh:
    html = fh.read()
html = re.sub(r'^#!/.*\n', '', html)
html = re.sub(r'^"""[^"]*"""', '', html, flags=re.DOTALL)
parts.append(html.strip())

# Read chat.py for server + telegram bot
with open("chat.py") as fh:
    server = fh.read()
server = re.sub(r'^#!/.*\n', '', server)
server = re.sub(r'^"""[^"]*"""', '', server, flags=re.DOTALL)
# Remove duplicate imports from chat.py
server = re.sub(r'^from mimo_\w+ import.*\n', '', server, flags=re.MULTILINE)
parts.append(server.strip())

combined = '''#!/usr/bin/env python3
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

''' + "\n\n".join(parts) + '''

if __name__ == "__main__":
    os.system("termux-wake-lock 2>/dev/null")
    os.system("termux-notification -t MiMo -c 'Superagent online' 2>/dev/null")
    threading.Thread(target=wait_for_brain, daemon=True).start()
    threading.Thread(target=telegram_poll, daemon=True).start()
    run_server()
'''

with open("chat_deploy.py", "w") as f:
    f.write(combined)

print("Combined chat_deploy.py:", len(combined), "bytes")
