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
VERSION = "5.4.2"
ROOT = pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home())) / "ThayLinhPCBridge"
ROOT.mkdir(parents=True, exist_ok=True)
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
STATE_FILE = ROOT / "state.json"
CONFIG_FILE = ROOT / "config.json"
LOCK_FILE = ROOT / "agent.lock"

STOP = threading.Event()
STATE_LOCK = threading.Lock()
CONFIG: dict[str, Any] = {}
STATE: dict[str, Any] = {}
BUS_CACHE: pathlib.Path | None = None
BUS_CACHE_AT = 0.0

GITHUB_RESCUE_ACTIONS = {
    "PING", "STATUS", "SELF_TEST", "ZALO_STATUS",
    "START_HUB", "START_COMPUTER_USE", "RESTART_COMPUTER_USE",
    "START_DESKTOP_COMMANDER", "RESTART_DESKTOP_COMMANDER",
    "START_ZALO", "FOCUS_ZALO", "START_CAPCUT", "FOCUS_CAPCUT",
    "REPAIR_ALL",
}
DRIVE_UI_ACTIONS = GITHUB_RESCUE_ACTIONS | {
    "LIST_WINDOWS", "ACTIVE_WINDOW", "FOCUS_WINDOW",
    "MOUSE_POSITION", "MOVE_MOUSE", "CLICK", "DOUBLE_CLICK", "RIGHT_CLICK",
    "KEY", "TYPE_TEXT", "SCREENSHOT", "WAIT", "BATCH",
}


def now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def log(message: str) -> None:
    line = f"{now_iso()} {message}"
    print(line, flush=True)
    try:
        with (LOG_DIR / f"bridge-{datetime.now().strftime('%Y%m%d')}.log").open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass


def load_json(path: pathlib.Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return default


def atomic_json(path: pathlib.Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)


def load_config() -> dict[str, Any]:
    default = {
        "version": VERSION,
        "repo": "nguyenlinhns-arch/stockradar",
        "trusted_user": "nguyenlinhns-arch",
        "github_prefixes": ["[PC-CONTROL]", "[ZALO-CONTROL]"],
        "github_min_issue_number": 110,
        "github_poll_seconds": 180,
        "drive_poll_seconds": 2,
        "heartbeat_seconds": 30,
        "drive_root_folder": "07_CHATGPT_PC",
        "drive_bus_folder": "PC_CONTROL_BUS",
        "hub_url": "http://127.0.0.1:4310/",
        "computer_use_health_urls": ["http://127.0.0.1:8777/health", "http://127.0.0.1:8766/health"],
        "api_port": 4321,
        "auto_start_hub": True,
        "auto_start_computer_use": True,
        "auto_start_desktop_commander": True,
        "app_candidates": {},
    }
    user = load_json(CONFIG_FILE, {})
    if isinstance(user, dict):
        default.update(user)
    return default


def load_state() -> dict[str, Any]:
    state = load_json(STATE_FILE, {})
    if not isinstance(state, dict):
        state = {}
    state.setdefault("processed_issues", [])
    state.setdefault("last_drive_command_id", None)
    state.setdefault("last_command", None)
    state.setdefault("last_result", None)
    state.setdefault("started_at", now_iso())
    return state


def save_state() -> None:
    with STATE_LOCK:
        STATE["updated_at"] = now_iso()
        atomic_json(STATE_FILE, STATE)


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


def http_get(url: str, timeout: float = 3.0) -> tuple[bool, Any]:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": f"ThayLinh-PCBridge/{VERSION}"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                body: Any = json.loads(raw)
            except Exception:
                body = raw[:500]
            return 200 <= int(resp.status) < 500, body
    except Exception as exc:
        return False, str(exc)


def hub_health() -> dict[str, Any]:
    ok, _ = http_get(str(CONFIG.get("hub_url", "http://127.0.0.1:4310/")), 2)
    return {"ok": ok}


def computer_use_health() -> dict[str, Any]:
    for url in CONFIG.get("computer_use_health_urls", []):
        ok, detail = http_get(str(url), 2)
        if ok:
            return {"ok": True, "url": str(url), "detail": detail if isinstance(detail, dict) else None}
    return {"ok": False}


def detached_flags() -> int:
    return (0x00000008 | 0x00000200) if os.name == "nt" else 0


def start_detached(argv: list[str], cwd: str | None = None) -> dict[str, Any]:
    try:
        subprocess.Popen(argv, cwd=cwd, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, creationflags=detached_flags(), close_fds=(os.name != "nt"))
        return {"ok": True}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_helper(script_name: str, extra: list[str] | None = None, wait_seconds: int = 0) -> dict[str, Any]:
    script = ROOT / script_name
    if not script.exists():
        return {"ok": False, "error": f"{script_name} missing"}
    argv = ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-WindowStyle", "Hidden", "-File", str(script)]
    if extra:
        argv.extend(extra)
    result = start_detached(argv, str(ROOT))
    if wait_seconds and result.get("ok"):
        time.sleep(wait_seconds)
    return result


def start_hub() -> dict[str, Any]:
    if hub_health()["ok"]:
        return {"ok": True, "status": "already_healthy"}
    helper = run_helper("repair_hub.ps1", wait_seconds=3)
    for _ in range(12):
        if hub_health()["ok"]:
            return {"ok": True, "status": "started"}
        time.sleep(1)
    return {"ok": False, "status": "unavailable", "helper": helper}


def start_computer_use(force: bool = False) -> dict[str, Any]:
    if computer_use_health()["ok"] and not force:
        return {"ok": True, "status": "already_healthy"}
    helper = run_helper("start_computer_use.ps1", ["-Force"] if force else [], 2)
    for _ in range(12):
        health = computer_use_health()
        if health["ok"]:
            return {"ok": True, "status": "started", "health": health}
        time.sleep(1)
    return {"ok": False, "status": "unavailable", "helper": helper}


def process_command_lines() -> str:
    if os.name != "nt":
        return ""
    ps = "Get-CimInstance Win32_Process|Select-Object ProcessId,Name,CommandLine|ConvertTo-Json -Compress"
    try:
        cp = subprocess.run(["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", ps],
                            text=True, capture_output=True, timeout=15)
        return cp.stdout or ""
    except Exception:
        return ""


def desktop_commander_running() -> bool:
    text = process_command_lines().lower()
    return "desktop-commander" in text and "remote" in text


def desktop_commander_paired() -> bool:
    return (pathlib.Path.home() / ".desktop-commander-device" / "device.json").exists()


def start_desktop_commander(force: bool = False, allow_pairing: bool = False) -> dict[str, Any]:
    if desktop_commander_running() and not force:
        return {"ok": True, "status": "already_running", "paired": desktop_commander_paired()}
    if not desktop_commander_paired() and not allow_pairing:
        return {"ok": False, "status": "pairing_required", "paired": False}
    extra: list[str] = []
    if force:
        extra.append("-Force")
    if allow_pairing:
        extra.append("-AllowPairing")
    helper = run_helper("start_desktop_commander.ps1", extra, 3)
    return {"ok": desktop_commander_running(), "status": "running" if desktop_commander_running() else "not_running",
            "paired": desktop_commander_paired(), "helper": helper}


def expanded(value: str) -> str:
    return os.path.expandvars(os.path.expanduser(value))


def find_executable(app: str) -> pathlib.Path | None:
    app = app.lower().strip()
    for raw in CONFIG.get("app_candidates", {}).get(app, []):
        p = pathlib.Path(expanded(str(raw)))
        if p.exists():
            return p
    local = pathlib.Path(os.environ.get("LOCALAPPDATA", pathlib.Path.home()))
    roots = {"zalo": [local / "Programs" / "Zalo", local / "Zalo"],
             "capcut": [local / "CapCut", local / "Programs" / "CapCut"]}.get(app, [])
    target = {"zalo": "Zalo.exe", "capcut": "CapCut.exe"}.get(app, "")
    for root in roots:
        if not target or not root.exists():
            continue
        try:
            for p in root.rglob(target):
                if p.is_file():
                    return p
        except Exception:
            pass
    return None


def configure_user32():
    from ctypes import wintypes
    user32 = ctypes.windll.user32
    user32.EnumWindows.argtypes = [ctypes.c_void_p, wintypes.LPARAM]
    user32.EnumWindows.restype = wintypes.BOOL
    user32.IsWindowVisible.argtypes = [wintypes.HWND]
    user32.IsWindowVisible.restype = wintypes.BOOL
    user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    user32.GetWindowTextLengthW.restype = ctypes.c_int
    user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    user32.GetWindowTextW.restype = ctypes.c_int
    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND
    user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    user32.ShowWindow.restype = wintypes.BOOL
    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL
    user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
    user32.SetCursorPos.restype = wintypes.BOOL
    user32.GetCursorPos.argtypes = [ctypes.POINTER(wintypes.POINT)]
    user32.GetCursorPos.restype = wintypes.BOOL
    return user32


def list_windows() -> list[dict[str, Any]]:
    if os.name != "nt":
        return []
    from ctypes import wintypes
    user32 = configure_user32()
    kernel32 = ctypes.windll.kernel32
    kernel32.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel32.OpenProcess.restype = wintypes.HANDLE
    kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel32.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel32.QueryFullProcessImageNameW.restype = wintypes.BOOL
    result: list[dict[str, Any]] = []
    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd): return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0: return True
        title_buf = ctypes.create_unicode_buffer(length + 1)
        user32.GetWindowTextW(hwnd, title_buf, length + 1)
        title = title_buf.value.strip()
        if not title: return True
        pid = wintypes.DWORD(); user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        proc_name = ""
        hproc = kernel32.OpenProcess(0x1000, False, pid.value)
        if hproc:
            try:
                size = wintypes.DWORD(32768); path_buf = ctypes.create_unicode_buffer(size.value)
                if kernel32.QueryFullProcessImageNameW(hproc, 0, path_buf, ctypes.byref(size)):
                    proc_name = pathlib.Path(path_buf.value).name
            finally: kernel32.CloseHandle(hproc)
        result.append({"hwnd": int(hwnd), "title": title[:300], "pid": int(pid.value), "process": proc_name})
        return True
    user32.EnumWindows(cb, 0)
    return result[:200]


