"""
LLM Client — connects to OpenRouter, MiMo, or OpenCode Zen.
Runs in background, brain uses it when ready.
"""

import json
import urllib.request
import urllib.error


class LLMClient:
    def __init__(self, provider="mimo", model="mimo-v2.5", api_key="", endpoint="", system_prompt=""):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.endpoint = endpoint or "https://opencode.ai/zen/go/v1/chat/completions"
        self.system_prompt = system_prompt
        self.history = []

    def chat(self, user_message: str) -> str:
        """Send message to LLM, get response."""
        self.history.append({"role": "user", "content": user_message})

        messages = []
        if self.system_prompt:
            messages.append({"role": "system", "content": self.system_prompt})
        messages.extend(self.history[-20:])  # Keep last 20 messages

        payload = json.dumps({
            "model": self.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1024,
        }).encode()

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120.0.0.0 Mobile Safari/537.36",
        }

        req = urllib.request.Request(self.endpoint, data=payload, headers=headers)

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode())
                reply = data["choices"][0]["message"]["content"]
                self.history.append({"role": "assistant", "content": reply})
                return reply
        except urllib.error.HTTPError as e:
            body = e.read().decode() if e.fp else ""
            raise Exception(f"HTTP {e.code}: {body[:200]}")
        except Exception as e:
            raise Exception(f"LLM request failed: {e}")
