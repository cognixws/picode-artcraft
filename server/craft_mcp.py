#!/usr/bin/env python3
"""picode-artcraft MCP server (stdio, Python standard library only).

One process per app: `craft_mcp.py <photocraft|vectorcraft|filmcraft|effectcraft|lightcraft|designcraft|printcraft>`.
It lists the app's own MCP tools (server/tools/<app>.json, captured from the
app's bridge mode) plus `app_status` and `app_open`. The first call that needs
the app opens it with its control channel on, then starts the app's own CLI
(`<app>-cli mcp`, bridged to that window) and forwards each call to it, so the
human watches the agent work in the real window.

On WSL the Windows build is used: the `.exe` files run through interop and the
CLI reaches the app on Windows' own loopback, so no mirrored networking is
needed. Paths cross with `wslpath`.
"""

import base64
import functools
import json
import os
import re
import ssl
import struct
import tempfile
import urllib.error
import urllib.request
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
# Every child runs from here, never from the package folder: PiCode replaces that
# folder on an update, and a process whose cwd was deleted makes wslpath fail
# ("No such file or directory") for paths that exist.
SAFE_CWD = "/mnt/c" if os.path.isdir("/mnt/c") else "/"
VERSION = "0.5.0"
STATE_DIR = os.path.join(os.path.expanduser("~"), ".picode-artcraft")
PROTOCOLS = ("2025-06-18", "2025-03-26", "2024-11-05")

APPS = {
    "photocraft": {
        "title": "PhotoCraft",
        "port": 7878,
        "token": True,   # bearer token file; the app creates it
        "roots": True,   # file access only below --automation-*-root
        "connect": lambda port: ["--bridge", f"127.0.0.1:{port}"],
    },
    "vectorcraft": {
        "title": "VectorCraft",
        "port": 7979,
        "token": False,  # its control channel has no token (loopback only)
        "roots": False,  # takes absolute paths
        "connect": lambda port: ["--connect", f"127.0.0.1:{port}"],
    },
    "filmcraft": {
        "title": "FilmCraft",
        "port": 9876,
        "token": False,
        "roots": False,
        "connect": lambda port: ["--bridge", f"127.0.0.1:{port}"],
    },
    "effectcraft": {
        "title": "EffectCraft",
        "port": 9877,
        "token": False,
        "roots": False,
        "connect": lambda port: ["--bridge", str(port)],
    },
    "lightcraft": {
        "title": "LightCraft",
        "port": 7980,
        "token": False,
        "roots": False,
        "connect": lambda port: ["--connect", f"127.0.0.1:{port}"],
    },
    "designcraft": {
        "title": "DesignCraft",
        "port": 7981,    # its own default (7979) is VectorCraft's
        "token": False,
        "roots": False,
        "connect": lambda port: ["--connect", str(port)],
    },
    # PrintCraft's MCP server has no bridge to the window: it edits PDFs
    # headless, only under --root. The window is driven by `printcraft-cli ui`
    # over a control file (random loopback port, token inside), which this
    # server turns into ui_* tools.
    "printcraft": {
        "title": "PrintCraft",
        "port": None,
        "token": False,
        "roots": True,
        "headless": True,
        "connect": lambda port: [],
    },
}

for _name, _spec in APPS.items():  # PICODE_<APP>_PORT moves an app off its default port
    _p = os.environ.get(f"PICODE_{_name.upper()}_PORT", "")
    if _p.isdigit() and _spec["port"] is not None:
        _spec["port"] = int(_p)

# Argument keys that may carry a file path. Only absolute POSIX values are
# translated here: a relative value under `path` can be something else (an
# EffectCraft property path such as `transform/position`).
FILE_KEYS = {"path", "paths", "file", "files", "out", "output", "dir", "folder"}
# FilmCraft's media_import takes absolute paths, one per line, in `text`.
TEXT_PATHS = {("filmcraft", "media_import")}


class ToolError(Exception):
    pass


def log(*args):
    print("picode-artcraft:", *args, file=sys.stderr, flush=True)


# ---------- where the app is ----------

def in_wsl():
    if os.environ.get("WSL_DISTRO_NAME"):
        return True
    try:
        with open("/proc/version") as f:
            return "microsoft" in f.read().lower()
    except OSError:
        return False


