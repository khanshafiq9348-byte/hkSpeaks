"""
TTS Platform Continuous Server Supervisor
Guarantees continuous uptime for HK Speaks (FastAPI Backend on 8000 & Next.js Frontend on 3000).
- Runs as an independent, detached Windows background process
- Auto-reclaims ports to prevent random/temporary port drift
- Continuous health monitoring and crash auto-restart
- Automatic Windows reboot / restart auto-start via Startup Folder & Registry
- Strict sequential startup: Backend boots first, then Frontend
- Command CLI finishes immediately once services are confirmed healthy (no stuck tasks)
"""

import os
import sys
import time
import signal
import socket
import urllib.request
import subprocess
import argparse
from pathlib import Path
from typing import Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "apps" / "web"
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"
VENV_PYTHONW = BACKEND_DIR / ".venv" / "Scripts" / "pythonw.exe"

BACKEND_HOST = "0.0.0.0"
BACKEND_PORT = 8000
FRONTEND_PORT = 3000

BACKEND_HEALTH_URL = f"http://127.0.0.1:{BACKEND_PORT}/health"
FRONTEND_HEALTH_URL = f"http://localhost:{FRONTEND_PORT}"

PID_FILE = ROOT_DIR / "data" / "supervisor.pid"
SUPERVISOR_LOG = ROOT_DIR / "data" / "supervisor.log"
BACKEND_LOG = ROOT_DIR / "data" / "backend.log"
FRONTEND_LOG = ROOT_DIR / "data" / "frontend.log"

