#!/usr/bin/env python3
"""
Support webhook — MiMo calls this when she needs help.
Listens on port 8888. MiMo sends: curl http://<PC_IP>:8888/support?question=...
Answers questions directly using shell commands and web search.
"""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import subprocess, os, platform, datetime

class SupportHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path == "/support":
            params = parse_qs(parsed.query)
            question = params.get("question", [""])[0]
            if not question:
                self.respond(400, {"error": "missing ?question= parameter"})
                return
            print(f"[SUPPORT] MiMo asked: {question}")
            answer = self.answer_question(question)
            self.respond(200, {"answer": answer})
        elif parsed.path == "/health":
            self.respond(200, {"ok": True, "service": "simone-support"})
        else:
            self.respond(404, {"error": "not found"})
    
    def answer_question(self, question):
        q = question.lower().strip()
        try:
            # Time
            if "time" in q or "date" in q or "what day" in q:
                now = datetime.datetime.now()
                return f"PC time: {now.strftime('%Y-%m-%d %H:%M:%S')} ({platform.node()})"
            # IP
            if "ip" in q:
                r = subprocess.run(["ipconfig"], capture_output=True, text=True, timeout=5)
                lines = [l.strip() for l in r.stdout.split("\n") if "IPv4" in l]
                return "\n".join(lines) if lines else "No IP found"
            # Memory/RAM
            if "memory" in q or "ram" in q:
                r = subprocess.run(["wmic", "OS", "get", "FreePhysicalMemory,TotalVisibleMemorySize", "/ value"], capture_output=True, text=True, timeout=5)
                return r.stdout.strip() if r.stdout else "Can't get memory info"
            # Disk
            if "disk" in q or "space" in q:
                r = subprocess.run(["wmic", "logicaldisk", "get", "size,freespace,caption", "/value"], capture_output=True, text=True, timeout=5)
                return r.stdout.strip() if r.stdout else "Can't get disk info"
            # Process
            if "process" in q or "running" in q:
                r = subprocess.run(["tasklist", "/FI", "STATUS eq RUNNING"], capture_output=True, text=True, timeout=5)
                lines = r.stdout.split("\n")[:15]
                return "\n".join(lines)
            # Default: run as shell command
            r = subprocess.run(question, shell=True, capture_output=True, text=True, timeout=15)
            out = r.stdout.strip() or r.stderr.strip() or "No output"
            return out[:2000]
        except Exception as e:
            return f"Error: {e}"
    
    def respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        pass

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 9876), SupportHandler)
    print("Simone support webhook running on port 9876")
    server.serve_forever()
