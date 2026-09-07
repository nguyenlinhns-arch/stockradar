from __future__ import annotations

import ctypes
import json
import os
import pathlib
import re
import signal
import subprocess
import sys
import threading
import time
import traceback
import urllib.error
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

APP_NAME = "ThayLinh PC Bridge"
VERSION = "5.4.1"
DEFAULT_REPO = "nguyenlinhns-arch/stockradar"
DEFAULT_PREFIXES = ("[PC-CONTROL]", "[ZALO-CONTROL]")
DEFAULT_TRUSTED_USER = "nguyenlinhns-arch"
API_PORT = 4321
POLL_SECONDS = 75
HUB_URL = "http://127.0.0.1:4310/health"

ROOT = pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home())) / "ThayLinhPCBridge"
ROOT.mkdir(parents=True, exist_ok=True)
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = ROOT / "state.json"
CONFIG_FILE = ROOT / "config.json"
LOCK_FILE = ROOT / "agent.lock"

STOP = threading.Event()
STATE_LOCK = threading.Lock()


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def log(message: str) -> None:
    line = f"{now_iso()} {message}"
    print(line, flush=True)
    path = LOG_DIR / f"bridge-{datetime.now().strftime('%Y%m%d')}.log"
    try:
        with path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_json(path: pathlib.Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def atomic_write_json(path: pathlib.Path, data: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_config() -> dict[str, Any]:
    cfg = {
        "repo": DEFAULT_REPO,
        "trusted_user": DEFAULT_TRUSTED_USER,
        "prefixes": list(DEFAULT_PREFIXES),
        "poll_seconds": POLL_SECONDS,
        "hub_url": HUB_URL,
        "api_port": API_PORT,
        "auto_start_hub": True,
        "auto_start_desktop_commander": True,
        "desktop_commander_command": "npx @wonderwhy-er/desktop-commander@latest remote",
        "app_candidates": {
            "zalo": [
                r"%LOCALAPPDATA%\Programs\Zalo\Zalo.exe",
                r"%LOCALAPPDATA%\Zalo\Zalo.exe",
            ],
            "capcut": [
                r"%LOCALAPPDATA%\CapCut\Apps\CapCut.exe",
                r"%LOCALAPPDATA%\Programs\CapCut\CapCut.exe",
            ],
        },
    }
    user_cfg = load_json(CONFIG_FILE, {})
    if isinstance(user_cfg, dict):
        for key, value in user_cfg.items():
            if key == "app_candidates" and isinstance(value, dict):
                cfg["app_candidates"].update(value)
            else:
                cfg[key] = value
    return cfg


def load_state() -> dict[str, Any]:
    state = load_json(STATE_FILE, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("processed_issues", [])
    state.setdefault("last_command", None)
    state.setdefault("last_result", None)
    state.setdefault("started_at", now_iso())
    return state


STATE = load_state()
CONFIG = load_config()


def save_state() -> None:
    with STATE_LOCK:
        STATE["updated_at"] = now_iso()
        atomic_write_json(STATE_FILE, STATE)


def acquire_single_instance() -> bool:
    if os.name != "nt":
        return True
    import msvcrt

    handle = LOCK_FILE.open("a+b")
    try:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        handle.close()
        return False
    acquire_single_instance.handle = handle  # type: ignore[attr-defined]
    return True


def http_get_json(url: str, timeout: float = 3.0) -> tuple[bool, Any]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": f"ThayLinh-PCBridge/{VERSION}"}
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            try:
                return 200 <= resp.status < 300, json.loads(body)
            except Exception:
                return 200 <= resp.status < 300, body[:500]
    except Exception as exc:
        return False, str(exc)


def hub_health() -> dict[str, Any]:
    ok, detail = http_get_json(str(CONFIG.get("hub_url", HUB_URL)), timeout=2.0)
    return {"ok": ok, "detail": detail}


def detached_flags() -> int:
    if os.name != "nt":
        return 0
    return 0x00000008 | 0x00000200


def start_detached(argv: list[str], cwd: str | None = None) -> dict[str, Any]:
    try:
        subprocess.Popen(
            argv,
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=detached_flags(),
            close_fds=(os.name != "nt"),
        )
        return {"ok": True, "argv": argv}
    except Exception as exc:
        return {"ok": False, "error": str(exc), "argv": argv}


def expanded(path: str) -> str:
    return os.path.expandvars(os.path.expanduser(path))


def start_hub() -> dict[str, Any]:
    if hub_health()["ok"]:
        return {"ok": True, "status": "already_healthy"}
    home = pathlib.Path.home()
    candidates = [
        home / "Desktop" / "automation_hub.cmd",
        home / ".openai" / "computer-use" / "automation_hub.cmd",
        home / ".openai" / "computer-use" / "automation_hub.py",
    ]
    attempts: list[dict[str, Any]] = []
    for path in candidates:
        if not path.exists():
            continue
        if path.suffix.lower() == ".py":
            python = sys.executable or "python.exe"
            attempt = start_detached([python, str(path)], cwd=str(path.parent))
        else:
            attempt = start_detached(
                ["cmd.exe", "/d", "/c", str(path)], cwd=str(path.parent)
            )
        attempts.append(attempt)
        if attempt.get("ok"):
            for _ in range(10):
                time.sleep(1)
                if hub_health()["ok"]:
                    return {
                        "ok": True,
                        "status": "started",
                        "path": str(path),
                        "attempts": attempts,
                    }
    return {"ok": False, "status": "not_started", "attempts": attempts}


def process_command_lines() -> str:
    if os.name != "nt":
        return ""
    script = (
        "Get-CimInstance Win32_Process | "
        "Select-Object ProcessId,Name,CommandLine | ConvertTo-Json -Compress"
    )
    try:
        cp = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-Command",
                script,
            ],
            text=True,
            capture_output=True,
            timeout=15,
        )
        return cp.stdout or ""
    except Exception:
        return ""


def desktop_commander_running() -> bool:
    text = process_command_lines().lower()
    return "desktop-commander" in text and "remote" in text


def start_desktop_commander(force_restart: bool = False) -> dict[str, Any]:
    if force_restart and os.name == "nt":
        ps = (
            "Get-CimInstance Win32_Process | Where-Object { "
            "$_.CommandLine -match 'desktop-commander' -and $_.CommandLine -match 'remote' } | "
            "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
        )
        try:
            subprocess.run(
                ["powershell.exe", "-NoProfile", "-Command", ps], timeout=15
            )
            time.sleep(1)
        except Exception:
            pass
    elif desktop_commander_running():
        return {"ok": True, "status": "already_running"}

    cmd = str(
        CONFIG.get(
            "desktop_commander_command",
            "npx @wonderwhy-er/desktop-commander@latest remote",
        )
    )
    result = (
        start_detached(["cmd.exe", "/d", "/c", cmd])
        if os.name == "nt"
        else {"ok": False, "error": "Windows only"}
    )
    if result.get("ok"):
        time.sleep(2)
        result["status"] = "started"
        result["detected"] = desktop_commander_running()
    return result


def find_executable(app: str) -> pathlib.Path | None:
    app = app.lower().strip()
    for raw in CONFIG.get("app_candidates", {}).get(app, []):
        p = pathlib.Path(expanded(str(raw)))
        if p.exists():
            return p
    local = pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home()))
    roots = {
        "zalo": [local / "Programs" / "Zalo", local / "Zalo"],
        "capcut": [local / "CapCut", local / "Programs" / "CapCut"],
    }.get(app, [])
    target = "Zalo.exe" if app == "zalo" else "CapCut.exe" if app == "capcut" else ""
    if target:
        for root in roots:
            if root.exists():
                try:
                    for p in root.rglob(target):
                        if p.is_file():
                            return p
                except Exception:
                    pass
    return None