WSL = in_wsl()


def find_install(app):
    """Return (dir, gui, cli) or None. PICODE_<APP>_DIR wins."""
    title = APPS[app]["title"]
    ext = ".exe" if WSL else ""
    dirs = []
    env = os.environ.get(f"PICODE_{app.upper()}_DIR")
    if env:
        dirs.append(env if not WSL or env.startswith("/") else wslpath("-u", env))
    if WSL:
        for drive in sorted(os.listdir("/mnt")):
            if len(drive) == 1:
                dirs += [f"/mnt/{drive}/Apps/{title}", f"/mnt/{drive}/Program Files/{title}"]
        users = "/mnt/c/Users"
        if os.path.isdir(users):
            for u in sorted(os.listdir(users)):
                dirs.append(f"{users}/{u}/AppData/Local/Programs/{title}")
                dirs.append(f"{users}/{u}/AppData/Local/{title}")
    else:
        cli = shutil.which(f"{app}-cli")
        if cli:
            dirs.append(os.path.dirname(cli))
        dirs += [os.path.expanduser(f"~/Apps/{title}"), f"/opt/{app}"]
    for d in dirs:
        gui, cli = os.path.join(d, app + ext), os.path.join(d, f"{app}-cli{ext}")
        if os.path.isfile(gui) and os.path.isfile(cli):
            return d, gui, cli
    return None


@functools.lru_cache(maxsize=512)
def wslpath(flag, path):
    """wslpath, cached (a path converts the same way every time) and retried once:
    under load it has failed once in a while on a path that exists."""
    for attempt in (1, 2):
        out = subprocess.run(["wslpath", flag, path], capture_output=True, text=True, timeout=10, cwd=SAFE_CWD)
        if out.returncode == 0:
            return out.stdout.strip()
        if attempt == 1:
            time.sleep(0.3)
    raise ToolError(f"cannot convert path {path!r}: {out.stderr.strip()}")


def to_app_path(path):
    """A path as the app's own OS sees it."""
    return wslpath("-w", path) if WSL else path


def powershell(script):
    exe = shutil.which("powershell.exe") or "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    out = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-Command", script],
                         capture_output=True, text=True, timeout=30, cwd=SAFE_CWD)
    return out.stdout.replace("\r", "").strip()


# ---------- the app's window and control channel ----------

