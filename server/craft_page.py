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

import json
import concurrent.futures
import os
import ssl
import sys
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import craft_mcp as cm  # noqa: E402

SECRET = os.environ.get("PICODE_EXT_PROXY_SECRET", "")
PORT = int(os.environ.get("PICODE_EXT_PORT", "0"))
SNAP_SIDE = cm.SNAP_SIDE  # keeps a picture well under PiCode's 1 MiB relay

# What each app is, in the page's words, and which files it opens.
KINDS = {name: (spec["kind"], tuple(spec["extensions"])) for name, spec in cm.APPS.items()}


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


def app_row(meta):
    row = dict(meta)
    app = cm.App(meta["app"])
    try:
        st = app.status()
        row.update(installed=st["installed"], open=st["open_with_control"],
                   window=st.get("window"), folder=st.get("folder"),
                   openedForRoot=app.read_state().get("root"))
        if not st["installed"]:
            row["state"] = "not-installed"
        elif st.get("connection") == "unavailable":
            row["state"] = "connection-error"
            row["message"] = st.get("hint", "The app connection is unavailable.")
        elif st["open_with_control"]:
            row["state"] = "connected"
        elif st.get("running_without_control"):
            row["state"] = "uncontrolled"
        else:
            row["state"] = "ready"
        app.install() if st["installed"] else None
    except (cm.ToolError, OSError, ValueError, RuntimeError) as e:
        row["state"] = "error"
        row["message"] = str(e) if isinstance(e, cm.ToolError) else "Could not check this app. Try Refresh."
    return row


def status():
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        return {"apps": list(pool.map(app_row, cm.public_catalog()))}


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


def open_file(path, ws_id, name=None):
    choices = cm.candidates(path)
    if name and name not in choices:
        raise PageError("This app does not open this kind of file.")
    if not name and len(choices) > 1:
        raise PageError("Choose an app to open this file.")
    name = name or (choices[0] if choices else None)
    if not name:
        raise PageError("None of the Crafting Apps opens this kind of file.")
    app = app_in(name, ws_id)
    path = os.path.realpath(path if os.path.isabs(path) else os.path.join(app.root, path))
    if os.path.commonpath([path, app.root]) != app.root:
        raise PageError("Choose a file in this workspace.")
    if not os.path.isfile(path):
        raise PageError("That file is not there any more.")
    try:
        with cm.app_lock(name), cm.Bridge(app) as bridge:
            app.ensure_open()
            cm.open_file_in(app, name, path, bridge)
    except cm.ToolError as e:
        raise PageError(str(e))
    return {"message": "Opened %s in %s." % (os.path.basename(path), cm.APPS[name]["title"])}


# The snapshot each app takes of its own window without bringing it forward.
SNAP = {
    "photocraft": ("control_call", {"method": "ui.screenshot", "params": {"focus": False}}),
    "vectorcraft": ("screenshot", {"window": True}),
    "effectcraft": ("screenshot", {"max_side": SNAP_SIDE}),
    "filmcraft": ("ui_screenshot", {"max_side": SNAP_SIDE}),
    "lightcraft": ("screenshot", {"maxSize": SNAP_SIDE}),
    # Its window screenshot raises the window (measured), so the page shows the
    # document's current page, rendered headless, instead.
    "designcraft": ("render_page", {"scale": 0.8}),
    "wordcraft": ("render_page", {"page": 1, "scale": 0.8}),
    "deckcraft": ("render_slide", {"scale": 0.8}),
    "gridcraft": ("screenshot", {}),
    "printcraft": None,  # its window goes through the control file, not an MCP bridge
}


shrink = cm.shrink


# A picture larger than this is not sent: base64 of it would not fit the relay.
MAX_PNG = 700 * 1024


def snapshot(name):
    if name not in cm.APPS:
        raise PageError("No such app.")
    app = cm.App(name)
    if not app.listening_pid():
        raise PageError("%s is not open." % cm.APPS[name]["title"])
    try:
        app.verify_connection()
    except cm.ToolError as e:
        raise PageError(str(e))
    if name == "printcraft":
        try:
            b64 = cm.printcraft_screenshot(app)
        except cm.ToolError as e:
            raise PageError(str(e))
        return {"image": b64, "mime": "image/png"}
    if name == "gridcraft":
        # This release's window capture can stall while the app is unfocused.
        # A small, live cell preview is read-only and does not change focus.
        try:
            with cm.Bridge(app) as bridge:
                res = bridge.call("read_range", {"range": "A1:H12", "formatted": True}, timeout=10)
            if "error" in res or res.get("result", {}).get("isError"):
                raise cm.ToolError("Could not read spreadsheet cells.")
            value = cm.content_value(res.get("result"))
            return {"table": value, "caption": "Live cells · A1:H12"}
        except cm.ToolError as e:
            raise PageError(str(e))
    tool, args = SNAP[name]
    b64 = take(app, tool, args)
    caption = "Rendered document page" if name in {"designcraft", "wordcraft"} else "Rendered slide" if name == "deckcraft" else "Window snapshot"
    b64, size = shrink(b64)
    if size > MAX_PNG and name == "vectorcraft":
        # No ffmpeg to shrink the window: show the artwork itself, smaller.
        b64, size = shrink(take(app, "screenshot", {"scale": 0.5}))
    if size > MAX_PNG:
        raise PageError("The picture of %s's window is too large to show; install ffmpeg to shrink it." % cm.APPS[name]["title"])
    return {"image": b64, "mime": "image/png", "caption": caption}


def take(app, tool, args):
    try:
        with cm.Bridge(app) as bridge:
            res = bridge.call(tool, args)
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
            print("request %s failed: %r" % (self.path, e), file=sys.stderr, flush=True)
            return self.reply(500, {"message": "Something went wrong. Try Refresh; if it keeps happening, restart "
                                               "the extension from its page in Extensions."})

    def do_GET(self):
        if not self.allowed():
            return
        if self.path == "/catalog":
            return self.reply(200, {"apps": cm.public_catalog()})
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
            return self.run(lambda: open_file(req.get("path") or ctx.get("path", ""), ws, req.get("app")))
        if self.path == "/snapshot":
            return self.run(lambda: snapshot(req.get("app", "")))
        self.reply(404, {"message": "no such route"})

    def log_message(self, *args):
        pass


if __name__ == "__main__":
    print("picode-artcraft page server on 127.0.0.1:%d" % PORT, flush=True)
    ThreadingHTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
