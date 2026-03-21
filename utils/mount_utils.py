import os
import subprocess
import sys
import time
import atexit
import signal
from pathlib import Path

# Constants
LOCK_FILE = Path(".mount.lock")
LOG_FILE = Path(".mount.log")
CREATIONFLAGS = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0

_startup_cleanup_performed = False
_active_mount_proc = None

def is_process_running(pid):
    """Checks if a process with the given PID is still running (Windows specific)."""
    try:
        output = subprocess.check_output(['tasklist', '/FI', f'PID eq {pid}'], stderr=subprocess.STDOUT, creationflags=CREATIONFLAGS)
        return str(pid) in output.decode()
    except:
        return False

def get_mount_pid():
    """Reads the PID from the lock file if it exists and is valid."""
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            if is_process_running(pid):
                return pid
            else:
                # Cleanup stale lock
                LOCK_FILE.unlink(missing_ok=True)
        except:
            LOCK_FILE.unlink(missing_ok=True)
    return None

def is_mounted():
    """Public check if mounting is currently active."""
    return get_mount_pid() is not None

def start_mount(local_path):
    """Starts the mpremote mount process and records its PID."""
    global _active_mount_proc
    if is_mounted():
        return False
        
    cmd = [sys.executable, "-m", "mpremote", "mount", str(local_path)]
    try:
        # Redirect stdout/stderr to a log file to avoid pipe buffer blocking 
        # and to capture the exact reason if it fails/crashes.
        log_handle = open(LOG_FILE, "w")
        _active_mount_proc = subprocess.Popen(cmd, creationflags=CREATIONFLAGS, stdout=log_handle, stderr=subprocess.STDOUT)
        LOCK_FILE.write_text(str(_active_mount_proc.pid))
        return True
    except Exception as e:
        print(f"Mount Error: {e}")
        return False

def stop_mount():
    """Stops the active mount process and cleans up the lock file."""
    pid = get_mount_pid()
    if pid:
        try:
            # On Windows, taskkill is a reliable way to kill a process by PID
            subprocess.run(['taskkill', '/F', '/T', '/PID', str(pid)], creationflags=CREATIONFLAGS)
        except:
            pass
    # Always try to remove the lock file
    if LOCK_FILE.exists():
        LOCK_FILE.unlink(missing_ok=True)

def startup_cleanup():
    """Kills any orphaned mpremote mount processes on system startup."""
    global _startup_cleanup_performed
    if _startup_cleanup_performed:
        return
    _startup_cleanup_performed = True

    # 1. Try to kill the specific PID from the lock file
    stop_mount()
    
    # 2. Aggressive cleanup: Kill any process that looks like 'mpremote mount'
    try:
        # This is a bit risky but requested by the user for 'releasing COM'
        # Windows 11 removed wmic, so we use PowerShell
        ps_cmd = ['powershell', '-NoProfile', '-Command', 
                  "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" | Select-Object CommandLine, ProcessId"]
        output = subprocess.check_output(ps_cmd, creationflags=CREATIONFLAGS).decode()
        for line in output.splitlines():
            if line and "mpremote" in line and "mount" in line:
                parts = line.strip().split()
                if parts:
                    pid = parts[-1]
                    try:
                        subprocess.run(['taskkill', '/F', '/T', '/PID', pid], creationflags=CREATIONFLAGS)
                    except:
                        pass
    except:
        pass

def register_exit_handlers():
    """Ensures stop_mount is called when the application exits."""
    atexit.register(stop_mount)


def is_rp2350_connected() -> bool:
    """Returns True if an RP2xxx device is detected on any serial COM port.
    Matches by Raspberry Pi VID (0x2E8A) or description/manufacturer containing 'RP2'.
    """
    try:
        import serial.tools.list_ports
        for port in serial.tools.list_ports.comports():
            desc = (port.description or "").upper()
            mfr  = (port.manufacturer or "").upper()
            if "RP2" in desc or "RP2" in mfr or port.vid == 0x2E8A:
                return True
    except Exception:
        pass
    return False
