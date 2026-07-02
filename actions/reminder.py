# actions/reminder.py

import subprocess
import platform
import os
import sys
from datetime import datetime

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


def _reminder_windows(target_dt, safe_message, date_str, time_str, player):
    task_name = f"MARKReminder_{target_dt.strftime('%Y%m%d_%H%M')}"

    python_exe = sys.executable
    if python_exe.lower().endswith("python.exe"):
        pythonw = python_exe.replace("python.exe", "pythonw.exe")
        if os.path.exists(pythonw):
            python_exe = pythonw

    temp_dir      = os.environ.get("TEMP", "C:\\Temp")
    notify_script = os.path.join(temp_dir, f"{task_name}.pyw")
    project_root  = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )

    script_code = f'''import sys, os, time
sys.path.insert(0, r"{project_root}")

try:
    import winsound
    for freq in [800, 1000, 1200]:
        winsound.Beep(freq, 200)
        time.sleep(0.1)
except Exception:
    pass

try:
    from win10toast import ToastNotifier
    ToastNotifier().show_toast(
        "MARK Reminder",
        "{safe_message}",
        duration=15,
        threaded=False
    )
except Exception:
    try:
        import subprocess
        subprocess.run(["msg", "*", "/TIME:30", "{safe_message}"], shell=True)
    except Exception:
        pass

time.sleep(3)
try:
    os.remove(__file__)
except Exception:
    pass
'''
    with open(notify_script, "w", encoding="utf-8") as f:
        f.write(script_code)

    xml_content = f'''<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo>
    <Description>MARK Reminder: {safe_message}</Description>
  </RegistrationInfo>
  <Triggers>
    <TimeTrigger>
      <StartBoundary>{target_dt.strftime("%Y-%m-%dT%H:%M:%S")}</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Actions>
    <Exec>
      <Command>{python_exe}</Command>
      <Arguments>"{notify_script}"</Arguments>
    </Exec>
  </Actions>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <StartWhenAvailable>true</StartWhenAvailable>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT5M</ExecutionTimeLimit>
    <Enabled>true</Enabled>
  </Settings>
  <Principals>
    <Principal>
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>LeastPrivilege</RunLevel>
    </Principal>
  </Principals>
</Task>'''

    xml_path = os.path.join(temp_dir, f"{task_name}.xml")
    with open(xml_path, "w", encoding="utf-16") as f:
        f.write(xml_content)

    result = subprocess.run(
        ["schtasks", "/Create", "/TN", task_name, "/XML", xml_path, "/F"],
        capture_output=True, text=True
    )

    try:
        os.remove(xml_path)
    except Exception:
        pass

    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        print(f"[Reminder] ❌ schtasks failed: {err}")
        try:
            os.remove(notify_script)
        except Exception:
            pass
        return "I couldn't schedule the reminder due to a system error."

    if player:
        player.write_log(f"[reminder] set for {date_str} {time_str}")

    return f"Reminder set for {target_dt.strftime('%B %d at %I:%M %p')}."


def _reminder_macos(target_dt, safe_message, date_str, time_str, player):
    """Schedule a one-shot reminder via a self-removing launchd agent."""
    label      = f"com.jarvis.reminder.{target_dt.strftime('%Y%m%d%H%M')}"
    agents_dir = os.path.expanduser("~/Library/LaunchAgents")
    os.makedirs(agents_dir, exist_ok=True)
    plist_path  = os.path.join(agents_dir, f"{label}.plist")
    script_path = os.path.join(agents_dir, f"{label}.py")
    msg_path    = os.path.join(agents_dir, f"{label}.txt")

    # The user message is written as plain DATA (never interpolated into code or
    # XML) and read back at fire time, then handed to osascript via `on run argv`
    # so it is passed as an argument rather than concatenated into script source.
    with open(msg_path, "w", encoding="utf-8") as f:
        f.write(safe_message)

    # A tiny script that fires the notification, then unloads and deletes itself.
    # Only trusted, timestamp-derived paths are interpolated below.
    script_code = f'''import subprocess, os

PLIST = {plist_path!r}
MSGF  = {msg_path!r}

try:
    with open(MSGF, encoding="utf-8") as fh:
        msg = fh.read()
except Exception:
    msg = "Reminder"

try:
    subprocess.run([
        "osascript",
        "-e", "on run argv",
        "-e", 'display notification (item 1 of argv) with title "MARK Reminder" sound name "Glass"',
        "-e", "end run",
        msg,
    ])
except Exception:
    pass

try:
    for _ in range(3):
        subprocess.run(["afplay", "/System/Library/Sounds/Glass.aiff"])
except Exception:
    pass

try:
    subprocess.run(["launchctl", "unload", PLIST])
except Exception:
    pass
for path in (PLIST, MSGF, __file__):
    try:
        os.remove(path)
    except Exception:
        pass
'''
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(script_code)

    plist_content = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key><string>{label}</string>
    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>{script_path}</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Month</key><integer>{target_dt.month}</integer>
        <key>Day</key><integer>{target_dt.day}</integer>
        <key>Hour</key><integer>{target_dt.hour}</integer>
        <key>Minute</key><integer>{target_dt.minute}</integer>
    </dict>
    <key>RunAtLoad</key><false/>
