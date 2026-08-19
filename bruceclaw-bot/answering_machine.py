#!/usr/bin/env python3
"""
BruceClaw Answering Machine
Runs as background thread. Detects calls, answers, talks via MiMo.
Bot fills silence while MiMo thinks.
"""
import os, json, time, subprocess, threading, random

HOME = os.path.expanduser("~")
FILLERS = [
    "Hmm, let me think about that...",
    "Ok, give me a second...",
    "Let me check on that...",
    "Hmm, one moment...",
    "Ok hold on, looking into it...",
    "Let me see...",
    "Hmm, that's interesting...",
    "Ok, bear with me...",
    "Let me think...",
    "Hmm, checking now...",
]
GREETINGS = [
    "Hey, this is BruceClaw, Bruce's AI assistant. How can I help?",
    "Hi there, Bruce's phone. He's busy right now but I can help. What do you need?",
    "Hello! Bruce can't talk right now. I'm his AI assistant. What can I do for you?",
]

def speak(text):
    """Speak text using termux TTS."""
    cleaned = text.replace("#","").replace("*","").replace("/","")
    try:
        subprocess.run(["termux-tts-speak", cleaned], timeout=15)
    except: pass

def answer_call():
    """Answer incoming call."""
    subprocess.run(["input", "keyevent", "5"])

def hangup():
    """Hang up."""
    subprocess.run(["input", "keyevent", "6"])

def get_call_state():
    """Check if phone is in a call."""
    try:
        r = subprocess.run(["termux-telephony-call-state"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip()
    except:
        return "idle"

def listen_audio(duration=5):
    """Record audio from mic."""
    path = f"{HOME}/call_audio.wav"
    try:
        subprocess.run(["termux-microphone-record", "-l", str(duration), "-f", path], timeout=duration + 5)
        if os.path.exists(path):
            size = os.path.getsize(path)
            os.remove(path)
            return size > 1000  # Return True if we got actual audio
    except: pass
    return False

def check_incoming():
    """Check for incoming calls via call log."""
    try:
        r = subprocess.run(["termux-call-log", "-l", "1"], capture_output=True, text=True, timeout=5)
        data = json.loads(r.stdout)
        if data and data[0].get("type") == "INCOMING":
            return data[0]
    except: pass
    return None

class AnsweringMachine:
    def __init__(self):
        self.running = False
        self.in_call = False
        self.enabled = False
        self.mimo_chat = None  # Set by chat.py

    def start(self):
        self.running = True
        threading.Thread(target=self._monitor, daemon=True).start()

    def stop(self):
        self.running = False

    def _monitor(self):
        """Monitor for incoming calls."""
        last_call_id = None
        while self.running:
            try:
                if not self.enabled:
                    time.sleep(5)
                    continue

                state = get_call_state()
                
                if state == "ringing" and not self.in_call:
                    # Incoming call!
                    call = check_incoming()
                    caller = call.get("name", "Unknown") if call else "Unknown"
                    number = call.get("phone_number", "") if call else ""
                    
                    print(f"[CALL] Incoming from {caller} ({number})")
                    
                    # Answer after brief delay (natural)
                    time.sleep(2)
                    answer_call()
                    self.in_call = True
                    
                    # Greet caller
                    greeting = random.choice(GREETINGS)
                    speak(greeting)
                    
                    # Conversation loop
                    self._handle_call(caller, number)
                    
                elif state == "idle" and self.in_call:
                    # Call ended
                    print("[CALL] Call ended")
                    self.in_call = False

                time.sleep(3)
                
            except Exception as e:
                print(f"[CALL] Monitor error: {e}")
                time.sleep(5)

    def _handle_call(self, caller, number):
        """Handle active call — listen, think, respond."""
        while self.in_call:
            try:
                state = get_call_state()
                if state == "idle":
                    self.in_call = False
                    break

                # Listen for caller speaking
                print("[CALL] Listening...")
                has_audio = listen_audio(5)
                
                if has_audio:
                    # Caller said something — process it
                    # Bot fills silence while MiMo thinks
                    filler = random.choice(FILLERS)
                    speak(filler)
                    
                    # Get MiMo response
                    if self.mimo_chat:
                        # In real implementation, this would be STT → MiMo → TTS
                        # For now, acknowledge
                        response = f"I heard you. Let me look into that."
                        # Give MiMo a moment to think
                        time.sleep(3)
                        speak(response)
                    else:
                        speak("I'm having trouble connecting. Call back later.")
                        hangup()
                        self.in_call = False
                        break
                else:
                    # No audio — caller might be waiting
                    time.sleep(2)

            except Exception as e:
                print(f"[CALL] Error: {e}")
                time.sleep(3)

if __name__ == "__main__":
    am = AnsweringMachine()
    am.enabled = True
    am.start()
    print("Answering machine started. Waiting for calls...")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        am.stop()
