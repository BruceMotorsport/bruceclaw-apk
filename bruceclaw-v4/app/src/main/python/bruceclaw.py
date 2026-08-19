#!/usr/bin/env python3
"""
BruceClaw v4 — Python Brain
Boots instantly, greets user, hands off to LLM when ready.
"""

import json
import socket
import threading
import time
import sys
import os

# === INSTANT BOOT — no LLM dependency ===
BOOT_MESSAGES = [
    "BruceClaw ready.",
    "Say 'Bruce' to wake me up.",
    "Or just type your message.",
]

WELCOME = """
Hey, I'm BruceClaw.

I can control your phone — open apps, tap, type, scroll, swipe.

Say my name or type a command. Type 'help' for what I can do.
""".strip()

HELP_TEXT = """
Commands:
  open <app>       — Open an app (chrome, settings, camera, etc.)
  tap <x> <y>      — Tap screen coordinates
  swipe <dir>      — Swipe up/down/left/right
  type <text>      — Type text into current field
  scroll <dir>     — Scroll up or down
  press <key>      — Press back/home/enter/tab/delete
  find <text>      — Find element by text and tap it
  screen           — Show screen tree
  help             — Show this help
  quit             — Close connection
""".strip()


class BruceClawBrain:
    """Main brain — handles commands locally or forwards to LLM."""

    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)
        self.name = self.config.get("wake_word", "Bruce")
        self.llm_ready = False
        self.llm_client = None
        self.phone = PhoneController()

        # Start LLM connection in background
        threading.Thread(target=self._init_llm, daemon=True).start()

    def _load_config(self, path):
        default = {
            "wake_word": "Bruce",
            "wake_word_aliases": ["Bruce", "Hey Bruce", "Hey BruceClaw"],
            "voice_trained": False,
            "voice_samples": [],
            "provider": "mimo",
            "model": "mimo-v2.5",
            "api_key": "",
            "endpoint": "https://opencode.ai/zen/go/v1/chat/completions",
            "system_prompt": (
                "You are BruceClaw, Bruce's phone assistant. "
                "You can control the phone: open apps, tap, type, swipe, scroll. "
                "Keep responses short. Bruce hates verbose. "
                "You are direct, calm, no filler."
            ),
        }
        if os.path.exists(path):
            with open(path) as f:
                saved = json.load(f)
                default.update(saved)
        return default

    def _save_config(self):
        with open("config.json", "w") as f:
            json.dump(self.config, f, indent=2)

    def _init_llm(self):
        """Connect to LLM in background. Takes a few seconds."""
        try:
            from llm_client import LLMClient
            self.llm_client = LLMClient(
                provider=self.config["provider"],
                model=self.config["model"],
                api_key=self.config["api_key"],
                endpoint=self.config["endpoint"],
                system_prompt=self.config["system_prompt"],
            )
            self.llm_ready = True
            print("[LLM] Connected — " + self.config["model"])
        except Exception as e:
            print(f"[LLM] Failed to connect: {e}")
            print("[LLM] Running in local-only mode")

    def handle_input(self, user_input: str) -> str:
        """Process user input — local commands or LLM."""
        text = user_input.strip()

        if not text:
            return ""

        # Local commands (instant, no LLM needed)
        lower = text.lower()

        if lower in ("help", "?"):
            return HELP_TEXT

        if lower in ("quit", "exit", "bye"):
            return "Goodbye."

        if lower == "screen":
            return self.phone.get_screen_tree()

        # Check if LLM is ready
        if not self.llm_ready:
            return self._local_fallback(text)

        # Forward to LLM
        return self._ask_llm(text)

    def _local_fallback(self, text: str) -> str:
        """Handle basic commands locally when LLM isn't ready."""
        lower = text.lower()

        if lower.startswith("open "):
            app = text[5:].strip()
            result = self.phone.open_app(app)
            return f"Opening {app}... {result}"

        if lower.startswith("tap "):
            parts = text[4:].strip().split()
            if len(parts) == 2:
                x, y = float(parts[0]), float(parts[1])
                self.phone.tap(x, y)
                return f"Tapped ({x}, {y})"
            return "Usage: tap <x> <y>"

        if lower.startswith("type "):
            t = text[5:].strip()
            self.phone.type_text(t)
            return f"Typed: {t}"

        if lower.startswith("swipe "):
            direction = text[6:].strip()
            self.phone.scroll(direction)
            return f"Swiped {direction}"

        if lower.startswith("press "):
            key = text[6:].strip()
            self.phone.press_key(key)
            return f"Pressed {key}"

        return f"LLM connecting... Try basic commands: open, tap, type, swipe, press"

    def _ask_llm(self, text: str) -> str:
        """Send to LLM and execute any phone commands it returns."""
        try:
            response = self.llm_client.chat(text)

            # Check if LLM wants to control the phone
            # LLM returns JSON actions like: {"action": "tap", "x": 500, "y": 300}
            lines = response.split("\n")
            result_lines = []
            for line in lines:
                line = line.strip()
                if line.startswith("{"):
                    try:
                        action = json.loads(line)
                        cmd_result = self.phone.execute(action)
                        result_lines.append(cmd_result)
                    except json.JSONDecodeError:
                        result_lines.append(line)
                else:
                    result_lines.append(line)

            return "\n".join(result_lines) if result_lines else response

        except Exception as e:
            return f"LLM error: {e}"