class App:
    def __init__(self, name):
        self.name = name
        self.spec = APPS[name]
        self.root = os.path.realpath(os.environ.get("PICODE_CRAFT_ROOT") or os.getcwd())
        self.state_file = os.path.join(STATE_DIR, f"{name}.json")
        self._token_file = None

    def install(self):
        found = find_install(self.name)
        if not found:
            raise ToolError(
                f"{self.spec['title']} is not installed where picode-artcraft looks "
                f"(<drive>:\\Apps\\{self.spec['title']}, Program Files, AppData\\Local\\Programs). "
                f"Set PICODE_{self.name.upper()}_DIR to the folder that holds "
                f"{self.name}{'.exe' if WSL else ''} and {self.name}-cli.")
        return found

    def private_file(self, suffix):
        """A file of the extension's own, as the app's OS spells it (the token, the control file)."""
        if WSL:
            local = powershell("[Environment]::GetFolderPath('LocalApplicationData')")
            if not local:
                raise ToolError("cannot read %LOCALAPPDATA% from Windows")
            win = local + "\\picode-artcraft"
            os.makedirs(wslpath("-u", win), exist_ok=True)
            return win + f"\\{self.name}-{suffix}"
        os.makedirs(STATE_DIR, mode=0o700, exist_ok=True)
        return os.path.join(STATE_DIR, f"{self.name}-{suffix}")

    def token_file(self):
        """Where the PhotoCraft token lives, as the app's OS spells it."""
        if not self._token_file:
            self._token_file = self.private_file("control.token")
        return self._token_file

    def control_file(self):
        """PrintCraft: the file `--control` writes its loopback port and token to."""
        return self.private_file("ui.json")

    def ui(self, verb, args=None, out=None, timeout=60):
        """Run `printcraft-cli ui --control FILE <verb> k=v…` and parse its JSON answer."""
        cmd = [self.install()[2], "ui", "--control", self.control_file(), verb]
        for k, v in (args or {}).items():
            if v is None:
                continue
            cmd.append(f"{k}={v if isinstance(v, str) else json.dumps(v)}")
        if out:
            cmd += ["--out", out]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, stdin=subprocess.DEVNULL,
                           cwd=SAFE_CWD)
        text = (r.stdout or "").strip()
        if r.returncode != 0:
            raise ToolError((r.stderr or text or f"printcraft-cli ui {verb} failed").strip()[:400])
        try:
            return json.loads(text) if text else {}
        except ValueError:
            return {"text": text}

    def listening_pid(self):
        if self.spec.get("headless"):  # alive = the control file answers
            try:
                return -1 if find_install(self.name) and self.ui("state", timeout=8) is not None else None
            except (ToolError, subprocess.TimeoutExpired, OSError):
                return None
        port = self.spec["port"]
        if WSL:
            pid = powershell(
                f"(Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue"
                " | Select-Object -First 1).OwningProcess")
            return int(pid) if pid.isdigit() else None
        import socket
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=1):
                return -1
        except OSError:
            return None

    def window(self):
        """The app window's handle (the id PiCode's computer tool uses), or None."""
        if not WSL:
            return None
        if self.spec.get("headless"):  # no fixed port: the process' own window
            hwnd = powershell(f"(Get-Process -Name '{self.name}' -ErrorAction SilentlyContinue"
                              " | Where-Object { $_.MainWindowHandle -ne 0 } | Select-Object -First 1).MainWindowHandle")
            return int(hwnd) if hwnd.isdigit() and hwnd != "0" else None
        port = self.spec["port"]
        hwnd = powershell(
            f"$c = Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue"
            " | Select-Object -First 1; if ($c) { (Get-Process -Id $c.OwningProcess).MainWindowHandle }")
        return int(hwnd) if hwnd.isdigit() and hwnd != "0" else None

    def window_hint(self):
        """The app's window, and the human's Agent screen pointed at it.

        With PiCode's screen-follow door (ADR-0230 amendment of 2026-10-06)
        the extension points the screen itself; without it (an older PiCode,
        or the permission not granted) the agent is told how to."""
        hwnd = None
        for _ in range(10):  # the window can appear a moment after the channel
            hwnd = self.window()
            if hwnd:
                break
            time.sleep(0.5)
        if not hwnd:
            return {}
        out = {"window": hwnd}
        followed, why = screen_follow(hwnd)
        if followed:
            out["screen"] = "following this window"
            self.followed = hwnd
        else:
            out["screen"] = f"not followed ({why})"
            out["watch"] = (f"If you have PiCode's computer tool, call it with action screenshot and window {hwnd} "
                            "now: the human's Agent screen panel follows the window you use there.")
        return out

    def follow_once(self):
        """Point the screen at the app the first time a tool opens it (not on every call)."""
        if getattr(self, "followed", None):
            return
        hwnd = self.window()
        if hwnd and screen_follow(hwnd)[0]:
            self.followed = hwnd

    def running_without_control(self):
        """The app runs, but nothing listens on its control port (the human opened it by hand)."""
        if WSL:
            n = powershell(f"@(Get-Process -Name '{self.name}' -ErrorAction SilentlyContinue).Count")
        else:
            out = subprocess.run(["pgrep", "-x", self.name], capture_output=True, text=True, cwd=SAFE_CWD)
            n = str(len(out.stdout.split()))
        return n.isdigit() and int(n) > 0 and not self.listening_pid()

    def read_state(self):
        try:
            with open(self.state_file) as f:
                return json.load(f)
        except (OSError, ValueError):
            return {}

    def status(self):
        found = find_install(self.name)
        state = self.read_state()
        pid = self.listening_pid() if found else None
        st = {
            "app": self.spec["title"],
            "installed": bool(found),
            "folder": (to_app_path(found[0]) if found else None),
            "open_with_control": bool(pid),
            "workspace_root": self.root,
        }
        if self.spec["port"] is not None:
            st["port"] = self.spec["port"]
        if self.spec.get("headless"):
            st["document_tools"] = "work on files under the workspace without the window; ui_* drive the window"
        elif self.spec["roots"] and pid:
            st["files_root"] = state.get("root")
        if pid:
            hwnd = self.window()
            if hwnd:
                st["window"] = hwnd
        elif found and self.running_without_control():
            st["running_without_control"] = True
            st["hint"] = (f"{self.spec['title']} is open without its control channel; ask the human to close it "
                          "so the extension can open it with control on.")
        if not found:
            st["hint"] = f"Install {self.spec['title']} (github.com/storytold/{self.name}/releases)."
        return st

    def ensure_open(self):
        """Open the app with control on, unless it already listens. Returns True if launched now."""
        _, gui, _ = self.install()
        if self.listening_pid():
            if self.spec["roots"] and not self.spec.get("headless"):
                root = self.read_state().get("root")
                if root and root != self.root:
                    raise ToolError(
                        f"{self.spec['title']} is open with files root {root}, not this workspace "
                        f"({self.root}). Work with paths under that root, or ask the human to close "
                        f"{self.spec['title']} so the next call opens it here.")
            return False
        if self.running_without_control():
            raise ToolError(
                f"{self.spec['title']} is already open without its control channel, so the extension cannot "
                f"drive it, and opening a second copy would confuse the human. Ask them to save their work and "
                f"close {self.spec['title']}; the next call opens it with control on.")
        if self.spec.get("headless"):
            args = [gui, "--control", self.control_file()]
        else:
            args = [gui, "--control", str(self.spec["port"])]
        if self.spec["token"]:
            args += ["--control-token-file", self.token_file()]
        if self.spec["roots"] and not self.spec.get("headless"):
            r = to_app_path(self.root)
            args += ["--automation-read-root", r, "--automation-write-root", r]
        os.makedirs(STATE_DIR, exist_ok=True)
        log_path = os.path.join(STATE_DIR, f"{self.name}-app.log")
        with open(log_path, "w") as out:
            subprocess.Popen(args, cwd=os.path.dirname(gui), stdin=subprocess.DEVNULL,
                             stdout=out, stderr=subprocess.STDOUT, start_new_session=True)
        with open(self.state_file, "w") as f:
            json.dump({"root": self.root, "started": time.time()}, f)
        deadline = time.time() + 45
        while time.time() < deadline:
            time.sleep(0.5)
            try:
                with open(log_path) as f:
                    if "control server listening" in f.read():
                        return True
            except OSError:
                pass
            if self.spec.get("headless") and self.listening_pid():
                return True
        raise ToolError(f"{self.spec['title']} did not open its control channel in 45 s; see {log_path}")

    def bridge_cmd(self):
        _, _, cli = self.install()
        if self.spec.get("headless"):  # edits files, no window; confined to the workspace
            return [cli, "mcp", "--root", to_app_path(self.root)]
        cmd = [cli, "mcp"] + self.spec["connect"](self.spec["port"])
        if self.spec["token"]:
            cmd += ["--control-token-file", self.token_file()]
        return cmd

    def path_arg(self, value):
        """Translate a path an agent gives into what the app accepts."""
        if not isinstance(value, str) or not value:
            return value
        if self.spec["roots"]:
            # PhotoCraft: forward-slash relative to the workspace root.
            if os.path.isabs(value):
                rel = os.path.relpath(os.path.realpath(value), self.root)
                if rel.startswith(".."):
                    raise ToolError(f"{value} is outside the workspace ({self.root}); "
                                    f"{self.spec['title']} only reads and writes under it.")
                value = rel
            return value.replace("\\", "/")
        # VectorCraft: an absolute path in the app's OS.
        if WSL and len(value) > 1 and value[1] == ":":
            return value  # already a Windows path
        full = value if os.path.isabs(value) else os.path.join(self.root, value)
        return to_app_path(os.path.normpath(full))

    def translate_abs(self, value, key=None, keys=FILE_KEYS):
        """Turn absolute POSIX paths anywhere in a tool's arguments into the app's paths."""
        if self.spec["roots"] or not WSL:
            return value
        if isinstance(value, dict):
            return {k: self.translate_abs(v, k, keys) for k, v in value.items()}
        if isinstance(value, list):
            return [self.translate_abs(v, key, keys) for v in value]
        if isinstance(value, str) and key in keys:
            lines = value.split("\n")
            if any(l.strip().startswith("/") for l in lines):
                return "\n".join(to_app_path(l.strip()) if l.strip().startswith("/") else l for l in lines)
        return value