def active_window() -> dict[str, Any]:
    if os.name != "nt": return {"ok": False}
    user32 = configure_user32(); hwnd = user32.GetForegroundWindow()
    if not hwnd: return {"ok": False}
    length = user32.GetWindowTextLengthW(hwnd); buf = ctypes.create_unicode_buffer(max(1, length + 1))
    user32.GetWindowTextW(hwnd, buf, len(buf))
    return {"ok": True, "hwnd": int(hwnd), "title": buf.value[:300]}


def focus_window(title_contains: str) -> dict[str, Any]:
    if os.name != "nt" or not title_contains: return {"ok": False, "error": "title_contains required"}
    user32 = configure_user32(); needle = title_contains.casefold(); matched = {"hwnd": 0, "title": ""}
    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def cb(hwnd, _):
        if not user32.IsWindowVisible(hwnd): return True
        length = user32.GetWindowTextLengthW(hwnd)
        if length <= 0: return True
        buf = ctypes.create_unicode_buffer(length + 1); user32.GetWindowTextW(hwnd, buf, length + 1)
        if needle in buf.value.casefold(): matched["hwnd"] = int(hwnd); matched["title"] = buf.value[:300]; return False
        return True
    user32.EnumWindows(cb, 0)
    if not matched["hwnd"]: return {"ok": False, "error": "window_not_found"}
    user32.ShowWindow(matched["hwnd"], 9); user32.SetForegroundWindow(matched["hwnd"]); time.sleep(0.2)
    return {"ok": True, **matched}


def focus_process(exe_name: str) -> bool:
    target = exe_name.casefold()
    for w in list_windows():
        if str(w.get("process", "")).casefold() == target and focus_window(str(w.get("title", ""))).get("ok"):
            return True
    return False


