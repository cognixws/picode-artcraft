#!/usr/bin/env python3
"""picode-artcraft's background program (PiCode ADR-0230: process, pages).

PiCode starts it while the extension is on in a workspace and is the only
caller: every request carries X-PiCode-Proxy-Secret, the value PiCode gave
this process in PICODE_EXT_PROXY_SECRET. It reuses craft_mcp's App and
Bridge, so it opens and talks to the apps exactly as the agents' MCP
servers do (same ports, token file and files root).

    GET  /status             every app: installed, open, its window
    GET  /workspaces         the workspaces the extension is on in
    POST /open {app, workspace}            open an app with control on
    POST /open-file {path, workspace}      open a file in the app it belongs to
    POST /snapshot {app}                   a picture of the app's window
"""

import base64
import json
import os
import shutil
import ssl
import struct
import subprocess
import sys
import tempfile
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import craft_mcp as cm  # noqa: E402

SECRET = os.environ.get("PICODE_EXT_PROXY_SECRET", "")
PORT = int(os.environ.get("PICODE_EXT_PORT", "0"))
SNAP_SIDE = 900  # keeps a picture well under PiCode's 1 MiB relay

# What each app is, in the page's words, and which files it opens.
KINDS = {
    "photocraft": ("Images", (".pcraft", ".psd", ".psb", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp")),
    "vectorcraft": ("Vector art", (".vectorcraft", ".svg", ".svgz", ".ai", ".eps", ".pdf")),
    "effectcraft": ("Motion", (".ecproj",)),
    "filmcraft": ("Video", (".fcproj",)),
}


class PageError(Exception):
    pass


def app_for(path):
    low = (path or "").lower()
    for name, (_, exts) in KINDS.items():
        if low.endswith(exts):
            return name
    return None


def host(path):
    """GET a Host API route with the extension's own token."""
    url, token = os.environ.get("PICODE_URL", ""), os.environ.get("PICODE_EXT_TOKEN", "")
    if not url or not token:
        raise PageError("PiCode did not give this program its address; restart the extension.")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False  # PiCode's own loopback certificate
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url + path, headers={"X-PiCode-Extension-Token": token})
    with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
        return json.load(r)


def workspaces():
    rows = host("/api/ext/v1/workspaces")
    rows = rows.get("workspaces", rows) if isinstance(rows, dict) else rows
    return [{"id": w["id"], "name": w.get("name") or w["id"], "path": w.get("path", "")}
            for w in rows if w.get("extensionOn")]


def workspace_path(ws_id):
    for w in workspaces():
        if w["id"] == ws_id:
            if not w["path"]:
                raise PageError("This workspace has no folder.")
            return w["path"]
    raise PageError("Turn Crafting Apps on in this workspace first.")


def listeners():
    """{port: window handle} for every app's control port, in one PowerShell call."""
    ports = [s["port"] for s in cm.APPS.values()]
    if not cm.WSL:
        return {}
    script = (
        "$out=@{}; foreach($p in @(%s)){ $c = Get-NetTCPConnection -LocalPort $p -State Listen "
        "-ErrorAction SilentlyContinue | Select-Object -First 1; if($c){ $out[\"$p\"] = "
        "(Get-Process -Id $c.OwningProcess).MainWindowHandle } }; $out | ConvertTo-Json -Compress"
    ) % ",".join(str(p) for p in ports)
    raw = cm.powershell(script)
    try:
        return {int(k): int(v) for k, v in json.loads(raw or "{}").items()}
    except (ValueError, TypeError):
        return {}


def status():
    open_ports = listeners()
    apps = []
    for name, spec in cm.APPS.items():
        found = cm.find_install(name)
        row = {"app": name, "title": spec["title"], "kind": KINDS[name][0], "installed": bool(found)}
        if found:
            row["folder"] = cm.to_app_path(found[0])
            window = open_ports.get(spec["port"])
            row["open"] = window is not None
            if window:
                row["window"] = window
            if spec["roots"] and window:
                row["filesRoot"] = cm.App(name).read_state().get("root")
        apps.append(row)
    return {"apps": apps}


def app_in(name, ws_id):
    """The app, rooted at the workspace's folder (PhotoCraft reads and writes only there)."""
    if name not in cm.APPS:
        raise PageError("No such app.")
    app = cm.App(name)
    app.root = os.path.realpath(workspace_path(ws_id))
    return app


def open_app(name, ws_id):
    app = app_in(name, ws_id)
    try:
        launched = app.ensure_open()
    except cm.ToolError as e:
        raise PageError(str(e))
    title = cm.APPS[name]["title"]
    return {"opened": launched, "message": ("Opened %s." if launched else "%s is already open.") % title}


def open_file(path, ws_id):
    name = app_for(path)
    if not name:
        raise PageError("None of the Crafting Apps opens this kind of file.")
    if not os.path.isfile(path):
        raise PageError("That file is not there any more.")
    app = app_in(name, ws_id)
    try:
        app.ensure_open()
        tool, base = cm.OPEN_TOOL[name]
        call = dict(base)
        if tool == "command_run":
            call["params"] = {"path": app.path_arg(path)}
        else:
            call["path"] = app.path_arg(path)
        res = cm.Bridge(app).call(tool, call)
    except cm.ToolError as e:
        raise PageError(str(e))
    result = res.get("result") or {}
    if "error" in res or result.get("isError"):
        msg = cm.content_value(result) or (res.get("error") or {}).get("message") or "the app refused the file"
        raise PageError(str(msg))
    return {"message": "Opened %s in %s." % (os.path.basename(path), cm.APPS[name]["title"])}


# The snapshot each app takes of its own window without bringing it forward.
SNAP = {
    "photocraft": ("control_call", {"method": "ui.screenshot", "params": {"focus": False}}),
    "vectorcraft": ("screenshot", {"window": True}),
    "effectcraft": ("screenshot", {"max_side": SNAP_SIDE}),
    "filmcraft": ("ui_screenshot", {"max_side": SNAP_SIDE}),
}


def png_width(raw):
    return struct.unpack(">I", raw[16:20])[0] if raw[:8] == b"\x89PNG\r\n\x1a\n" else 0


def shrink(b64):
    """Scale a large PNG down to SNAP_SIDE wide with ffmpeg, when it is installed.

    A window capture at full resolution can exceed PiCode's 1 MiB relay."""
    raw = base64.b64decode(b64)
    if png_width(raw) <= SNAP_SIDE * 1.2 or not shutil.which("ffmpeg"):
        return b64, len(raw)
    with tempfile.TemporaryDirectory() as d:
        src, dst = os.path.join(d, "in.png"), os.path.join(d, "out.png")
        with open(src, "wb") as f:
            f.write(raw)
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-vf", "scale=%d:-1" % SNAP_SIDE, dst],
                           capture_output=True, timeout=30)
        if r.returncode != 0 or not os.path.exists(dst):
            return b64, len(raw)
        with open(dst, "rb") as f:
            small = f.read()
    return base64.b64encode(small).decode(), len(small)