# ---------- PiCode's screen-follow door ----------

def screen_follow(hwnd):
    """Ask PiCode to point this agent's Agent screen at window hwnd.

    PiCode gives this server PICODE_SCREEN_FOLLOW (a file with a credential
    bound to this agent and this extension) and PICODE_SCREEN_FOLLOW_URL when
    the extension holds screen:follow. Returns (followed, why)."""
    file, url = os.environ.get("PICODE_SCREEN_FOLLOW"), os.environ.get("PICODE_SCREEN_FOLLOW_URL")
    if not file or not url:
        return False, "this PiCode has no screen-follow door for this extension"
    try:
        with open(file) as f:
            token = f.read().strip()
    except OSError as e:
        return False, f"credential unreadable: {e}"
    req = urllib.request.Request(url, data=json.dumps({"window": hwnd}).encode(), method="POST",
                                 headers={"Content-Type": "application/json", "X-PiCode-Screen-Follow": token})
    ctx = ssl.create_default_context()
    if urllib.request.urlparse(url).hostname in ("localhost", "127.0.0.1"):
        ctx.check_hostname = False  # PiCode's own loopback certificate
        ctx.verify_mode = ssl.CERT_NONE
    try:
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            return r.status == 200, "ok"
    except urllib.error.HTTPError as e:
        try:
            msg = json.loads(e.read() or b"{}").get("error", "")
        except ValueError:
            msg = ""
        return False, msg or f"HTTP {e.code}"
    except (urllib.error.URLError, OSError) as e:
        return False, str(e)


