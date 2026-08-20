#!/usr/bin/env python3
"""Command dispatcher — maps user text to device commands."""
from mimo_cmds1 import *
from mimo_cmds2 import *
from mimo_cmds3 import *

def handle_command(msg):
    """Check if msg is a device command. Returns string or None."""
    l = msg.strip().lower()

    # Shell
    if l.startswith("shell:") or l.startswith("run:"):
        return cmd_shell(msg.strip().split(":", 1)[1].strip())
    if l.startswith("code:"):
        return cmd_code(msg.strip()[5:].strip())

    # Hardware
    if l in ("usb", "usb devices"): return cmd_usb()
    if l in ("bluetooth", "bt"): return cmd_bluetooth()
    if l == "bt scan": return cmd_bt_scan()
    if l == "bt on": return cmd_bt_on()
    if l == "bt off": return cmd_bt_off()

    # Apps
    if l in ("apps", "list apps"): return cmd_apps()
    if l.startswith("open ") or l.startswith("launch "):
        return cmd_open(msg.strip().split(" ", 1)[1])
    if l.startswith("kill app ") or l.startswith("force stop "):
        return cmd_kill_app(msg.strip().split(" ", 2)[2])

    # WiFi
    if l == "wifi": return cmd_wifi()
    if l == "wifi on": return cmd_wifi_on()
    if l == "wifi off": return cmd_wifi_off()
    if l == "wifi scan": return cmd_wifi_scan()

    # Battery / brightness / volume
    if l in ("battery", "bat"): return cmd_battery()
    if l.startswith("brightness "): return cmd_brightness(msg.strip().split(" ", 1)[1])
    if l.startswith("volume "): return cmd_volume(msg.strip().split(" ", 1)[1])

    # Screen
    if l == "screen on": return cmd_screen_on()
    if l == "screen off": return cmd_screen_off()

    # Location / contacts / comms
    if l in ("location", "gps"): return cmd_location()
    if l in ("contacts", "contact list"): return cmd_contacts()
    if l.startswith("call "): return cmd_call(msg.strip().split(" ", 1)[1])
    if l.startswith("sms "):
        parts = msg.strip().split(" ", 2)
        if len(parts) >= 3: return cmd_sms(parts[1], parts[2])
        return "Usage: sms <number> <message>"

    # Clipboard
    if l in ("clipboard", "clip get"): return cmd_clipboard()
    if l.startswith("clip "): return cmd_clip(msg.strip()[5:].strip())

    # Camera / media
    if l in ("photo", "camera"): return cmd_photo()
    if l in ("screenshot", "screen capture"): return cmd_screenshot()
    if l == "music play": return cmd_music_play()
    if l == "music pause": return cmd_music_pause()
    if l == "music next": return cmd_music_next()
    if l == "music prev": return cmd_music_prev()

    # System
    if l in ("processes", "top"): return cmd_processes()
    if l.startswith("kill ") and l[5:].strip().isdigit():
        return cmd_kill_pid(l[5:].strip())
    if l == "cpu": return cmd_cpu()
    if l in ("ram", "memory"): return cmd_ram()
    if l in ("disk", "storage"): return cmd_disk()
    if l in ("network", "netinfo"): return cmd_network()
    if l == "ip": return cmd_ip()
    if l.startswith("ping "): return cmd_ping(msg.strip().split(" ", 1)[1])
    if l == "uptime": return cmd_uptime()
    if l in ("logs", "logcat"): return cmd_logs()

    # Radio
    if l == "airplane on": return cmd_airplane_on()
    if l == "airplane off": return cmd_airplane_off()
    if l in ("torch on", "flashlight on"): return cmd_torch_on()
    if l in ("torch off", "flashlight off"): return cmd_torch_off()
    if l == "nfc on": return cmd_nfc_on()
    if l == "nfc off": return cmd_nfc_off()
    if l.startswith("vibrate "): return cmd_vibrate(msg.strip().split(" ", 1)[1])

    # Notifications
    if l.startswith("notify "):
        parts = msg.strip().split(" ", 2)
        if len(parts) >= 3: return cmd_notify(parts[1], parts[2])
        return "Usage: notify <title> <msg>"
    if l in ("notifications", "notifs"): return cmd_notifications()

    # Sensors
    if l in ("sensors", "sensor list"): return cmd_sensors()
    if l.startswith("sensor "): return cmd_sensor(msg.strip().split(" ", 1)[1])
    if l in ("cellinfo", "cell towers"): return cmd_cellinfo()
    if l in ("devinfo", "device info"): return cmd_devinfo()

    # Files
    if l.startswith("read:"):
        path = msg.strip()[5:].strip()
        return "File " + path + ":\n" + shell_exec("cat " + path + " 2>/dev/null | head -50")
    if l.startswith("write:"):
        rest = msg.strip()[6:].strip()
        parts = rest.split(" -> ", 1)
        if len(parts) == 2:
            shell_exec("echo '" + parts[1] + "' > " + parts[0])
            return "Written to " + parts[0]
        return "Usage: write: <path> -> <content>"

    # Support (PC)
    if l.startswith("support:") or l.startswith("ask simone:"):
        return cmd_support(msg.strip().split(":", 1)[1].strip())

    # Meta
    if l in ("fix yourself", "diagnose"): return cmd_diagnose()
    if l == "transcripts": return cmd_transcripts()
    if l in ("who am i", "who are you"): return "I am MiMo, Bruce Nigel's phone superagent. Flipper Zero on a phone."
    if l in ("help", "commands"): return cmd_help()

    return None  # Not a command — pass to LLM
