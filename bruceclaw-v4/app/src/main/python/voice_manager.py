"""
Voice Manager — wake word detection + STT + TTS.

Wake word approach (no constant beeping):
1. Android SpeechRecognizer listens in BACKGROUND mode
2. Partial results come in real-time
3. We only check if partial text contains the wake word
4. When wake word detected → activate full STT
5. When user stops talking → send to LLM

Voice training:
- Record 5 samples of user saying wake word
- Store as voice profile (MFCC features)
- Only respond to matching voice
"""

import json
import os
import threading
import time


class VoiceManager:
    """Manages wake word detection, STT, and TTS."""

    def __init__(self, config_path="config.json"):
        self.config = self._load_config(config_path)
        self.wake_word = self.config.get("wake_word", "Bruce")
        self.wake_aliases = self.config.get("wake_word_aliases", ["Bruce", "Hey Bruce"])
        self.voice_trained = self.config.get("voice_trained", False)
        self.voice_samples = self.config.get("voice_samples", [])

        self.is_listening = False
        self.is_speaking = False
        self.on_wake = None  # Callback when wake word detected
        self.on_command = None  # Callback when command received
        self.on_result = None  # Callback for STT results

    def _load_config(self, path):
        if os.path.exists(path):
            with open(path) as f:
                return json.load(f)
        return {}

    def _save_config(self):
        self.config["wake_word"] = self.wake_word
        self.config["wake_word_aliases"] = self.wake_aliases
        self.config["voice_trained"] = self.voice_trained
        self.config["voice_samples"] = self.voice_samples
        with open("config.json", "w") as f:
            json.dump(self.config, f, indent=2)

    # === WAKE WORD ===

    def set_wake_word(self, word: str):
        """Set custom wake word."""
        self.wake_word = word.strip()
        self.wake_aliases = [word, f"Hey {word}"]
        self._save_config()

    def check_wake_word(self, text: str) -> bool:
        """Check if text contains wake word."""
        text_lower = text.lower().strip()
        for alias in self.wake_aliases:
            if alias.lower() in text_lower:
                return True
        return False

    # === VOICE TRAINING ===

    def start_voice_training(self):
        """Start voice training — record samples of wake word."""
        print(f"Say '{self.wake_word}' five times...")
        print("Recording sample 1/5...")
        # In real implementation, this triggers Android audio recording
        # and extracts MFCC features from each sample
        return "ready"

    def save_voice_sample(self, audio_features):
        """Save a voice sample for speaker verification."""
        self.voice_samples.append(audio_features)
        if len(self.voice_samples) >= 5:
            self.voice_trained = True
            self._save_config()
            return "Voice trained! I'll only respond to your voice."
        return f"Sample {len(self.voice_samples)}/5 recorded. Say '{self.wake_word}' again."

    def verify_voice(self, audio_features) -> bool:
        """Check if voice matches trained profile."""
        if not self.voice_trained or not self.voice_samples:
            return True  # No training = accept all voices

        # Simple cosine similarity check
        # In real implementation, use speaker embedding comparison
        for sample in self.voice_samples:
            similarity = self._cosine_similarity(audio_features, sample)
            if similarity > 0.85:
                return True
        return False

    def _cosine_similarity(self, a, b):
        """Compare two feature vectors."""
        if len(a) != len(b):
            return 0.0
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x * x for x in a) ** 0.5
        norm_b = sum(x * x for x in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    # === LISTENING STATE ===

    def get_status(self) -> dict:
        return {
            "wake_word": self.wake_word,
            "voice_trained": self.voice_trained,
            "samples": len(self.voice_samples),
            "listening": self.is_listening,
        }