# ---------- the app's own MCP server, bridged ----------

class Bridge:
    def __init__(self, app):
        self.app = app
        self.proc = None
        self.next_id = 1

    def _rpc(self, method, params):
        i = self.next_id
        self.next_id += 1
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "id": i, "method": method, "params": params}) + "\n")
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise ToolError(f"{self.app.spec['title']}'s MCP server stopped")
            try:
                msg = json.loads(line)
            except ValueError:
                continue
            if msg.get("id") == i:
                return msg

    def start(self):
        self.proc = subprocess.Popen(self.app.bridge_cmd(), cwd=SAFE_CWD, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, encoding="utf-8")
        init = self._rpc("initialize", {"protocolVersion": PROTOCOLS[0], "capabilities": {},
                                        "clientInfo": {"name": "picode-artcraft", "version": VERSION}})
        if "error" in init:
            raise ToolError(f"bridge refused: {init['error']}")
        self.proc.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        self.proc.stdin.flush()

    def call(self, name, args):
        for attempt in (1, 2):
            if not self.proc or self.proc.poll() is not None:
                self.start()
            try:
                return self._rpc("tools/call", {"name": name, "arguments": args})
            except (ToolError, BrokenPipeError, OSError):
                self.proc = None
                if attempt == 2:
                    raise
        raise ToolError("unreachable")


# ---------- this server ----------

OWN_TOOLS = [
    {
        "name": "app_status",
        "description": "Whether the app is installed, open with its control channel, and which folder it reads and writes.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "app_open",
        "description": "Open the app on the human's desktop with its control channel on (if it is not already), "
                       "optionally opening a file in it. Other tools open the app on their own; call this to start "
                       "where the human can watch, or to open a file.",
        "inputSchema": {"type": "object", "properties": {
            "file": {"type": "string", "description": "A file to open, absolute or relative to the workspace."}}},
    },
    {
        "name": "app_path",
        "description": "Turn a workspace path into the path to give the app inside command params (import, export, "
                       "open). Absolute paths in path-like params are translated on their own; use this for "
                       "relative ones or to check.",
        "inputSchema": {"type": "object", "required": ["path"], "properties": {
            "path": {"type": "string", "description": "Absolute, or relative to the workspace."}}},
    },
]

