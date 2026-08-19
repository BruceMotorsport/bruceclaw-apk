"""
LLM Client — uses curl for HTTPS (python ssl broken on phone).
"""
import json, subprocess, os

class LLMClient:
    def __init__(self, provider="mimo", model="mimo-v2.5", api_key="", endpoint="", system_prompt=""):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.endpoint = endpoint or "https://opencode.ai/zen/go/v1/chat/completions"
        self.system_prompt = system_prompt
        self.history = []

    def chat(self, user_message: str) -> str:
        self.history.append({"role": "user", "content": user_message})
        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(self.history[-20:])
        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        })
        tmp = "/tmp/llm_payload.json"
        open(tmp, "w").write(payload)
        cmd = [
            "curl", "-s", "--max-time", "30",
            "-X", "POST", self.endpoint,
            "-H", "Content-Type: application/json",
            "-H", f"Authorization: Bearer {self.api_key}",
            "-d", f"@{tmp}"
        ]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=35)
        if r.returncode != 0:
            raise Exception(f"HTTP error: {r.stderr[:200]}")
        data = json.loads(r.stdout)
        reply = data["choices"][0]["message"]["content"]
        self.history.append({"role": "assistant", "content": reply})
        return reply