def log_msg(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    try:
        if sys.stdout is not None:
            print(line, flush=True)
    except Exception:
        pass
    try:
        SUPERVISOR_LOG.parent.mkdir(parents=True, exist_ok=True)
        with open(SUPERVISOR_LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass

_global_mutex = None

def acquire_single_instance_lock() -> bool:
    """
    Acquires a system-wide named mutex on Windows.
    Guarantees ONLY ONE supervisor instance can run at a time across the entire OS.
    """
    global _global_mutex
    if _global_mutex is not None:
        return True
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        mutex_name = "Local\\HKSpeaksSupervisorMutex"
        _global_mutex = kernel32.CreateMutexW(None, True, mutex_name)
        if kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
            return False
        return bool(_global_mutex)
    except Exception:
        return True

def get_python_exe() -> str:
    if VENV_PYTHON.exists():
        return str(VENV_PYTHON)
    return sys.executable

def get_pythonw_exe() -> str:
    if VENV_PYTHONW.exists():
        return str(VENV_PYTHONW)
    return get_python_exe()

def get_npm_cmd() -> str:
    if sys.platform == "win32":
        return "npm.cmd"
    return "npm"

def is_pid_alive(pid: int) -> bool:
    if not pid or pid <= 0:
        return False
    if sys.platform == "win32":
        try:
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            output = subprocess.check_output(
                f'tasklist /FI "PID eq {pid}" /NH',
                shell=True,
                creationflags=flags,
                stderr=subprocess.DEVNULL,
                text=True
            )
            for line in output.strip().splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[1] == str(pid):
                    return True
            return False
        except Exception:
            return False
    else:
        try:
            os.kill(pid, 0)
            return True
        except OSError:
            return False

def get_existing_supervisor_pid() -> Optional[int]:
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            if pid != os.getpid() and is_pid_alive(pid):
                return pid
            elif not is_pid_alive(pid):
                PID_FILE.unlink(missing_ok=True)
        except Exception:
            PID_FILE.unlink(missing_ok=True)
    return None

def find_pids_on_port(port: int) -> list[int]:
    pids = []
    try:
        if sys.platform == "win32":
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            output = subprocess.check_output(
                f"netstat -ano -p tcp | findstr :{port}",
                shell=True,
                creationflags=flags,
                stderr=subprocess.DEVNULL,
                text=True
            )
            for line in output.strip().splitlines():
                parts = line.split()
                if len(parts) >= 5 and parts[3] == "LISTENING":
                    try:
                        pid = int(parts[4])
                        if pid != 0 and pid != os.getpid() and pid not in pids:
                            pids.append(pid)
                    except ValueError:
                        pass
        else:
            output = subprocess.check_output(
                ["lsof", "-t", f"-i:{port}"],
                stderr=subprocess.DEVNULL,
                text=True
            )
            for line in output.strip().splitlines():
                try:
                    pid = int(line)
                    if pid != os.getpid() and pid not in pids:
                        pids.append(pid)
                except ValueError:
                    pass
    except Exception:
        pass
    return pids

def kill_process_tree(pid: int):
    try:
        if sys.platform == "win32":
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=flags,
                check=False
            )
        else:
            os.kill(pid, signal.SIGKILL)
    except Exception:
        pass

def free_port(port: int, label: str):
    pids = find_pids_on_port(port)
    if pids:
        log_msg(f"[{label}] Port {port} is occupied by PID(s): {pids}. Cleaning up to maintain stable URL...")
        for p in pids:
            kill_process_tree(p)
        time.sleep(1.0)

def is_ffmpeg_running() -> bool:
    try:
        if sys.platform == "win32":
            flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            output = subprocess.check_output(
                'tasklist /FI "IMAGENAME eq ffmpeg.exe" /NH',
                shell=True,
                creationflags=flags,
                stderr=subprocess.DEVNULL,
                text=True
            )
            return "ffmpeg.exe" in output.lower()
        else:
            output = subprocess.check_output(
                ["pgrep", "ffmpeg"],
                stderr=subprocess.DEVNULL,
                text=True
            )
            return bool(output.strip())
    except Exception:
        return False

def is_backend_healthy(timeout: float = 6.0) -> bool:
    for host in ["127.0.0.1", "localhost"]:
        try:
            req = urllib.request.Request(f"http://{host}:{BACKEND_PORT}/health", headers={"User-Agent": "HK-Supervisor"})
            with urllib.request.urlopen(req, timeout=timeout) as res:
                if res.status == 200:
                    return True
        except Exception:
            pass
    return False

def is_frontend_healthy(timeout: float = 4.0) -> bool:
    for host in ["localhost", "127.0.0.1"]:
        try:
            req = urllib.request.Request(f"http://{host}:{FRONTEND_PORT}", headers={"User-Agent": "HK-Supervisor"})
            with urllib.request.urlopen(req, timeout=timeout) as res:
                if res.status < 500:
                    return True
        except Exception:
            pass
    return False

def install_autostart() -> bool:
    if sys.platform != "win32":
        return False

    success = False
    vbs_path = ROOT_DIR / "scripts" / "autostart.vbs"

    vbs_content = (
        '\' =========================================================================\n'
        '\' HK Speaks Platform - Silent Auto-Start Wrapper\n'
        '\' =========================================================================\n'
        'Set WshShell = CreateObject("WScript.Shell")\n'
        'Set FSO = CreateObject("Scripting.FileSystemObject")\n'
        f'RootDir = "{str(ROOT_DIR)}"\n'
        'WshShell.CurrentDirectory = RootDir\n'
        f'PythonwExe = RootDir & "\\backend\\.venv\\Scripts\\pythonw.exe"\n'
        'If Not FSO.FileExists(PythonwExe) Then\n'
        '    PythonwExe = RootDir & "\\backend\\.venv\\Scripts\\python.exe"\n'
        'End If\n'
        'If Not FSO.FileExists(PythonwExe) Then\n'
        '    PythonwExe = "pythonw.exe"\n'
        'End If\n'
        'SupervisorScript = RootDir & "\\scripts\\supervisor.py"\n'
        'Cmd = """" & PythonwExe & """ """ & SupervisorScript & """ --daemon"\n'
        'WshShell.Run Cmd, 0, False\n'
    )
    try:
        vbs_path.write_text(vbs_content, encoding="ascii")
    except Exception as e:
        log_msg(f"[AutoStart] Warning writing autostart.vbs: {e}")

    try:
        startup_dir = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"))
        if startup_dir.exists():
            startup_vbs = startup_dir / "HKSpeaks_AutoStart.vbs"
            launcher_code = (
                '\' HK Speaks Platform - Windows Auto-Start\n'
                'Set WshShell = CreateObject("WScript.Shell")\n'
                'Set FSO = CreateObject("Scripting.FileSystemObject")\n'
                f'ProjectDir = "{str(ROOT_DIR)}"\n'
                'If FSO.FolderExists(ProjectDir) Then\n'
                '    WshShell.CurrentDirectory = ProjectDir\n'
                '    AutostartScript = ProjectDir & "\\scripts\\autostart.vbs"\n'
                '    If FSO.FileExists(AutostartScript) Then\n'
                '        WshShell.Run "wscript.exe """ & AutostartScript & """", 0, False\n'
                '    Else\n'
                '        PythonwExe = ProjectDir & "\\backend\\.venv\\Scripts\\pythonw.exe"\n'
                '        SupervisorPy = ProjectDir & "\\scripts\\supervisor.py"\n'
                '        If FSO.FileExists(PythonwExe) And FSO.FileExists(SupervisorPy) Then\n'
                '            WshShell.Run """" & PythonwExe & """ """ & SupervisorPy & """ --daemon", 0, False\n'
                '        End If\n'
                '    End If\n'
                'End If\n'
            )
            startup_vbs.write_text(launcher_code, encoding="ascii")
            log_msg(f"[AutoStart] Registered Windows Startup Folder: {startup_vbs}")
            success = True
    except Exception as e:
        log_msg(f"[AutoStart] Failed to register in Startup folder: {e}")

    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        cmd_str = f'wscript.exe "{str(vbs_path)}"'
        winreg.SetValueEx(key, "HKSpeaksPlatform", 0, winreg.REG_SZ, cmd_str)
        winreg.CloseKey(key)
        log_msg("[AutoStart] Registered HKCU Run Registry key: HKSpeaksPlatform")
        success = True
    except Exception as e:
        log_msg(f"[AutoStart] Warning setting HKCU Run key: {e}")

    return success

def uninstall_autostart():
    if sys.platform != "win32":
        return
    try:
        startup_dir = Path(os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"))
        startup_vbs = startup_dir / "HKSpeaks_AutoStart.vbs"
        if startup_vbs.exists():
            startup_vbs.unlink()
            log_msg(f"[AutoStart] Removed Startup Folder shortcut: {startup_vbs}")
    except Exception as e:
        log_msg(f"[AutoStart] Error removing startup file: {e}")

    try:
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        try:
            winreg.DeleteValue(key, "HKSpeaksPlatform")
            log_msg("[AutoStart] Removed Registry HKCU CurrentVersion\\Run entry")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception as e:
        log_msg(f"[AutoStart] Error removing registry key: {e}")

class Supervisor:
    def __init__(self, dev_mode: bool = False):
        self.dev_mode = dev_mode
        self.backend_proc: Optional[subprocess.Popen] = None
        self.frontend_proc: Optional[subprocess.Popen] = None
        self.backend_log = None
        self.frontend_log = None
        self.running = True
        self.backend_fail_count = 0
        self.frontend_fail_count = 0

    def start_backend(self):
        if is_backend_healthy():
            log_msg(f"[Supervisor] Backend is already running and healthy on port {BACKEND_PORT}. Skipping unnecessary restart.")
            self.backend_fail_count = 0
            return
        free_port(BACKEND_PORT, "Backend")
        py_exe = get_python_exe()
        cmd = [
            py_exe,
            "-m", "uvicorn",
            "app.main:app",
            "--app-dir", "backend",
            "--host", BACKEND_HOST,
            "--port", str(BACKEND_PORT),
            "--log-level", "info"
        ]
        log_msg(f"[Supervisor] Launching Backend on http://{BACKEND_HOST}:{BACKEND_PORT} ...")
        BACKEND_LOG.parent.mkdir(parents=True, exist_ok=True)
        if self.backend_log:
            try: self.backend_log.close()
            except Exception: pass
        self.backend_log = open(BACKEND_LOG, "a", encoding="utf-8")
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self.backend_proc = subprocess.Popen(
            cmd,
            cwd=str(ROOT_DIR),
            stdout=self.backend_log,
            stderr=subprocess.STDOUT,
            creationflags=flags
        )
        self.backend_fail_count = 0

    def start_frontend(self):
        if is_frontend_healthy():
            log_msg(f"[Supervisor] Frontend is already running and healthy on port {FRONTEND_PORT}. Skipping unnecessary restart.")
            self.frontend_fail_count = 0
            return
        free_port(FRONTEND_PORT, "Frontend")
        npm_cmd = get_npm_cmd()
        next_build = FRONTEND_DIR / ".next"
        if not self.dev_mode and next_build.exists():
            cmd = [npm_cmd, "start"]
            mode_desc = "Production"
        else:
            cmd = [npm_cmd, "run", "dev"]
            mode_desc = "Development"

        log_msg(f"[Supervisor] Launching Frontend ({mode_desc}) on http://localhost:{FRONTEND_PORT} ...")
        FRONTEND_LOG.parent.mkdir(parents=True, exist_ok=True)
        if self.frontend_log:
            try: self.frontend_log.close()
            except Exception: pass
        self.frontend_log = open(FRONTEND_LOG, "a", encoding="utf-8")
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        self.frontend_proc = subprocess.Popen(
            cmd,
            cwd=str(FRONTEND_DIR),
            stdout=self.frontend_log,
            stderr=subprocess.STDOUT,
            creationflags=flags
        )
        self.frontend_fail_count = 0

    def stop_all(self):
        self.running = False
        log_msg("[Supervisor] Stopping all services...")
        if self.backend_proc:
            kill_process_tree(self.backend_proc.pid)
            self.backend_proc = None
        if self.frontend_proc:
            kill_process_tree(self.frontend_proc.pid)
            self.frontend_proc = None
        if self.backend_log:
            try: self.backend_log.close()
            except Exception: pass
            self.backend_log = None
        if self.frontend_log:
            try: self.frontend_log.close()
            except Exception: pass
            self.frontend_log = None
        free_port(BACKEND_PORT, "Backend")
        free_port(FRONTEND_PORT, "Frontend")
        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except Exception:
                pass
        log_msg("[Supervisor] All services stopped.")

    def run(self):
        signal.signal(signal.SIGINT, lambda s, f: self.stop_all() or sys.exit(0))
        signal.signal(signal.SIGTERM, lambda s, f: self.stop_all() or sys.exit(0))

        if not acquire_single_instance_lock():
            log_msg("[Supervisor] Another supervisor instance is already running (System Mutex held). Exiting duplicate process.")
            sys.exit(0)

        PID_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(PID_FILE, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))

        # Guarantee lifetime autostart across Windows reboots
        try:
            install_autostart()
        except Exception as e:
            log_msg(f"[AutoStart] Warning during self-healing autostart: {e}")

        log_msg("=========================================================")
        log_msg("  HK Speaks — Continuous Platform Supervisor Active      ")
        log_msg(f"  Supervisor PID: {os.getpid()}")
        log_msg(f"  Backend:  http://{BACKEND_HOST}:{BACKEND_PORT}")
        log_msg(f"  Frontend: http://localhost:{FRONTEND_PORT}")
        log_msg("=========================================================")

        # Step 1: Start Backend first
        self.start_backend()

        log_msg("[Supervisor] Waiting for Backend to initialize and become healthy...")
        backend_ready = False
        for i in range(30):
            if is_backend_healthy():
                backend_ready = True
                log_msg(f"[Supervisor] Backend is HEALTHY (200 OK) after {i+1}s.")
                break
            time.sleep(1.0)

        if not backend_ready:
            log_msg("[Supervisor] [WARNING] Backend did not respond within 30s. Proceeding with Frontend launch...")

        # Step 2: Start Frontend once Backend is online
        self.start_frontend()

        log_msg("[Supervisor] Waiting for Frontend to become ready...")
        frontend_ready = False
        for i in range(30):
            if is_frontend_healthy():
                frontend_ready = True
                log_msg(f"[Supervisor] Frontend is HEALTHY (200 OK) after {i+1}s.")
                break
            time.sleep(1.0)

        b_ok = is_backend_healthy()
        f_ok = is_frontend_healthy()
        log_msg(f"[Supervisor] Initial status -> Backend: {'HEALTHY (200 OK)' if b_ok else 'STARTING'}, Frontend: {'HEALTHY (200 OK)' if f_ok else 'STARTING'}")

        # Continuous supervision loop
        while self.running:
            try:
                time.sleep(2.0)

                # Check Backend
                if self.backend_proc is None or self.backend_proc.poll() is not None:
                    if is_backend_healthy():
                        self.backend_fail_count = 0
                    else:
                        code = self.backend_proc.poll() if self.backend_proc else "None"
                        log_msg(f"[Supervisor] [ALERT] Backend process exited (code={code}) and port {BACKEND_PORT} down. Auto-restarting...")
                        self.start_backend()
                else:
                    if not is_backend_healthy(timeout=6.0):
                        self.backend_fail_count += 1
                        has_render = is_ffmpeg_running()
                        max_fails = 35 if has_render else 15
                        if self.backend_fail_count >= max_fails:
                            log_msg(f"[Supervisor] [ALERT] Backend unresponsive for {self.backend_fail_count} checks. Recycling process...")
                            kill_process_tree(self.backend_proc.pid)
                            self.start_backend()
                    else:
                        self.backend_fail_count = 0

                # Check Frontend
                if self.frontend_proc is None or self.frontend_proc.poll() is not None:
                    if is_frontend_healthy():
                        self.frontend_fail_count = 0
                    else:
                        code = self.frontend_proc.poll() if self.frontend_proc else "None"
                        log_msg(f"[Supervisor] [ALERT] Frontend process exited (code={code}) and port {FRONTEND_PORT} down. Auto-restarting...")
                        self.start_frontend()
                else:
                    if not is_frontend_healthy():
                        self.frontend_fail_count += 1
                        if self.frontend_fail_count >= 10:
                            log_msg("[Supervisor] [ALERT] Frontend unresponsive for 10 checks. Recycling process...")
                            kill_process_tree(self.frontend_proc.pid)
                            self.start_frontend()
                    else:
                        self.frontend_fail_count = 0

            except KeyboardInterrupt:
                self.stop_all()
                break
            except Exception as e:
                log_msg(f"[Supervisor] Loop error: {e}")
                time.sleep(1.0)

def spawn_detached_supervisor() -> bool:
    """
    Spawns supervisor.py as an independent, completely hidden Windows background service.
    Guarantees NO console window or popup ever appears.
    """
    py_exe = get_pythonw_exe()
    script_path = str(ROOT_DIR / "scripts" / "supervisor.py")
    cmd = [py_exe, script_path, "--daemon"]

    creationflags = 0
    if sys.platform == "win32":
        DETACHED_PROCESS = 0x00000008
        CREATE_NEW_PROCESS_GROUP = 0x00000200
        CREATE_NO_WINDOW = 0x08000000
        CREATE_BREAKAWAY_FROM_JOB = 0x01000000
        creationflags = DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP | CREATE_NO_WINDOW | CREATE_BREAKAWAY_FROM_JOB

    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT_DIR),
        creationflags=creationflags,
        close_fds=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL
    )
    log_msg(f"[Supervisor] Detached background supervisor daemon launched silently (PID {proc.pid}).")
    return True

