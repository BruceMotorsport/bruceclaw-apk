#!/usr/bin/env python3
"""MiMo Superagent - Flipper Zero on a Phone"""
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