def start_app(app: str, focus: bool = True) -> dict[str, Any]:
    exe = find_executable(app)
    if not exe: return {"ok": False, "error": f"{app}_not_found"}
    if focus and focus_process(exe.name): return {"ok": True, "status": "focused"}
    result = start_detached([str(exe)], str(exe.parent))
    if result.get("ok"):
        time.sleep(2); result["focused"] = focus_process(exe.name) if focus else False
    return result


def mouse_position() -> dict[str, Any]:
    if os.name != "nt": return {"ok": False}
    from ctypes import wintypes
    pt = wintypes.POINT(); configure_user32().GetCursorPos(ctypes.byref(pt))
    return {"ok": True, "x": int(pt.x), "y": int(pt.y)}


def move_mouse(x: int, y: int) -> dict[str, Any]:
    if os.name != "nt": return {"ok": False}
    ok = bool(configure_user32().SetCursorPos(int(x), int(y)))
    return {"ok": ok, "x": int(x), "y": int(y)}


def click_mouse(x: int, y: int, button: str = "left", count: int = 1) -> dict[str, Any]:
    if os.name != "nt": return {"ok": False}
    user32 = configure_user32(); user32.SetCursorPos(int(x), int(y))
    down, up = {"left": (0x0002,0x0004), "right": (0x0008,0x0010), "middle": (0x0020,0x0040)}.get(button.lower(), (0x0002,0x0004))
    for _ in range(max(1, min(int(count), 3))):
        user32.mouse_event(down,0,0,0,0); user32.mouse_event(up,0,0,0,0); time.sleep(0.08)
    return {"ok": True, "x": int(x), "y": int(y), "button": button, "count": int(count)}


def key_combo(spec: str) -> dict[str, Any]:
    if os.name != "nt" or not spec: return {"ok": False, "error": "keys required"}
    user32 = ctypes.windll.user32; tokens = [x.strip().upper() for x in spec.split("+") if x.strip()]
    vk = {"CTRL":0x11,"CONTROL":0x11,"ALT":0x12,"SHIFT":0x10,"WIN":0x5B,"WINDOWS":0x5B,"ENTER":0x0D,"RETURN":0x0D,
          "TAB":0x09,"ESC":0x1B,"ESCAPE":0x1B,"SPACE":0x20,"BACKSPACE":0x08,"DELETE":0x2E,"HOME":0x24,"END":0x23,
          "PGUP":0x21,"PAGEUP":0x21,"PGDN":0x22,"PAGEDOWN":0x22,"LEFT":0x25,"UP":0x26,"RIGHT":0x27,"DOWN":0x28}
    for i in range(1,13): vk[f"F{i}"] = 0x6F+i
    def code(t: str):
        if t in vk: return vk[t]
        if len(t)==1 and t.isalnum(): return ord(t)
        return None
    codes=[code(t) for t in tokens]
    if any(c is None for c in codes): return {"ok": False, "error": "unsupported_key", "keys": spec}
    for c in codes: user32.keybd_event(int(c),0,0,0); time.sleep(0.03)
    for c in reversed(codes): user32.keybd_event(int(c),0,0x0002,0); time.sleep(0.03)
    return {"ok": True, "keys": spec}


