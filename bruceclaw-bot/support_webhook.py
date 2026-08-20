#!/usr/bin/env python3
"""
Support webhook — MiMo calls this when she needs help from Simone/Hermes.
Listens on port 8888. MiMo sends: curl http://<PC_IP>:8888/support?question=...
"""
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import subprocess, os

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
            # Forward to Hermes via terminal
            try:
                result = subprocess.run(
                    ["hermes", "send", question],
                    capture_output=True, text=True, timeout=60
                )
                answer = result.stdout.strip() or result.stderr.strip() or "No response"
            except Exception as e:
                answer = f"Error contacting Simone: {e}"
            self.respond(200, {"answer": answer})
        elif parsed.path == "/health":
            self.respond(200, {"ok": True, "service": "simone-support"})
        else:
            self.respond(404, {"error": "not found"})
    
    def respond(self, code, data):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def log_message(self, format, *args):
        pass  # Quiet

if __name__ == "__main__":
    server = HTTPServer(("0.0.0.0", 8888), SupportHandler)
    print("Simone support webhook running on port 8888")
    server.serve_forever()