# A picture larger than this is not sent: base64 of it would not fit the relay.
MAX_PNG = 700 * 1024


def snapshot(name):
    if name not in cm.APPS:
        raise PageError("No such app.")
    app = cm.App(name)
    if not app.listening_pid():
        raise PageError("%s is not open." % cm.APPS[name]["title"])
    tool, args = SNAP[name]
    b64 = take(app, tool, args)
    b64, size = shrink(b64)
    if size > MAX_PNG and name == "vectorcraft":
        # No ffmpeg to shrink the window: show the artwork itself, smaller.
        b64, size = shrink(take(app, "screenshot", {"scale": 0.5}))
    if size > MAX_PNG:
        raise PageError("The picture of %s's window is too large to show; install ffmpeg to shrink it." % cm.APPS[name]["title"])
    return {"image": b64, "mime": "image/png"}


def take(app, tool, args):
    try:
        res = cm.Bridge(app).call(tool, args)
    except cm.ToolError as e:
        raise PageError(str(e))
    result = res.get("result") or {}
    for c in result.get("content", []):
        if c.get("type") == "image" and c.get("data"):
            return c["data"]
    value = cm.content_value(result)  # PhotoCraft's control call answers {base64: ...}
    if isinstance(value, dict):
        for key in ("base64", "data", "image", "png"):
            if isinstance(value.get(key), str):
                return value[key]
    raise PageError(str(value or "%s gave no picture of its window." % app.spec["title"])[:300])


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, body):
        data = json.dumps(body).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def allowed(self):
        if SECRET and self.headers.get("X-PiCode-Proxy-Secret") == SECRET:
            return True
        self.reply(403, {"message": "only PiCode may call this program"})
        return False

    def body(self):
        n = int(self.headers.get("Content-Length") or 0)
        try:
            return json.loads(self.rfile.read(n) or b"{}")
        except ValueError:
            return {}

    def run(self, fn):
        try:
            return self.reply(200, fn())
        except PageError as e:
            return self.reply(409, {"message": str(e)})
        except Exception as e:  # noqa: BLE001 — answer, never crash
            return self.reply(500, {"message": "%s: %s" % (type(e).__name__, e)})

    def do_GET(self):
        if not self.allowed():
            return
        if self.path == "/status":
            return self.run(status)
        if self.path == "/workspaces":
            return self.run(lambda: {"workspaces": workspaces()})
        self.reply(404, {"message": "no such route"})

    def do_POST(self):
        if not self.allowed():
            return
        req = self.body()
        ctx = req.get("context") or {}
        ws = req.get("workspace") or ctx.get("workspaceId") or ""
        if self.path == "/open":
            return self.run(lambda: open_app(req.get("app", ""), ws))
        if self.path == "/open-file":
            return self.run(lambda: open_file(req.get("path") or ctx.get("path", ""), ws))
        if self.path == "/snapshot":
            return self.run(lambda: snapshot(req.get("app", "")))
        self.reply(404, {"message": "no such route"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("picode-artcraft page server on 127.0.0.1:%d" % PORT, flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