def type_unicode(text: str) -> dict[str, Any]:
    if len(text) > 10000: return {"ok": False, "error": "text_too_long"}
    if os.name != "nt": return {"ok": False}
    from ctypes import wintypes
    class KEYBDINPUT(ctypes.Structure):
        _fields_=[("wVk",wintypes.WORD),("wScan",wintypes.WORD),("dwFlags",wintypes.DWORD),("time",wintypes.DWORD),("dwExtraInfo",wintypes.WPARAM)]
    class U(ctypes.Union): _fields_=[("ki",KEYBDINPUT)]
    class INPUT(ctypes.Structure): _anonymous_=("u",); _fields_=[("type",wintypes.DWORD),("u",U)]
    units=text.encode("utf-16-le", errors="surrogatepass"); sent=0
    for i in range(0,len(units),2):
        unit=int.from_bytes(units[i:i+2],"little")
        down=INPUT(type=1,ki=KEYBDINPUT(0,unit,0x0004,0,0)); up=INPUT(type=1,ki=KEYBDINPUT(0,unit,0x0004|0x0002,0,0))
        if ctypes.windll.user32.SendInput(1,ctypes.byref(down),ctypes.sizeof(INPUT))==1:
            ctypes.windll.user32.SendInput(1,ctypes.byref(up),ctypes.sizeof(INPUT)); sent+=1
    return {"ok": sent==len(units)//2, "chars": len(text), "utf16_units": sent}


def capture_screenshot(bus: pathlib.Path | None, command_id: str) -> dict[str, Any]:
    if os.name != "nt": return {"ok": False}
    if bus is None: return {"ok": False, "error": "drive_bus_not_found"}
    safe=re.sub(r"[^A-Za-z0-9_.-]+","_",command_id)[:80]; out=bus/f"SCREENSHOT_{safe}.png"; pe=str(out).replace("'","''")
    ps=("Add-Type -AssemblyName System.Windows.Forms;Add-Type -AssemblyName System.Drawing;"
        "$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds;$bmp=New-Object System.Drawing.Bitmap($b.Width,$b.Height);"
        "$g=[System.Drawing.Graphics]::FromImage($bmp);$g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size);"
        f"$bmp.Save('{pe}',[System.Drawing.Imaging.ImageFormat]::Png);$g.Dispose();$bmp.Dispose();"
        "Write-Output ($b.Width.ToString()+'x'+$b.Height.ToString())")
    try:
        cp=subprocess.run(["powershell.exe","-NoProfile","-ExecutionPolicy","Bypass","-Command",ps],text=True,capture_output=True,timeout=20)
        return {"ok": cp.returncode==0 and out.exists(), "file": out.name, "size": cp.stdout.strip()}
    except Exception as exc: return {"ok": False, "error": str(exc)}


def discover_drive_bus(force: bool = False) -> pathlib.Path | None:
    global BUS_CACHE, BUS_CACHE_AT
    now=time.monotonic()
    if not force and BUS_CACHE is not None and now-BUS_CACHE_AT<20 and BUS_CACHE.exists(): return BUS_CACHE
    BUS_CACHE_AT=now; root_name=str(CONFIG.get("drive_root_folder","07_CHATGPT_PC")); bus_name=str(CONFIG.get("drive_bus_folder","PC_CONTROL_BUS")); home=pathlib.Path.home()
    candidates=[home/"Google Drive"/"My Drive"/root_name/bus_name, home/"My Drive"/root_name/bus_name]
    if os.name=="nt":
        for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            root=pathlib.Path(f"{letter}:\\")
            try:
                if not root.exists(): continue
            except Exception: continue
            candidates += [root/"My Drive"/root_name/bus_name, root/root_name/bus_name, root/"Google Drive"/"My Drive"/root_name/bus_name]
    seen=set()
    for p in candidates:
        key=str(p).casefold()
        if key in seen: continue
        seen.add(key)
        try:
            if p.exists() and p.is_dir(): BUS_CACHE=p; return p
        except Exception: pass
    BUS_CACHE=None; return None


def self_test() -> dict[str, Any]:
    bus=discover_drive_bus(); active=active_window()
    return {"ok":True,"version":VERSION,"time":now_iso(),"drive_bus_found":bool(bus),"hub_ok":bool(hub_health().get("ok")),
            "computer_use":computer_use_health(),"desktop_commander_running":desktop_commander_running(),
            "desktop_commander_paired":desktop_commander_paired(),"zalo_found":bool(find_executable("zalo")),
            "capcut_found":bool(find_executable("capcut")),"active_window":active.get("title") if active.get("ok") else None,
            "last_command":STATE.get("last_command"),"last_result":STATE.get("last_result")}


def sanitize_result(result: dict[str, Any]) -> dict[str, Any]:
    safe=dict(result); safe.pop("argv",None); return safe


def write_drive_readback(kind: str, result: dict[str, Any], command_id: str | None = None) -> bool:
    bus=discover_drive_bus()
    if bus is None: return False
    payload={"schema":1,"bridge":APP_NAME,"version":VERSION,"kind":kind,"time":now_iso(),"command_id":command_id,
             "status":self_test(),"result":sanitize_result(result)}
    try:
        atomic_json(bus/"LATEST.json",payload)
        if command_id:
            safe=re.sub(r"[^A-Za-z0-9_.-]+","_",command_id)[:80]; atomic_json(bus/f"RESULT_{safe}.json",payload)
        return True
    except Exception as exc: log(f"Drive readback failed: {exc}"); return False


def run_action(action: str, args: dict[str, Any] | None = None, source: str = "drive", command_id: str = "") -> dict[str, Any]:
    args=args or {}; action=action.upper().strip(); allowed=DRIVE_UI_ACTIONS if source=="drive" else GITHUB_RESCUE_ACTIONS
    if action not in allowed: return {"ok":False,"error":"action_not_allowed","action":action,"source":source}
    if action=="PING": return {"ok":True,"pong":True,"version":VERSION}
    if action in {"STATUS","SELF_TEST","ZALO_STATUS"}: return self_test()
    if action=="START_HUB": return start_hub()
    if action=="START_COMPUTER_USE": return start_computer_use(False)
    if action=="RESTART_COMPUTER_USE": return start_computer_use(True)
    if action=="START_DESKTOP_COMMANDER": return start_desktop_commander(False,bool(args.get("allow_pairing",False)))
    if action=="RESTART_DESKTOP_COMMANDER": return start_desktop_commander(True,bool(args.get("allow_pairing",False)))
    if action=="START_ZALO": return start_app("zalo",True)
    if action=="FOCUS_ZALO":
        exe=find_executable("zalo"); return {"ok":bool(exe and focus_process(exe.name))}
    if action=="START_CAPCUT": return start_app("capcut",True)
    if action=="FOCUS_CAPCUT":
        exe=find_executable("capcut"); return {"ok":bool(exe and focus_process(exe.name))}
    if action=="REPAIR_ALL":
        hub=start_hub(); cu=start_computer_use(False); rdc=start_desktop_commander(False,False)
        return {"ok":bool(hub.get("ok") or cu.get("ok") or rdc.get("ok")),"hub":hub,"computer_use":cu,"desktop_commander":rdc}
    if action=="LIST_WINDOWS": return {"ok":True,"windows":list_windows()}
    if action=="ACTIVE_WINDOW": return active_window()
    if action=="FOCUS_WINDOW": return focus_window(str(args.get("title_contains","")))
    if action=="MOUSE_POSITION": return mouse_position()
    if action=="MOVE_MOUSE": return move_mouse(int(args.get("x",0)),int(args.get("y",0)))
    if action in {"CLICK","DOUBLE_CLICK","RIGHT_CLICK"}:
        button="right" if action=="RIGHT_CLICK" else str(args.get("button","left")); count=2 if action=="DOUBLE_CLICK" else int(args.get("count",1))
        return click_mouse(int(args.get("x",0)),int(args.get("y",0)),button,count)
    if action=="KEY": return key_combo(str(args.get("keys","")))
    if action=="TYPE_TEXT": return type_unicode(str(args.get("text","")))
    if action=="SCREENSHOT": return capture_screenshot(discover_drive_bus(),command_id or f"shot-{int(time.time())}")
    if action=="WAIT":
        seconds=max(0.0,min(float(args.get("seconds",0.5)),10.0)); time.sleep(seconds); return {"ok":True,"seconds":seconds}
    if action=="BATCH":
        steps=args.get("steps",[])
        if not isinstance(steps,list): return {"ok":False,"error":"steps_must_be_list"}
        if len(steps)>50: return {"ok":False,"error":"too_many_steps"}
        outputs=[]
        for index,step in enumerate(steps):
            if not isinstance(step,dict): outputs.append({"ok":False,"index":index,"error":"invalid_step"}); break
            sub_action=str(step.get("action","")).upper().strip()
            if sub_action=="BATCH": outputs.append({"ok":False,"index":index,"error":"nested_batch_not_allowed"}); break
            sub_args=step.get("args",{}) if isinstance(step.get("args",{}),dict) else {}
            out=run_action(sub_action,sub_args,"drive",f"{command_id}-{index}"); outputs.append({"index":index,"action":sub_action,"result":out})
            if not out.get("ok",False) and bool(step.get("stop_on_error",True)): break
            delay_ms=max(0,min(int(step.get("delay_ms",0)),5000))
            if delay_ms: time.sleep(delay_ms/1000.0)
        return {"ok":all(bool(x.get("result",x).get("ok",False)) for x in outputs),"steps":outputs}
    return {"ok":False,"error":"unhandled_action"}


def process_drive_command(command: dict[str, Any]) -> None:
    command_id=str(command.get("id","")).strip(); action=str(command.get("action","")).strip().upper(); args=command.get("args",{})
    if not command_id or not action or not isinstance(args,dict): return
    started=time.monotonic()
    try: result=run_action(action,args,"drive",command_id)
    except Exception as exc: result={"ok":False,"error":str(exc),"trace":traceback.format_exc(limit=8)}
    result.update({"action":action,"duration_ms":int((time.monotonic()-started)*1000),"completed_at":now_iso()})
    STATE["last_drive_command_id"]=command_id; STATE["last_command"]={"source":"drive","id":command_id,"action":action,"time":now_iso()}; STATE["last_result"]=sanitize_result(result); save_state()
    write_drive_readback("command_result",result,command_id); log(f"DRIVE command id={command_id} action={action} ok={result.get('ok')}")


def poll_drive_once() -> None:
    bus=discover_drive_bus()
    if bus is None: return
    command_file=bus/"command.json"
    if not command_file.exists(): return
    command=load_json(command_file,{})
    if not isinstance(command,dict): return
    command_id=str(command.get("id","")).strip()
    if not command_id: return
    last=STATE.get("last_drive_command_id")
    if last is None and not bool(command.get("execute_on_first_seen",False)):
        STATE["last_drive_command_id"]=command_id; STATE["last_command"]={"source":"drive","id":command_id,"action":"BUS_BASELINE","time":now_iso()}; save_state()
        write_drive_readback("bus_online",{"ok":True,"baseline_id":command_id},None); return
    if command_id==str(last): return
    process_drive_command(command)


def github_request(path: str, timeout: float = 12.0) -> tuple[bool, Any]:
    repo=str(CONFIG.get("repo","nguyenlinhns-arch/stockradar")); url=f"https://api.github.com/repos/{repo}{path}"
    try:
        req=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json","User-Agent":f"ThayLinh-PCBridge/{VERSION}","X-GitHub-Api-Version":"2022-11-28"})
        with urllib.request.urlopen(req,timeout=timeout) as resp: return True,json.loads(resp.read().decode("utf-8",errors="replace"))
    except Exception as exc: return False,str(exc)


def parse_github_action(title: str) -> str | None:
    for prefix in CONFIG.get("github_prefixes",["[PC-CONTROL]","[ZALO-CONTROL]"]):
        p=str(prefix)
        if title.upper().startswith(p.upper()):
            rest=title[len(p):].strip(); return re.split(r"\s+",rest,maxsplit=1)[0].upper() if rest else None
    return None


def poll_github_once() -> None:
    ok,issues=github_request("/issues?state=open&per_page=30&sort=created&direction=desc")
    if not ok or not isinstance(issues,list): return
    min_issue=int(CONFIG.get("github_min_issue_number",110)); processed={int(x) for x in STATE.get("processed_issues",[]) if str(x).isdigit()}; trusted=str(CONFIG.get("trusted_user","nguyenlinhns-arch")).casefold()
    for issue in reversed(issues):
        if "pull_request" in issue: continue
        number=int(issue.get("number",0) or 0)
        if number<min_issue or number in processed: continue
        author=str((issue.get("user") or {}).get("login","")).casefold(); action=parse_github_action(str(issue.get("title","")))
        if author!=trusted or not action or action not in GITHUB_RESCUE_ACTIONS: continue
        started=time.monotonic()
        try: result=run_action(action,{},"github",str(number))
        except Exception as exc: result={"ok":False,"error":str(exc)}
        result.update({"action":action,"issue":number,"duration_ms":int((time.monotonic()-started)*1000)})
        processed.add(number); STATE["processed_issues"]=sorted(processed)[-500:]; STATE["last_command"]={"source":"github","id":number,"action":action,"time":now_iso()}; STATE["last_result"]=sanitize_result(result); save_state()
        write_drive_readback("github_rescue_result",result,f"gh-{number}"); log(f"GITHUB rescue issue={number} action={action} ok={result.get('ok')}")


class LocalHandler(BaseHTTPRequestHandler):
    server_version=f"ThayLinhPCBridge/{VERSION}"
    def _send(self,code:int,obj:Any)->None:
        data=json.dumps(obj,ensure_ascii=False).encode("utf-8"); self.send_response(code); self.send_header("Content-Type","application/json; charset=utf-8"); self.send_header("Content-Length",str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self)->None:
        if self.path=="/health": self._send(200,{"ok":True,"version":VERSION,"time":now_iso(),"drive_bus_found":bool(discover_drive_bus())})
        elif self.path=="/status": self._send(200,self_test())
        else: self._send(404,{"ok":False,"error":"not_found"})
    def log_message(self,fmt:str,*args:Any)->None: return


def local_server_loop()->None:
    port=int(CONFIG.get("api_port",4321))
    try:
        server=ThreadingHTTPServer(("127.0.0.1",port),LocalHandler); server.timeout=1.0; log(f"Local API listening on 127.0.0.1:{port}")
        while not STOP.is_set(): server.handle_request()
        server.server_close()
    except Exception as exc: log(f"Local API failed: {exc}")


def maintenance_once()->None:
    if bool(CONFIG.get("auto_start_hub",True)) and not hub_health()["ok"]: log("Maintenance: repairing Hub"); start_hub()
    if bool(CONFIG.get("auto_start_computer_use",True)) and not computer_use_health()["ok"]: log("Maintenance: repairing Computer Use"); start_computer_use(False)
    if bool(CONFIG.get("auto_start_desktop_commander",True)) and desktop_commander_paired() and not desktop_commander_running(): log("Maintenance: starting paired Desktop Commander"); start_desktop_commander(False,False)


def handle_stop(_signum=None,_frame=None)->None: STOP.set()


def main()->int:
    global CONFIG,STATE
    if os.name!="nt": print("This agent is designed for Windows.",file=sys.stderr); return 2
    CONFIG=load_config(); STATE=load_state()
    if not acquire_single_instance(): log("Another bridge instance is already running; exit."); return 0
    signal.signal(signal.SIGINT,handle_stop)
    try: signal.signal(signal.SIGTERM,handle_stop)
    except Exception: pass
    STATE["started_at"]=now_iso(); STATE["pid"]=os.getpid(); STATE["version"]=VERSION; save_state(); log(f"START {APP_NAME} v{VERSION} pid={os.getpid()}")
    threading.Thread(target=local_server_loop,daemon=True).start()
    last_maintenance=last_github=last_heartbeat=0.0
    while not STOP.is_set():
        now=time.monotonic()
        try:
            poll_drive_once()
            if now-last_maintenance>=60: maintenance_once(); last_maintenance=now
            if now-last_github>=max(60,int(CONFIG.get("github_poll_seconds",180))): poll_github_once(); last_github=now
            if now-last_heartbeat>=max(10,int(CONFIG.get("heartbeat_seconds",30))): write_drive_readback("heartbeat",{"ok":True},None); last_heartbeat=now
        except Exception as exc: log(f"Main loop error: {exc}\n{traceback.format_exc(limit=8)}")
        STOP.wait(max(1,int(CONFIG.get("drive_poll_seconds",2))))
    log("STOP"); return 0


if __name__=="__main__": raise SystemExit(main())
