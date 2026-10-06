#!/usr/bin/env python3
"""picode-artcraft MCP server (stdio, Python standard library only).

One process per app: `craft_mcp.py <photocraft|vectorcraft|filmcraft|effectcraft>`.
It lists the app's own MCP tools (server/tools/<app>.json, captured from the
app's bridge mode) plus `app_status` and `app_open`. The first call that needs
the app opens it with its control channel on, then starts the app's own CLI
(`<app>-cli mcp`, bridged to that window) and forwards each call to it, so the
human watches the agent work in the real window.

On WSL the Windows build is used: the `.exe` files run through interop and the
CLI reaches the app on Windows' own loopback, so no mirrored networking is
needed. Paths cross with `wslpath`.
"""

import json
import os
import shutil
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
VERSION = "0.2.0"
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
}

for _name, _spec in APPS.items():  # PICODE_<APP>_PORT moves an app off its default port
    _p = os.environ.get(f"PICODE_{_name.upper()}_PORT", "")
    if _p.isdigit():
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


def wslpath(flag, path):
    out = subprocess.run(["wslpath", flag, path], capture_output=True, text=True, timeout=10)
    if out.returncode != 0:
        raise ToolError(f"cannot convert path {path!r}: {out.stderr.strip()}")
    return out.stdout.strip()


def to_app_path(path):
    """A path as the app's own OS sees it."""
    return wslpath("-w", path) if WSL else path


def powershell(script):
    exe = shutil.which("powershell.exe") or "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
    out = subprocess.run([exe, "-NoProfile", "-NonInteractive", "-Command", script],
                         capture_output=True, text=True, timeout=30, cwd="/mnt/c")
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

    def token_file(self):
        """Where the PhotoCraft token lives, as the app's OS spells it."""
        if self._token_file:
            return self._token_file
        if WSL:
            local = powershell("[Environment]::GetFolderPath('LocalApplicationData')")
            if not local:
                raise ToolError("cannot read %LOCALAPPDATA% from Windows")
            win = local + "\\picode-artcraft"
            os.makedirs(wslpath("-u", win), exist_ok=True)
            self._token_file = win + f"\\{self.name}-control.token"
        else:
            os.makedirs(STATE_DIR, mode=0o700, exist_ok=True)
            self._token_file = os.path.join(STATE_DIR, f"{self.name}-control.token")
        return self._token_file

    def listening_pid(self):
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
        port = self.spec["port"]
        hwnd = powershell(
            f"$c = Get-NetTCPConnection -LocalPort {port} -State Listen -ErrorAction SilentlyContinue"
            " | Select-Object -First 1; if ($c) { (Get-Process -Id $c.OwningProcess).MainWindowHandle }")
        return int(hwnd) if hwnd.isdigit() and hwnd != "0" else None

    def window_hint(self):
        hwnd = None
        for _ in range(10):  # the window can appear a moment after the channel
            hwnd = self.window()
            if hwnd:
                break
            time.sleep(0.5)
        if not hwnd:
            return {}
        return {"window": hwnd,
                "watch": f"If you have PiCode's computer tool, call it with action screenshot and window {hwnd} "
                         "now: the human's Agent screen panel follows the window you use there."}

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
            "port": self.spec["port"],
            "workspace_root": self.root,
        }
        if self.spec["roots"] and pid:
            st["files_root"] = state.get("root")
        if pid:
            st.update(self.window_hint())
        if not found:
            st["hint"] = f"Install {self.spec['title']} (github.com/storytold/{self.name}/releases)."
        return st

    def ensure_open(self):
        """Open the app with control on, unless it already listens. Returns True if launched now."""
        _, gui, _ = self.install()
        if self.listening_pid():
            if self.spec["roots"]:
                root = self.read_state().get("root")
                if root and root != self.root:
                    raise ToolError(
                        f"{self.spec['title']} is open with files root {root}, not this workspace "
                        f"({self.root}). Work with paths under that root, or ask the human to close "
                        f"{self.spec['title']} so the next call opens it here.")
            return False
        args = [gui, "--control", str(self.spec["port"])]
        if self.spec["token"]:
            args += ["--control-token-file", self.token_file()]
        if self.spec["roots"]:
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
        raise ToolError(f"{self.spec['title']} did not open its control channel in 45 s; see {log_path}")

    def bridge_cmd(self):
        _, _, cli = self.install()
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
        self.proc = subprocess.Popen(self.app.bridge_cmd(), stdin=subprocess.PIPE, stdout=subprocess.PIPE,
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
}
# app_open {file}: the tool and argument that open a file in each app.
OPEN_TOOL = {"photocraft": ("doc_open", {}), "vectorcraft": ("open_file", {}),
             "filmcraft": ("command_run", {"id": "file.open"}), "effectcraft": ("open_project", {})}


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
    tools = OWN_TOOLS + vendored["tools"]
    known = {t["name"] for t in vendored["tools"]}
    paths_note = ("paths are relative to the workspace (absolute paths inside it are accepted)"
                  if APPS[name]["roots"] else "paths may be absolute or relative to the workspace")
    instructions = (vendored.get("instructions") or "") + (
        f"\n\nThrough PiCode: the app runs on the human's desktop and they watch it. The first call opens it "
        f"(app_open does so explicitly); {paths_note}. app_open and app_status return the app's `window`: if you "
        f"have PiCode's computer tool, take one screenshot of that window right away so the human's Agent "
        f"screen panel follows the app.")

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
                    tool_name, base = OPEN_TOOL[name]
                    call = dict(base)
                    if tool_name == "command_run":
                        call["params"] = {"path": app.path_arg(args["file"])}
                    else:
                        call["path"] = app.path_arg(args["file"])
                    res = bridge.call(tool_name, call)
                    if "error" in res or (res.get("result") or {}).get("isError"):
                        return res.get("result") or text_result(res.get("error"), True)
                    out["file"] = res["result"].get("content")
                out.update(app.window_hint())
                return text_result(out)
            if tool == "app_path":
                return text_result({"path": app.path_arg(args.get("path", ""))})
            if tool not in known:
                return text_result(f"unknown tool {tool}", True)
            for key in PATH_KEYS[name].get(tool, []):
                if key in args:
                    args[key] = app.path_arg(args[key])
            args = app.translate_abs(args, keys=FILE_KEYS | ({"text"} if (name, tool) in TEXT_PATHS else set()))
            app.ensure_open()
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
