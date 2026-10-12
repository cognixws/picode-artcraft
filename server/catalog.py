"""The release-pinned app catalog shared by the MCP bridge and the page."""
import json
from pathlib import Path

APPS = json.loads(Path(__file__).with_name("catalog.json").read_text())


def public_catalog():
    keys = ("title", "kind", "category", "purpose", "icon", "extensions", "version")
    return [{"app": name, **{key: spec[key] for key in keys},
             "download": f"https://github.com/storytold/{name}/releases"}
            for name, spec in APPS.items()]


def candidates(path):
    low = (path or "").lower()
    return [name for name, spec in APPS.items() if low.endswith(tuple(spec["extensions"]))]
