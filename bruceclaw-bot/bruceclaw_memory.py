#!/usr/bin/env python3
"""
BruceClaw v4 — Python Brain WITH MEMORY
Boots instantly, greets user, hands off to LLM when ready.
Remembers conversations and facts in SQLite.
"""
import json
import socket
import threading
import time
import sys
import os
import sqlite3

HOME = os.path.expanduser("~")
DB_PATH = os.path.join(HOME, "bruceclaw", "memory.db")

# === MEMORY SYSTEM ===
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY, role TEXT, content TEXT, ts REAL)")
    conn.execute("CREATE TABLE IF NOT EXISTS facts (key TEXT PRIMARY KEY, value TEXT)")
    conn.commit()
    return conn

def save_msg(conn, role, content):
    conn.execute("INSERT INTO messages (role, content, ts) VALUES (?, ?, ?)", (role, content, time.time()))
    conn.commit()

def get_history(conn, limit=20):
    rows = conn.execute("SELECT role, content FROM messages ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return list(reversed(rows))

def save_fact(conn, key, value):
    conn.execute("INSERT OR REPLACE INTO facts (key, value) VALUES (?, ?)", (key, value))
    conn.commit()

def get_fact(conn, key):
    row = conn.execute("SELECT value FROM facts WHERE key=?", (key,)).fetchone()
    return row[0] if row else None

def get_all_facts(conn):
    return {r[0]: r[1] for r in conn.execute("SELECT key, value FROM facts").fetchall()}

# === INSTANT BOOT ===
WELCOME = """
Hey, I'm BruceClaw.

I can control your phone — open apps, tap, type, scroll, swipe.
I remember our conversations and things you tell me.

Say my name or type a command. Type 'help' for what I can do.
Type 'remember <fact>' to teach me something.
Type 'what do you know' to see what I remember.
""".strip()

HELP_TEXT = """
Commands:
  open <app>        — Open an app
  tap <x> <y>       — Tap screen coordinates
  swipe <dir>       — Swipe up/down/left/right
  type <text>       — Type text into current field
  scroll <dir>      — Scroll up or down
  press <key>       — Press back/home/enter/tab/delete
  find <text>       — Find element by text and tap it
  screen            — Show screen tree
  remember <fact>   — Teach me something
  what do you know  — Show what I remember
  help              — Show this help
  quit              — Close connection
""".strip()


class BruceClawBrain:
    """Main brain — handles commands locally or forwards to LLM. Has memory."""

    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)
        self.name = self.config.get("wake_word", "Bruce")
        self.llm_ready = False
        self.llm_client = None
        self.phone = PhoneController()
        self.conn = init_db()

        # Load facts into system prompt
        facts = get_all_facts(self.conn)
        if facts:
            facts_text = "\n".join(f"- {k}: {v}" for k, v in facts.items())
            self.config["system_prompt"] += f"\n\nThings you know about Bruce:\n{facts_text}"

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
                "Keep responses SHORT. Bruce hates verbose. "
                "You are direct, calm, no filler. "
                "You remember things Bruce tells you."
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
            print(f"[LLM] Failed: {e}")

    def handle_input(self, user_input: str) -> str:
        text = user_input.strip()
        if not text:
            return ""

        lower = text.lower()

        # === LOCAL COMMANDS ===
        if lower in ("help", "?"):
            return HELP_TEXT

        if lower in ("quit", "exit", "bye"):
            return "Goodbye."

        if lower == "screen":
            return self.phone.get_screen_tree()

        # Memory commands
        if lower.startswith("remember "):
            fact = text[9:].strip()
            if "=" in fact:
                key, value = fact.split("=", 1)
                save_fact(self.conn, key.strip(), value.strip())
                return f"Remembered: {key.strip()} = {value.strip()}"
            else:
                save_fact(self.conn, fact, "true")
                return f"Remembered: {fact}"

        if lower in ("what do you know", "what do you remember", "memory"):
            facts = get_all_facts(self.conn)
            if facts:
                lines = [f"- {k}: {v}" for k, v in facts.items()]
                return "Things I know:\n" + "\n".join(lines)
            return "I don't know anything yet. Tell me something with 'remember <fact>'"

        # Save conversation history
        save_msg(self.conn, "user", text)

        # Check if LLM is ready
        if not self.llm_ready:
            return self._local_fallback(text)

        return self._ask_llm(text)

    def _local_fallback(self, text: str) -> str:
        lower = text.lower()
        if lower.startswith("open "):
            app = text[5:].strip()
            return f"Opening {app}... {self.phone.open_app(app)}"
        if lower.startswith("tap "):
            parts = text[4:].strip().split()
            if len(parts) == 2:
                self.phone.tap(float(parts[0]), float(parts[1]))
                return f"Tapped ({parts[0]}, {parts[1]})"
        return "LLM connecting... Try basic commands: open, tap, type, swipe, press"

    def _ask_llm(self, text: str) -> str:
        try:
            # Include conversation history
            history = get_history(self.conn, 20)
            messages = [{"role": "system", "content": self.config["system_prompt"]}]
            for role, content in history:
                messages.append({"role": role, "content": content})

            response = self.llm_client.chat(text)

            # Save response
            save_msg(self.conn, "assistant", response)

            # Check for tool commands
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

    def tap(self, x, y): return self._send({"action": "tap", "x": x, "y": y})
    def swipe(self, x1, y1, x2, y2, dur=300): return self._send({"action": "swipe", "x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration": dur})
    def type_text(self, t): return self._send({"action": "type", "text": t})
    def press_key(self, k): return self._send({"action": "press", "key": k})
    def scroll(self, d="down"): return self._send({"action": "scroll", "direction": d})
    def find_and_tap(self, t): return self._send({"action": "find_and_tap", "text": t})
    def get_screen_tree(self): return self._send({"action": "screen_tree"})

    def open_app(self, name):
        pkgs = {"chrome":"com.android.chrome","camera":"com.android.camera","settings":"com.android.settings","youtube":"com.google.android.youtube","whatsapp":"com.whatsapp","telegram":"org.telegram.messenger","maps":"com.google.android.apps.maps","phone":"com.google.android.dialer","contacts":"com.google.android.contacts","messages":"com.google.android.apps.messaging"}
        return self._send({"action": "open_app", "package": pkgs.get(name.lower(), name)})

    def execute(self, action):
        a = action.get("action","")
        if a=="tap": return self.tap(action["x"],action["y"])
        elif a=="type": return self.type_text(action["text"])
        elif a=="swipe": return self.swipe(action["x1"],action["y1"],action["x2"],action["y2"])
        elif a=="scroll": return self.scroll(action.get("direction","down"))
        elif a=="press": return self.press_key(action["key"])
        elif a=="open": return self.open_app(action["app"])
        elif a=="find_and_tap": return self.find_and_tap(action["text"])
        return f"Unknown: {a}"


def main():
    print(WELCOME)
    print()
    brain = BruceClawBrain()

    import socket as _s
    try:
        _s.socket(_s.AF_INET, _s.SOCK_STREAM).connect(("127.0.0.1", 9999))
        print("[APK] Connected on port 9999")
    except:
        print("[APK] Not running — phone control unavailable")
    print()

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