PATH_KEYS = {
    "photocraft": {"doc_open": ["path"], "doc_save": ["path"], "doc_export": ["path"]},
    "vectorcraft": {"open_file": ["path"], "save_file": ["path"], "export": ["path"], "screenshot": ["path"]},
    "filmcraft": {},
    "effectcraft": {"open_project": ["path"], "save_project": ["path"], "render_frame": ["path"],
                    "screenshot": ["path"]},
    "lightcraft": {"import": ["paths"], "render_photo": ["path"], "export": ["path", "dir"],
                   "screenshot": ["path"]},
    "designcraft": {"open_document": ["path"], "save_document": ["path"], "place_image": ["path"],
                    "render_page": ["path"], "export_png": ["path"], "screenshot": ["path"]},
    "printcraft": {},  # roots: see rootify
}
# app_open {file}: the tool, its fixed arguments and where the path goes.
OPEN_TOOL = {"photocraft": ("doc_open", {}, "path"), "vectorcraft": ("open_file", {}, "path"),
             "filmcraft": ("command_run", {"id": "file.open"}, "params.path"),
             "effectcraft": ("open_project", {}, "path"),
             "lightcraft": ("import", {}, "paths"), "designcraft": ("open_document", {}, "path")}

# Tools that duplicate another (LightCraft's 359 cmd_* are run_command with a
# fixed id): hidden from the list the agent loads, still forwarded if called.
HIDDEN = {"lightcraft": lambda n: n.startswith("cmd_")}

SNAP_SIDE = 900  # a window picture is shrunk to this width; PiCode's relay is 1 MiB


def png_width(raw):
    return struct.unpack(">I", raw[16:20])[0] if raw[:8] == b"\x89PNG\r\n\x1a\n" else 0


def shrink(b64):
    """Scale a large PNG down to SNAP_SIDE wide with ffmpeg, when it is installed."""
    raw = base64.b64decode(b64)
    if png_width(raw) <= SNAP_SIDE * 1.2 or not shutil.which("ffmpeg"):
        return b64, len(raw)
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.png"), os.path.join(d, "out.png")
        with open(src, "wb") as f:
            f.write(raw)
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", "scale=%d:-1" % SNAP_SIDE, dst],
                           capture_output=True, timeout=30, cwd=SAFE_CWD)
        if r.returncode != 0 or not os.path.exists(dst):
            return b64, len(raw)
        with open(dst, "rb") as f:
            small = f.read()
    return base64.b64encode(small).decode(), len(small)


def abs_looking(v):
    return isinstance(v, str) and (os.path.isabs(v) or bool(re.match(r"^[A-Za-z]:[\\/]", v)) or v.startswith("\\\\"))


def rootify(app, value, key=None):
    """PrintCraft reads and writes only under --root: an absolute POSIX path in a file
    argument becomes relative to the workspace (or is refused when outside it).
    Other values — a bookmark path, a Windows path — pass through; PrintCraft judges them."""
    if isinstance(value, dict):
        return {k: rootify(app, v, k) for k, v in value.items()}
    if isinstance(value, list):
        return [rootify(app, v, key) for v in value]
    if isinstance(value, str) and key in {"path", "paths", "out", "out_dir", "file"} and abs_looking(value):
        if os.path.isabs(value):
            return app.path_arg(value)
    return value


def open_file_in(app, name, file, bridge):
    """Open a workspace file in the app; returns what the app said. Raises ToolError."""
    if name == "printcraft":  # the window, through its control file (the MCP has none)
        rel = app.path_arg(file)
        full = os.path.realpath(os.path.join(app.root, rel))
        if os.path.commonpath([full, app.root]) != app.root:
            raise ToolError(f"{file} is outside the workspace ({app.root}).")
        return app.ui("open", {"path": to_app_path(full)})
    tool, base, kind = OPEN_TOOL[name]
    path = app.path_arg(file)
    call = dict(base)
    if kind == "params.path":
        call["params"] = {"path": path}
    elif kind == "paths":
        call["paths"] = [path]
    else:
        call["path"] = path
    res = bridge.call(tool, call)
    if "error" in res or (res.get("result") or {}).get("isError"):
        raise ToolError(str((res.get("result") and content_value(res["result"])) or (res.get("error") or {}).get("message")
                            or f"{app.spec['title']} refused the file"))
    return content_value(res["result"])