def focus_process(exe_name: str) -> bool:
    if os.name != "nt":
        return False
    from ctypes import wintypes

    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32
    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    SW_RESTORE = 9
    target = exe_name.lower()
    found = {"ok": False}

    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.CloseHandle.restype = wintypes.BOOL
    kernel32.QueryFullProcessImageNameW.argtypes = [
        wintypes.HANDLE,
        wintypes.DWORD,
        wintypes.LPWSTR,
        ctypes.POINTER(wintypes.DWORD),
    ]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    user32.GetWindowThreadProcessId.argtypes = [
        wintypes.HWND,
        ctypes.POINTER(wintypes.DWORD),
    ]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def enum_proc(hwnd, _lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        hproc = kernel32.OpenProcess(
            PROCESS_QUERY_LIMITED_INFORMATION, False, pid.value
        )
        if not hproc:
            return True
        try:
            size = wintypes.DWORD(32768)
            buf = ctypes.create_unicode_buffer(size.value)
            if kernel32.QueryFullProcessImageNameW(
                hproc, 0, buf, ctypes.byref(size)
            ):
                if pathlib.Path(buf.value).name.lower() == target:
                    user32.ShowWindow(hwnd, SW_RESTORE)
                    user32.SetForegroundWindow(hwnd)
                    found["ok"] = True
                    return False
        finally:
            kernel32.CloseHandle(hproc)
        return True

    user32.EnumWindows(enum_proc, 0)
    return bool(found["ok"])


def start_app(app: str, focus: bool = True) -> dict[str, Any]:
    exe = find_executable(app)
    if not exe:
        return {"ok": False, "error": f"Executable not found for {app}"}
    if focus and focus_process(exe.name):
        return {"ok": True, "status": "focused", "path": str(exe)}
    result = start_detached([str(exe)], cwd=str(exe.parent))
    result["path"] = str(exe)
    if result.get("ok"):
        time.sleep(2)
        result["focused"] = focus_process(exe.name) if focus else False
    return result


def self_test() -> dict[str, Any]:
    return {
        "ok": True,
        "version": VERSION,
        "time": now_iso(),
        "root": str(ROOT),
        "hub": hub_health(),
        "desktop_commander_running": desktop_commander_running(),
        "zalo_exe": str(find_executable("zalo") or ""),
        "capcut_exe": str(find_executable("capcut") or ""),
        "github_token_available": bool(resolve_github_token()),
        "processed_issue_count": len(STATE.get("processed_issues", [])),
        "last_command": STATE.get("last_command"),
        "last_result": STATE.get("last_result"),
    }


def run_action(action: str, body: str = "") -> dict[str, Any]:
    action = action.upper().strip()
    if action == "PING":
        return {"ok": True, "pong": True, "version": VERSION, "time": now_iso()}
    if action in {"STATUS", "SELF_TEST", "ZALO_STATUS"}:
        return self_test()
    if action == "START_HUB":
        return start_hub()
    if action == "START_DESKTOP_COMMANDER":
        return start_desktop_commander(False)
    if action == "RESTART_DESKTOP_COMMANDER":
        return start_desktop_commander(True)
    if action == "START_ZALO":
        return start_app("zalo")
    if action == "START_CAPCUT":
        return start_app("capcut")
    if action == "FOCUS_ZALO":
        exe = find_executable("zalo")
        return {"ok": bool(exe and focus_process(exe.name)), "path": str(exe or "")}
    if action == "FOCUS_CAPCUT":
        exe = find_executable("capcut")
        return {"ok": bool(exe and focus_process(exe.name)), "path": str(exe or "")}
    if action == "REPAIR_ALL":
        return {
            "ok": True,
            "hub": start_hub(),
            "desktop_commander": start_desktop_commander(False),
            "status": self_test(),
        }
    if action == "ZALO_CLASSIFY_OLD":
        return {
            "ok": False,
            "error": "Legacy command intentionally disabled in rescue layer; use main V5 UI controller.",
        }
    return {"ok": False, "error": f"Action not allowed: {action}"}


def resolve_github_token() -> str:
    for name in ("THAYLINH_GITHUB_TOKEN", "GH_TOKEN", "GITHUB_TOKEN"):
        token = os.environ.get(name, "").strip()
        if token:
            return token
    try:
        cp = subprocess.run(
            ["gh", "auth", "token"], text=True, capture_output=True, timeout=8
        )
        if cp.returncode == 0 and cp.stdout.strip():
            return cp.stdout.strip()
    except Exception:
        pass
    return ""


def github_request(
    method: str,
    path: str,
    payload: Any | None = None,
    timeout: float = 12.0,
) -> tuple[bool, Any, int]:
    repo = str(CONFIG.get("repo", DEFAULT_REPO))
    url = f"https://api.github.com/repos/{repo}{path}"
    token = resolve_github_token()
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"ThayLinh-PCBridge/{VERSION}",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    try:
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            return True, json.loads(raw) if raw else {}, int(resp.status)
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            detail = json.loads(raw)
        except Exception:
            detail = raw[:1000]
        return False, detail, int(exc.code)
    except Exception as exc:
        return False, str(exc), 0


def parse_action(title: str) -> str | None:
    for prefix in CONFIG.get("prefixes", list(DEFAULT_PREFIXES)):
        prefix = str(prefix)
        if title.upper().startswith(prefix.upper()):
            rest = title[len(prefix) :].strip()
            if not rest:
                return None
            return re.split(r"\s+", rest, maxsplit=1)[0].upper()
    return None


def comment_and_close(issue_number: int, result: dict[str, Any]) -> None:
    token = resolve_github_token()
    if not token:
        return
    text = (
        "```json\n"
        + json.dumps(result, ensure_ascii=False, indent=2)[:6000]
        + "\n```"
    )
    github_request("POST", f"/issues/{issue_number}/comments", {"body": text})
    github_request("PATCH", f"/issues/{issue_number}", {"state": "closed"})


def poll_github_once() -> None:
    ok, issues, status = github_request(
        "GET", "/issues?state=open&per_page=50&sort=created&direction=asc"
    )
    if not ok:
        STATE["github_last_error"] = {
            "time": now_iso(),
            "status": status,
            "detail": issues,
        }
        save_state()
        return
    if not isinstance(issues, list):
        return
    processed = set(
        int(x) for x in STATE.get("processed_issues", []) if str(x).isdigit()
    )
    trusted = str(CONFIG.get("trusted_user", DEFAULT_TRUSTED_USER)).lower()
    for issue in issues:
        if "pull_request" in issue:
            continue
        number = int(issue.get("number", 0) or 0)
        if not number or number in processed:
            continue
        author = str((issue.get("user") or {}).get("login", "")).lower()
        title = str(issue.get("title", ""))
        action = parse_action(title)
        if author != trusted or not action:
            continue
        body = str(issue.get("body") or "")
        log(f"COMMAND issue=#{number} author={author} action={action}")
        started = time.monotonic()
        try:
            result = run_action(action, body)
        except Exception as exc:
            result = {
                "ok": False,
                "error": str(exc),
                "trace": traceback.format_exc(limit=8),
            }
        result.update(
            {
                "issue": number,
                "action": action,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "bridge_version": VERSION,
                "completed_at": now_iso(),
            }
        )
        STATE["last_command"] = {
            "issue": number,
            "action": action,
            "time": now_iso(),
        }
        STATE["last_result"] = result
        processed.add(number)
        STATE["processed_issues"] = sorted(processed)[-500:]
        save_state()
        comment_and_close(number, result)


class LocalHandler(BaseHTTPRequestHandler):
    server_version = f"ThayLinhPCBridge/{VERSION}"

    def _send(self, code: int, obj: Any) -> None:
        payload = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send(200, {"ok": True, "version": VERSION, "time": now_iso()})
        elif self.path == "/status":
            self._send(200, self_test())
        else:
            self._send(404, {"ok": False, "error": "not_found"})

    def log_message(self, fmt: str, *args: Any) -> None:
        return


def local_server_loop() -> None:
    port = int(CONFIG.get("api_port", API_PORT))
    try:
        server = ThreadingHTTPServer(("127.0.0.1", port), LocalHandler)
        server.timeout = 1.0
        log(f"Local rescue API listening on 127.0.0.1:{port}")
        while not STOP.is_set():
            server.handle_request()
        server.server_close()
    except Exception as exc:
        log(f"Local API failed: {exc}")


def maintenance_once() -> None:
    if bool(CONFIG.get("auto_start_hub", True)) and not hub_health()["ok"]:
        log("Hub 4310 unhealthy; attempting repair")
        result = start_hub()
        log("Hub repair: " + json.dumps(result, ensure_ascii=False)[:1000])
    if bool(CONFIG.get("auto_start_desktop_commander", True)) and not desktop_commander_running():
        log("Desktop Commander remote not detected; attempting start")
        result = start_desktop_commander(False)
        log("Desktop Commander start: " + json.dumps(result, ensure_ascii=False)[:1000])


def handle_stop(_signum=None, _frame=None) -> None:
    STOP.set()


def main() -> int:
    if os.name != "nt":
        print("This agent is designed for Windows.", file=sys.stderr)
        return 2
    if not acquire_single_instance():
        log("Another bridge instance is already running; exit.")
        return 0
    signal.signal(signal.SIGINT, handle_stop)
    try:
        signal.signal(signal.SIGTERM, handle_stop)
    except Exception:
        pass
    log(f"START {APP_NAME} v{VERSION} pid={os.getpid()}")
    STATE["started_at"] = now_iso()
    STATE["pid"] = os.getpid()
    STATE["version"] = VERSION
    save_state()

    threading.Thread(target=local_server_loop, daemon=True).start()
    last_maintenance = 0.0
    while not STOP.is_set():
        now = time.monotonic()
        try:
            if now - last_maintenance > 120:
                maintenance_once()
                last_maintenance = now
            poll_github_once()
        except Exception as exc:
            log(f"Main loop error: {exc}\n{traceback.format_exc(limit=8)}")
        STOP.wait(max(15, int(CONFIG.get("poll_seconds", POLL_SECONDS))))
    log("STOP")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
