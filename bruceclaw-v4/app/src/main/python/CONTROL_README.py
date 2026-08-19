# BruceClaw v4 — Phone Control via Accessibility Service
#
# WHY Accessibility Service (not USB HID):
# - No root needed
# - No Magisk module needed
# - User enables ONCE in Settings > Accessibility
# - APK can then: tap, swipe, type, scroll, read screen
# - Works on ALL Android phones
# - Same approach as Tasker, Auto.js, MacroDroid
#
# HOW IT WORKS:
# 1. Python bot (LLM) decides: "I need to tap the search bar"
# 2. Python sends: {"action": "tap", "x": 540, "y": 1200}
# 3. APK receives command via WebSocket (local or remote)
# 4. Accessibility Service performs the tap
# 5. Phone behaves exactly as if user tapped
#
# CAPABILITIES:
# - tap(x, y) — tap any coordinate
# - swipe(x1, y1, x2, y2, duration_ms) — swipe gesture
# - type_text("hello world") — type via IME
# - press_key(keycode) — press Back, Home, Enter, etc.
# - scroll(direction) — scroll up/down
# - find_and_tap(text) — find element by text, tap it
# - screenshot() — capture current screen
# - get_screen_tree() — read all UI elements