</dict>
</plist>
'''
    with open(plist_path, "w", encoding="utf-8") as f:
        f.write(plist_content)

    subprocess.run(["launchctl", "unload", plist_path], capture_output=True)
    result = subprocess.run(["launchctl", "load", plist_path],
                            capture_output=True, text=True)

    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        print(f"[Reminder] ❌ launchctl failed: {err}")
        for path in (plist_path, script_path, msg_path):
            try:
                os.remove(path)
            except Exception:
                pass
        return "I couldn't schedule the reminder due to a system error."

    if player:
        player.write_log(f"[reminder] set for {date_str} {time_str}")

    return f"Reminder set for {target_dt.strftime('%B %d at %I:%M %p')}."


def _reminder_linux(target_dt, safe_message, date_str, time_str, player):
    """Best-effort reminder using the `at` scheduler if available."""
    import shlex
    from shutil import which
    if not which("at"):
        return ("Reminders on Linux require the 'at' scheduler. "
                "Install it (e.g. 'sudo apt install at') and enable the atd service.")

    # shlex.quote fully neutralises shell metacharacters ($, `, ;, |, &, ...)
    # since the command string is executed by a shell via `at`.
    esc = shlex.quote(safe_message)
    # notify-send for the popup, paplay/aplay for a sound if present.
    command = (f'notify-send "MARK Reminder" {esc}; '
               f'paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null || true')
    at_time = target_dt.strftime("%H:%M %Y-%m-%d")

    try:
        result = subprocess.run(["at", at_time], input=command,
                                capture_output=True, text=True)
    except Exception as e:
        return f"Could not schedule reminder: {e}"

    if result.returncode != 0:
        err = result.stderr.strip() or result.stdout.strip()
        print(f"[Reminder] ❌ at failed: {err}")
        return "I couldn't schedule the reminder due to a system error."

    if player:
        player.write_log(f"[reminder] set for {date_str} {time_str}")
    return f"Reminder set for {target_dt.strftime('%B %d at %I:%M %p')}."


def reminder(
    parameters: dict,
    response: str | None = None,
    player=None,
    session_memory=None
) -> str:
    """
    Sets a timed reminder.

    Uses Windows Task Scheduler on Windows, launchd on macOS, and the `at`
    scheduler on Linux.

    parameters:
        - date    (str) YYYY-MM-DD
        - time    (str) HH:MM
        - message (str)

    Returns a result string — Live API voices it automatically.
    No edge_speak needed.
    """

    date_str = parameters.get("date")
    time_str = parameters.get("time")
    message  = parameters.get("message", "Reminder")

    if not date_str or not time_str:
        return "I need both a date and a time to set a reminder."

    try:
        target_dt = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")

        if target_dt <= datetime.now():
            return "That time is already in the past."

        safe_message = message.replace('"', '').replace("'", "").strip()[:200]

        if _OS == "Windows":
            return _reminder_windows(target_dt, safe_message, date_str, time_str, player)
        if _OS == "Darwin":
            return _reminder_macos(target_dt, safe_message, date_str, time_str, player)
        return _reminder_linux(target_dt, safe_message, date_str, time_str, player)

    except ValueError:
        return "I couldn't understand that date or time format."

    except Exception as e:
        return f"Something went wrong while scheduling the reminder: {str(e)[:80]}"