class PhoneController:
    """Send commands to the Android APK's Accessibility Service."""

    def __init__(self, host="127.0.0.1", port=9999):
        self.host = host
        self.port = port

    def _send(self, cmd: dict) -> str:
        """Send command to APK server."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(5)
            s.connect((self.host, self.port))
            s.sendall((json.dumps(cmd) + "\n").encode())
            response = s.recv(4096).decode().strip()
            s.close()
            return response
        except ConnectionRefusedError:
            return "ERROR: APK server not running. Open BruceClaw app."
        except Exception as e:
            return f"ERROR: {e}"

    def tap(self, x: float, y: float):
        return self._send({"action": "tap", "x": x, "y": y})

    def swipe(self, x1, y1, x2, y2, duration=300):
        return self._send({"action": "swipe", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration": duration})

    def type_text(self, text):
        return self._send({"action": "type", "text": text})

    def press_key(self, key):
        return self._send({"action": "press", "key": key})

    def scroll(self, direction="down"):
        return self._send({"action": "scroll", "direction": direction})

    def find_and_tap(self, text):
        return self._send({"action": "find_and_tap", "text": text})

    def open_app(self, app_name):
        # Map common names to package names
        packages = {
            "chrome": "com.android.chrome",
            "camera": "com.android.camera",
            "settings": "com.android.settings",
            "calculator": "com.android.calculator2",
            "maps": "com.google.android.apps.maps",
            "youtube": "com.google.android.youtube",
            "whatsapp": "com.whatsapp",
            "telegram": "org.telegram.messenger",
            "gallery": "com.google.android.apps.photos",
            "files": "com.google.android.apps.nbu.files",
            "phone": "com.google.android.dialer",
            "contacts": "com.google.android.contacts",
            "messages": "com.google.android.apps.messaging",
            "play store": "com.android.vending",
        }
        pkg = packages.get(app_name.lower(), app_name)
        return self._send({"action": "open_app", "package": pkg})

    def get_screen_tree(self):
        return self._send({"action": "screen_tree"})

    def execute(self, action: dict):
        """Execute an action dict from LLM."""
        act = action.get("action", "")
        if act == "tap":
            return self.tap(action["x"], action["y"])
        elif act == "type":
            return self.type_text(action["text"])
        elif act == "swipe":
            return self.swipe(action["x1"], action["y1"], action["x2"], action["y2"])
        elif act == "scroll":
            return self.scroll(action.get("direction", "down"))
        elif act == "press":
            return self.press_key(action["key"])
        elif act == "open":
            return self.open_app(action["app"])
        elif act == "find_and_tap":
            return self.find_and_tap(action["text"])
        return f"Unknown action: {act}"


def main():
    """Instant boot entry point."""
    print(WELCOME)
    print()

    brain = BruceClawBrain()

    # Check if APK server is running
    import socket
    apk_online = False
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        s.connect(("127.0.0.1", 9999))
        s.close()
        apk_online = True
        print("[APK] Connected on port 9999")
    except:
        print("[APK] Not running — phone control unavailable")
        print("      Open BruceClaw app and tap START SERVER")
    print()

    # Always interactive — type commands, get responses
    while True:
        try:
            user = input("you> ").strip()
            if not user:
                continue
            response = brain.handle_input(user)
            if response:
                print(f"bot> {response}")
            if response == "Goodbye.":
                break
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye.")
            break


if __name__ == "__main__":
    main()