# PrintCraft's window tools: `printcraft-cli ui --control FILE <verb>` as MCP tools.
def _s(desc):
    return {"type": "string", "description": desc}


UI_TOOLS = {
    "ui_state": ("state", "What the live window shows: the document, page, tool and open dialogs.", {}),
    "ui_inspect": ("inspect", "The window's widget tree (role, label, rect, id); narrow it with `query`.",
                   {"query": _s("Only widgets whose label contains this text.")}),
    "ui_click": ("click", "Click a widget by its label or id (from ui_inspect).",
                 {"label": _s("The widget's label."), "id": _s("The widget's id.")}),
    "ui_type": ("type", "Type text into the focused field.", {"text": _s("The text.")}),
    "ui_key": ("key", "Press a key, with modifiers such as [\"command\"] for Ctrl.",
               {"key": _s("The key, e.g. K, Enter, Escape."),
                "modifiers": {"type": "array", "items": {"type": "string"}}}),
    "ui_command": ("command", "Run a menu/tool command by id (list them with ui_commands).",
                   {"id": _s("The command id, e.g. comment.square.")}),
    "ui_commands": ("commands", "Every command of the live window: id, label, menu, shortcut, enabled.", {}),
    "ui_open": ("open", "Open a PDF from the workspace in the live window (opens PrintCraft if needed).",
                {"path": _s("A PDF in the workspace, absolute or relative."), "password": _s("If it is encrypted.")}),
    "ui_screenshot": (None, "A picture of the live window (does not bring it forward).", {}),
}
UI_TOOL_DEFS = [{"name": n, "description": d,
                 "inputSchema": {"type": "object", "properties": props}} for n, (_, d, props) in UI_TOOLS.items()]


def printcraft_screenshot(app):
    """The live window as base64 PNG, shrunk. Raises ToolError."""
    out_dir = os.path.join(STATE_DIR, "out")
    os.makedirs(out_dir, exist_ok=True)
    f = os.path.join(out_dir, f"printcraft-{os.getpid()}.png")
    try:
        app.ui("screenshot", out=to_app_path(f))
        with open(f, "rb") as fh:
            raw = fh.read()
    except OSError as e:
        raise ToolError(f"no picture of the PrintCraft window: {e}")
    finally:
        if os.path.exists(f):
            os.remove(f)
    return shrink(base64.b64encode(raw).decode())[0]


def run_ui_tool(app, tool, args):
    verb, _, _ = UI_TOOLS[tool]
    if tool == "ui_screenshot":
        return {"content": [{"type": "image", "data": printcraft_screenshot(app), "mimeType": "image/png"}]}
    if tool == "ui_open":
        args = dict(args)
        rel = app.path_arg(args.get("path", ""))
        full = os.path.realpath(os.path.join(app.root, rel))
        if os.path.commonpath([full, app.root]) != app.root:
            raise ToolError(f"{args.get('path')} is outside the workspace ({app.root}).")
        args["path"] = to_app_path(full)
    return text_result(app.ui(verb, args))


# Apps whose window can come back tiny or minimized; app_open gives it a usable size.
RESTORE_WINDOW = {"effectcraft"}


def content_value(result):
    """A tool result's text content as data: parsed JSON when it is JSON, else the text."""
    texts = [c.get("text", "") for c in (result or {}).get("content", []) if c.get("type") == "text"]
    if not texts:
        return None
    try:
        return json.loads(texts[0])
    except ValueError:
        return texts[0]


def restore_window(bridge):
    """Resize EffectCraft's window when it reports less than a usable size."""
    try:
        state = content_value(bridge.call("control", {"method": "ui.inspect"}).get("result"))
        w, h = (state or {}).get("window") or (0, 0)
        if w < 1000 or h < 600:
            bridge.call("control", {"method": "ui.resize", "params": {"width": 1500, "height": 900}})
            return {"window_restored": [1500, 900]}
    except (ToolError, OSError, ValueError, TypeError):
        pass
    return {}


