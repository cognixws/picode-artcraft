# picode-artcraft

A [PiCode](https://cognix.ws) extension that lets your agents
work in the ArtCraft team's open-source **Crafting Apps** —
[PhotoCraft](https://github.com/storytold/photocraft) (images, Photoshop-style)
and [VectorCraft](https://github.com/storytold/vectorcraft) (vector art,
Illustrator-style). The agent edits in the real app window while you watch,
and saves into the workspace.

> v0.1 — PhotoCraft and VectorCraft. Plan and next apps in [docs/plan.md](docs/plan.md).

## How it works

Both apps are built for agents: every menu item, tool and dialog is a command,
and each ships its own MCP server (`photocraft-cli mcp`, `vectorcraft-cli mcp`)
that can drive a running window over a loopback control channel. This
extension adds what PiCode needs around them:

- **Two MCP servers** (`photocraft`, `vectorcraft`) with the apps' own tools
  plus `app_status` and `app_open`. The first call opens the app on your
  desktop with its control channel on; every call is then forwarded to the
  app's own MCP server, bridged to that window.
- **Paths**: PhotoCraft is opened with the workspace as its only file root
  (it refuses anything outside it); VectorCraft gets paths translated to what
  its OS sees.
- **Two skills** (`photocraft`, `vectorcraft`) with the working loop, and the
  apps' own MCP and control-protocol docs plus a command index as references.
- **Turns itself on** in a workspace with a `.pcraft` or `.vectorcraft` file.

On Windows with PiCode inside WSL, the Windows builds run through WSL
interop: the app's CLI reaches the app on Windows' own loopback, so no
mirrored networking is needed.

## Install

1. Install the apps. On Windows the portable zips are enough
   (`photocraft-<v>-windows-x64-portable.zip`,
   `vectorcraft-<v>-windows-x64-portable.zip` from each repository's
   releases), unzipped to `<drive>:\Apps\PhotoCraft` and
   `<drive>:\Apps\VectorCraft`. Other places: `Program Files`,
   `AppData\Local\Programs`, or set `PICODE_PHOTOCRAFT_DIR` /
   `PICODE_VECTORCRAFT_DIR` to the folder holding the app and its `-cli`.
2. In PiCode: **Extensions → Install extension**, paste
   `https://github.com/cognixws/picode-artcraft`, review, **Install**, then
   turn it on in the workspaces where you want it.

## Security

- PhotoCraft's control channel needs a 256-bit token. PhotoCraft creates it
  on first launch in `%LOCALAPPDATA%\picode-artcraft\` (Windows) or
  `~/.picode-artcraft/` (Linux); it never goes into a command line or a log.
- **VectorCraft's control channel has no token**: while VectorCraft runs with
  `--control`, any program on this machine can drive it over loopback. The
  extension only opens it with control when an agent first uses it. Close
  VectorCraft when you are done if that matters on your machine.

## Requirements

- PiCode with extensions (ADR-0230).
- PhotoCraft 0.2 and/or VectorCraft 0.3 (tested: 0.2.0 and 0.3.1 on Windows 11).
- Python 3.10+ on the machine running PiCode.

## License

Apache-2.0. The vendored PhotoCraft and VectorCraft documentation under
`skills/*/references/` is MIT OR Apache-2.0 from its authors; see
[third_party/README.md](third_party/README.md). Not affiliated with
ArtCraft or Storyteller.