def print_status(verbose: bool = True) -> int:
    b_pids = find_pids_on_port(BACKEND_PORT)
    f_pids = find_pids_on_port(FRONTEND_PORT)
    b_health = is_backend_healthy()
    f_health = is_frontend_healthy()

    sup_pid = None
    if PID_FILE.exists():
        try:
            cand = int(PID_FILE.read_text().strip())
            if is_pid_alive(cand):
                sup_pid = cand
            else:
                PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass

    if verbose:
        print("=========================================================")
        print("  HK Speaks Platform Status                              ")
        print("=========================================================")
        print(f"  Supervisor PID:  {sup_pid if sup_pid else 'Not running'}")
        print(f"  Backend Port:    {BACKEND_PORT} (PID: {b_pids or 'None'})")
        print(f"  Backend Health:  {'HEALTHY (200 OK)' if b_health else 'DOWN / UNHEALTHY'}")
        print(f"  Backend URL:     {BACKEND_HEALTH_URL}")
        print(f"  Frontend Port:   {FRONTEND_PORT} (PID: {f_pids or 'None'})")
        print(f"  Frontend Health: {'HEALTHY (200 OK)' if f_health else 'DOWN / UNHEALTHY'}")
        print(f"  Frontend URL:    {FRONTEND_HEALTH_URL}")
        print("=========================================================")
    return 0 if (b_health and f_health) else 1

