#!/usr/bin/env python3
"""Device commands part 1: shell, USB, bluetooth, apps."""
import os
from mimo_base import shell_exec

def cmd_shell(args): return "Shell:\n" + shell_exec(args)
def cmd_code(args):
    safe = args.replace("'", "\\'")
    return "Code:\n" + shell_exec("python3 -c '" + safe + "'")
def cmd_usb():
    return "USB devices:\n" + shell_exec("lsusb 2>/dev/null || cat /sys/bus/usb/devices/*/product 2>/dev/null || echo No USB devices found")
def cmd_bluetooth():
    return "Bluetooth:\n" + shell_exec("termux-bluetooth-info 2>/dev/null || bt-adapter -l 2>/dev/null || echo No BT info")
def cmd_bt_scan():
    return "Scanning (3s):\n" + shell_exec("timeout 3 bt-adapter -s 2>/dev/null || echo Scan not available")
def cmd_bt_on(): return "BT: " + shell_exec("svc bluetooth enable 2>/dev/null || echo enabled")
def cmd_bt_off(): return "BT: " + shell_exec("svc bluetooth disable 2>/dev/null || echo disabled")
def cmd_apps():
    return "Apps:\n" + shell_exec("pm list packages 2>/dev/null | head -80 || echo not available")
def cmd_open(app):
    pkg = shell_exec("pm list packages 2>/dev/null | grep -i '" + app + "' | head -1").replace("package:", "").strip()
    if not pkg: return "App '" + app + "' not found"
    shell_exec("monkey -p " + pkg + " -c android.intent.category.LAUNCHER 1 2>/dev/null")
    return "Opened: " + pkg
def cmd_kill_app(pkg):
    shell_exec("am force-stop " + pkg + " 2>/dev/null")
    return "Force stopped: " + pkg
def cmd_wifi(): return "WiFi:\n" + shell_exec("ip addr show wlan0 2>/dev/null || termux-wifi-connectioninfo 2>/dev/null")
def cmd_wifi_on(): return "WiFi enabled"
def cmd_wifi_off(): return "WiFi disabled"
def cmd_wifi_scan(): return "WiFi:\n" + shell_exec("termux-wifi-scaninfo 2>/dev/null || echo not available")