def text_result(obj, error=False):
    return {"content": [{"type": "text", "text": obj if isinstance(obj, str) else json.dumps(obj, indent=1)}],
            "isError": error}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in APPS:
        sys.exit("usage: craft_mcp.py " + "|".join(APPS))
    name = sys.argv[1]
    app = App(name)
    bridge = Bridge(app)
    with open(os.path.join(HERE, "tools", f"{name}.json")) as f:
        vendored = json.load(f)
    hidden = HIDDEN.get(name, lambda n: False)
    headless = bool(APPS[name].get("headless"))
    tools = OWN_TOOLS + [t for t in vendored["tools"] if not hidden(t["name"])] + (UI_TOOL_DEFS if headless else [])
    known = {t["name"] for t in vendored["tools"]}
    paths_note = ("paths are relative to the workspace (absolute paths inside it are accepted)"
                  if APPS[name]["roots"] else "paths may be absolute or relative to the workspace")
    if headless:
        through = (f"\n\nThrough PiCode: the document tools edit PDFs in the workspace without a window "
                   f"({paths_note}); nothing is shown to the human until you save and open the file. app_open opens "
                   f"the real window (optionally with a PDF) and points the human's Agent screen at it; ui_* operate "
                   f"that window. If app_open answers `screen: not followed` and you have PiCode's computer tool, take "
                   f"one screenshot of the returned `window`.")
    else:
        through = (f"\n\nThrough PiCode: the app runs on the human's desktop and they watch it. The first call opens it "
                   f"(app_open does so explicitly); {paths_note}. app_open points the human's Agent screen at the app "
                   f"itself (`screen: following this window`); only when it answers `screen: not followed` and you have "
                   f"PiCode's computer tool, take one screenshot of the returned `window` so the panel follows the app.")
    instructions = (vendored.get("instructions") or "") + through

    def handle(msg):
        method, params = msg.get("method"), msg.get("params") or {}
        if method == "initialize":
            v = params.get("protocolVersion")
            return {"protocolVersion": v if v in PROTOCOLS else PROTOCOLS[0],
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": f"picode-{name}", "version": VERSION},
                    "instructions": instructions}
        if method == "ping":
            return {}
        if method == "tools/list":
            return {"tools": tools}
        if method != "tools/call":
            raise LookupError(method)
        tool, args = params.get("name"), dict(params.get("arguments") or {})
        try:
            if tool == "app_status":
                return text_result(app.status())
            if tool == "app_open":
                launched = app.ensure_open()
                out = {"opened": launched, "already_open": not launched}
                if args.get("file"):
                    out["file"] = open_file_in(app, name, args["file"], bridge)
                if name in RESTORE_WINDOW:
                    out.update(restore_window(bridge))
                out.update(app.window_hint())
                return text_result(out)
            if tool == "app_path":
                return text_result({"path": app.path_arg(args.get("path", ""))})
            if headless and tool in UI_TOOLS:
                app.ensure_open()
                app.follow_once()
                return run_ui_tool(app, tool, args)
            if tool not in known:
                return text_result(f"unknown tool {tool}", True)
            for key in PATH_KEYS[name].get(tool, []):
                if key in args:
                    v = args[key]
                    args[key] = [app.path_arg(x) for x in v] if isinstance(v, list) else app.path_arg(v)
            if name == "printcraft":
                args = rootify(app, args)
            else:
                args = app.translate_abs(args, keys=FILE_KEYS | ({"text"} if (name, tool) in TEXT_PATHS else set()))
                app.ensure_open()
                app.follow_once()
            res = bridge.call(tool, args)
            if "error" in res:
                return text_result(res["error"].get("message") or res["error"], True)
            return res["result"]
        except ToolError as e:
            return text_result(str(e), True)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except ValueError:
            continue
        if "id" not in msg:
            continue  # a notification
        reply = {"jsonrpc": "2.0", "id": msg["id"]}
        try:
            reply["result"] = handle(msg)
        except LookupError as e:
            reply["error"] = {"code": -32601, "message": f"method not found: {e}"}
        except Exception as e:  # keep serving
            log("error:", repr(e))
            reply["error"] = {"code": -32603, "message": str(e)}
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