def stop_services():
    if PID_FILE.exists():
        try:
            pid = int(PID_FILE.read_text().strip())
            print(f"Stopping supervisor PID {pid}...")
            kill_process_tree(pid)
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
    free_port(BACKEND_PORT, "Backend")
    free_port(FRONTEND_PORT, "Frontend")
    print("Services stopped.")

def start_and_wait(timeout_seconds: int = 15) -> int:
    """
    Ensures the continuous supervisor daemon is running in background.
    Waits until both Backend and Frontend are healthy, prints status, and exits 0.
    """
    try:
        install_autostart()
    except Exception:
        pass

    existing_pid = get_existing_supervisor_pid()
    if existing_pid and is_backend_healthy() and is_frontend_healthy():
        print("[Supervisor] Platform is already active and healthy in background.")
        return print_status(verbose=True)

    if existing_pid:
        print(f"[Supervisor] Existing supervisor PID {existing_pid} was degraded. Stopping old process...")
        kill_process_tree(existing_pid)
        PID_FILE.unlink(missing_ok=True)
        time.sleep(1.0)

    print("[Supervisor] Launching background supervisor daemon...")
    spawn_detached_supervisor()

    # Wait for services to become healthy
    print(f"[Supervisor] Waiting for platform services to become ready (up to {timeout_seconds}s)...")
    start_t = time.time()
    while time.time() - start_t < timeout_seconds:
        b_ok = is_backend_healthy()
        f_ok = is_frontend_healthy()
        if b_ok and f_ok:
            print("[Supervisor] All services are online and healthy!")
            return print_status(verbose=True)
        time.sleep(1.0)

    print("[Supervisor] Platform startup initiated. Current status:")
    return print_status(verbose=True)

