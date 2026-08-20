#!/usr/bin/env python3
"""MiMo Superagent - Main Server. Imports all modules."""
import os, sys, json, time, threading, urllib.request, urllib.parse
from http.server import SimpleHTTPRequestHandler, HTTPServer

# Import our modules
from mimo_base import shell_exec, log_transcript, TRANSCRIPT, SUPPORT_URL
from mimo_dispatch import handle_command
from mimo_html import HTML_PAGE, MANIFEST, SERVICE_WORKER

HOST, PORT = "0.0.0.0", 8080
TG_TOKEN = os.environ.get("TG_TOKEN", "")
TG_CHAT_ID = os.environ.get("TG_CHAT_ID", "")
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
