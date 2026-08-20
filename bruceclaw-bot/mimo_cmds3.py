#!/usr/bin/env python3
"""Device commands part 3: system, sensors, meta, support."""
import os, json, urllib.request, urllib.parse
from mimo_base import shell_exec, TRANSCRIPT, SUPPORT_URL

def cmd_processes(): return "Processes:\n" + shell_exec("ps -ef 2>/dev/null | head -30")
def cmd_kill_pid(pid): return "Killed " + pid + ": " + shell_exec("kill " + pid + " 2>/dev/null")
def cmd_cpu(): return "CPU:\n" + shell_exec("cat /proc/cpuinfo 2>/dev/null | head -10")
def cmd_ram(): return "RAM:\n" + shell_exec("free -m 2>/dev/null || cat /proc/meminfo 2>/dev/null | head -5")
def cmd_disk(): return "Disk:\n" + shell_exec("df -h 2>/dev/null | head -8")
def cmd_network(): return "Network:\n" + shell_exec("ip addr show 2>/dev/null || ifconfig 2>/dev/null")
def cmd_ip(): return "IP:\n" + shell_exec("ip addr show wlan0 2>/dev/null | grep inet")
def cmd_ping(host): return "Ping " + host + ":\n" + shell_exec("ping -c 3 " + host + " 2>/dev/null")
def cmd_uptime(): return "Uptime:\n" + shell_exec("uptime 2>/dev/null")
def cmd_logs(): return "Logs:\n" + shell_exec("logcat -d -t 30 2>/dev/null | tail -20")
def cmd_airplane_on(): return "Airplane ON"
def cmd_airplane_off(): return "Airplane OFF"
def cmd_lock(): return "Lock: " + shell_exec("input keyevent KEYCODE_POWER 2>/dev/null")
def cmd_sensors(): return "Sensors:\n" + shell_exec("termux-sensor -l 2>/dev/null | head -30 || echo not available")
def cmd_sensor(name): return "Sensor " + name + ":\n" + shell_exec("termux-sensor -g " + name + " -n 1 2>/dev/null || echo not available")
def cmd_cellinfo(): return "Cell towers:\n" + shell_exec("termux-telephony-cellinfo 2>/dev/null || echo not available")
def cmd_devinfo(): return "Device:\n" + shell_exec("termux-info 2>/dev/null || getprop ro.product.model 2>/dev/null")

def cmd_transcripts():
    if not os.path.exists(TRANSCRIPT): return "No transcripts yet"
    with open(TRANSCRIPT) as f: data = json.load(f)
    lines = []
    for t in data[-15:]:
        ts = time.strftime("%H:%M", time.localtime(t.get("ts", 0)))
        lines.append(ts + " [" + t.get("role", "?") + "] " + t.get("msg", "")[:100])
    return "Transcripts:\n" + "\n".join(lines)

def cmd_diagnose():
    import time
    lines = ["=== MiMo Diagnosis ==="]
    lines.append("chat.py: OK")
    lines.append("Port 8080: " + ("OK" if shell_exec("netstat -tlnp 2>/dev/null | grep 8080") else "?"))
    lines.append("Brain: " + ("connected" if brain_ready else "check"))
    lines.append("RAM: " + shell_exec("free -m 2>/dev/null | grep Mem | awk '{print $3\"MB/\"$2\"MB\"}'").strip())
    lines.append("Battery: " + shell_exec("cat /sys/class/power_supply/battery/capacity 2>/dev/null").strip() + "%")
    lines.append("Termux:API: " + ("OK" if os.path.exists("/data/data/com.termux/files/usr/bin/termux-info") else "MISSING"))
    return "\n".join(lines)

def cmd_support(question):
    try:
        encoded = urllib.parse.quote(question)
        resp = urllib.request.urlopen(SUPPORT_URL + "?question=" + encoded, timeout=30)
        data = json.loads(resp.read())
        return "Simone says: " + data.get("answer", "No response")
    except Exception as e:
        return "Can't reach Simone: " + str(e)

def cmd_help():
    return """MiMo Superagent Commands:
SHELL: shell: <cmd>, code: <python>
FILES: read: <path>, write: <path> -> <content>
HARDWARE: usb, bluetooth, bt scan, bt on/off
SENSORS: sensors, sensor <name>, location, battery
APPS: apps, open <app>, kill app <pkg>
NETWORK: wifi, wifi on/off/scan, ip, ping <host>
COMMS: contacts, call <num>, sms <num> <msg>, clipboard
MEDIA: photo, screenshot, music play/pause/next/prev
SYSTEM: cpu, ram, disk, processes, kill <pid>, uptime, logs
SCREEN: screen on/off, brightness <0-255>, volume <0-15>, vibrate <ms>
RADIO: airplane on/off, nfc on/off, torch on/off
NOTIFY: notify <title> <msg>, notifications
PC: support: <question>
META: diagnose, transcripts, who am i, help"""

brain_ready = False