def main():
    parser = argparse.ArgumentParser(description="HK Speaks Continuous Platform Supervisor")
    parser.add_argument("--status", action="store_true", help="Check status of services and exit")
    parser.add_argument("--stop", action="store_true", help="Stop all services and exit")
    parser.add_argument("--restart", action="store_true", help="Stop and restart all services in background")
    parser.add_argument("--start", action="store_true", help="Start all services in background")
    parser.add_argument("--daemon", action="store_true", help="Run supervisor loop as background daemon")
    parser.add_argument("--foreground", action="store_true", help="Run supervisor loop in foreground")
    parser.add_argument("--dev", action="store_true", help="Run frontend in dev mode")
    parser.add_argument("--install-autostart", action="store_true", help="Register Windows startup auto-start")
    parser.add_argument("--uninstall-autostart", action="store_true", help="Remove Windows startup auto-start")
    args = parser.parse_args()

    if args.install_autostart:
        success = install_autostart()
        print(f"Auto-start installation {'SUCCEEDED' if success else 'FAILED'}.")
        sys.exit(0 if success else 1)

    if args.uninstall_autostart:
        uninstall_autostart()
        print("Auto-start removed.")
        sys.exit(0)

    if args.status:
        sys.exit(print_status(verbose=True))

    if args.stop:
        stop_services()
        sys.exit(0)

    if args.daemon or args.foreground:
        if not acquire_single_instance_lock():
            log_msg("[Supervisor] Another supervisor instance is already running (System Mutex held). Exiting duplicate process.")
            sys.exit(0)
        # Long-running background daemon process
        supervisor = Supervisor(dev_mode=args.dev)
        supervisor.run()
        return

    if args.restart:
        stop_services()
        time.sleep(1.0)
        sys.exit(start_and_wait(timeout_seconds=20))

    # Default action: start detached background daemon if not already running, wait for healthy, then exit 0
    sys.exit(start_and_wait(timeout_seconds=20))

if __name__ == "__main__":
    main()
