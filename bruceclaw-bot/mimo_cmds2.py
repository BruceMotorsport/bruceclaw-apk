#!/usr/bin/env python3
"""Device commands part 2: battery, screen, comms, camera, media."""
from mimo_base import shell_exec

def cmd_battery(): return "Battery:\n" + shell_exec("termux-battery-status 2>/dev/null || cat /sys/class/power_supply/battery/capacity 2>/dev/null")
def cmd_brightness(val): shell_exec("termux-brightness " + val + " 2>/dev/null"); return "Brightness: " + val
def cmd_volume(val): shell_exec("termux-volume media " + val + " 2>/dev/null"); return "Volume: " + val
def cmd_screen_on(): return "Screen: " + shell_exec("input keyevent KEYCODE_WAKEUP 2>/dev/null")
def cmd_screen_off(): return "Screen: " + shell_exec("input keyevent KEYCODE_SLEEP 2>/dev/null")
def cmd_location(): return "Location:\n" + shell_exec("termux-location 2>/dev/null || echo not available")
def cmd_contacts(): return "Contacts:\n" + shell_exec("termux-contact-list 2>/dev/null | head -30 || echo not available")
def cmd_call(num): return "Calling: " + shell_exec("termux-telephony-call " + num + " 2>/dev/null || am start -a android.intent.action.CALL -d tel:" + num + " 2>/dev/null")
def cmd_sms(num, msg):
    shell_exec("termux-sms-send -n " + num + " '" + msg + "' 2>/dev/null")
    return "SMS sent to " + num
def cmd_photo(): return "Photo: " + shell_exec("termux-camera-photo -f /sdcard/DCIM/mimo.jpg 2>/dev/null && echo saved")
def cmd_screenshot(): return "Screenshot: " + shell_exec("screencap -p /sdcard/mimo_ss.png 2>/dev/null && echo saved")
def cmd_vibrate(ms): return "Vibrate: " + shell_exec("termux-vibrate -d " + ms + " 2>/dev/null")
def cmd_clipboard(): return "Clipboard:\n" + shell_exec("termux-clipboard-get 2>/dev/null || echo empty")
def cmd_clip(text): shell_exec("termux-clipboard-set '" + text + "' 2>/dev/null"); return "Clipboard set"
def cmd_music_pause(): return "Music: " + shell_exec("input keyevent KEYCODE_MEDIA_PAUSE 2>/dev/null")
def cmd_music_play(): return "Music: " + shell_exec("input keyevent KEYCODE_MEDIA_PLAY 2>/dev/null")
def cmd_music_next(): return "Music: " + shell_exec("input keyevent KEYCODE_MEDIA_NEXT 2>/dev/null")
def cmd_music_prev(): return "Music: " + shell_exec("input keyevent KEYCODE_MEDIA_PREVIOUS 2>/dev/null")
def cmd_notify(title, msg): shell_exec("termux-notification -t '" + title + "' -c '" + msg + "' 2>/dev/null"); return "Notification sent"
def cmd_notifications(): return "Notifications:\n" + shell_exec("termux-notification-list 2>/dev/null || echo none")
def cmd_torch_on(): return "Torch: " + shell_exec("termux-torch on 2>/dev/null || echo not available")
def cmd_torch_off(): return "Torch: " + shell_exec("termux-torch off 2>/dev/null || echo not available")
def cmd_nfc_on(): return "NFC: " + shell_exec("svc nfc enable 2>/dev/null || echo enable manually")
def cmd_nfc_off(): return "NFC: " + shell_exec("svc nfc disable 2>/dev/null || echo disable manually")
