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
       