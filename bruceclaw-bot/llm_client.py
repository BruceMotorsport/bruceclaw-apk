import json, subprocess, os

class LLMClient:
    def __init__(self, provider="mimo", model="mimo-v2.5", api_key="", endpoint="", system_prompt=""):
        self.provider = provider
        self.model = model
        self.api_key = api_key
        self.endpoint = endpoint or "https://opencode.ai/zen/go/v1/chat/completions"
        self.system_prompt = system_prompt
        self.history = []

    def chat(self, user_message):
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
        r = subprocess.run(
            ["curl", "-s", "--max-time", "30", "-X", "POST", self.endpoint,
             "-H", "Content-Type: application/json",
             "-H", "Authorization: Bearer " + self.api_key,
             "-d", "@" + tmp],
            capture_output=True, text=True, timeout=35
        )
        if r.returncode != 0:
            raise Exception(f"HTTP error: {r.stderr[:200]}")
        data = json.loads(r.stdout)
        choices = data.get("choices", [])
        if not choices:
            raise Exception("No choices: " + r.stdout[:200])
        msg = choices[0].get("message", {})
        content = msg.get("content") or msg.get("reasoning_content") or "Thinking..."
        self.history.append({"role": "assistant", "content": content})
        return content
