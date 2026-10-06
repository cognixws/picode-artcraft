# picode-artcraft

A [PiCode](https://cognix.ws) extension that lets your agents
work in the ArtCraft team's open-source **Crafting Apps** —
[PhotoCraft](https://github.com/storytold/photocraft) (images, Photoshop-style),
[VectorCraft](https://github.com/storytold/vectorcraft) (vector art,
Illustrator-style), [EffectCraft](https://github.com/storytold/effectcraft)
(motion graphics, After Effects-style) and
[FilmCraft](https://github.com/storytold/filmcraft) (video editing,
Premiere-style). The agent works in the real app window while you watch, and
saves into the workspace.

> v0.2 — four apps. Plan and next apps in [docs/plan.md](docs/plan.md).

## How it works

Both apps are built for agents: every menu item, tool and dialog is a command,
and each ships its own MCP server (`photocraft-cli mcp`, `vectorcraft-cli mcp`)
that can drive a running window over a loopback control channel. This
extension adds what PiCode needs around them:

- **One MCP server per app** (`photocraft`, `vectorcraft`, `effectcraft`,
  `filmcraft`) with the app's own tools plus `app_status`, `app_open` and
  `app_path`. The first call opens the app on your
  desktop with its control channel on; every call is then forwarded to the
  app's own MCP server, bridged to that window.
- **Paths**: PhotoCraft is opened with the workspace as its only file root
  (it refuses anything outside it); VectorCraft gets paths translated to what
  its OS sees; the others get absolute paths in path-like arguments
  translated, and `app_path` converts a workspace path for command params.
- **The Agent screen**: `app_open` and `app_status` return the app's window,
  and the skills tell an agent with PiCode's `computer` tool to take one
  screenshot of it, so the panel beside the agent follows the app.
- **One skill per app** with the working loop, and the app's own agent and
  control-protocol docs plus a command index as references.
- **Turns itself on** in a workspace with a `.pcraft`, `.vectorcraft`,
  `.ecproj` or `.fcproj` file.

On Windows with PiCode inside WSL, the Windows builds run through WSL
interop: the app's CLI reaches the app on Windows' own loopback, so no
mirrored networking is needed.

## Install

1. Install the apps. On Windows the portable zips are enough
   (`<app>-<v>-windows-x64-portable.zip` from each repository's releases),
   unzipped to `<drive>:\Apps\PhotoCraft`, `VectorCraft`, `EffectCraft`,
   `FilmCraft`. Other places: `Program Files`, `AppData\Local\Programs`, or
   set `PICODE_<APP>_DIR` (e.g. `PICODE_FILMCRAFT_DIR`) to the folder holding
   the app and its `-cli`. `PICODE_<APP>_PORT` moves an app off its default
   control port (PhotoCraft 7878, VectorCraft 7979, FilmCraft 9876,
   EffectCraft 9877).
2. In PiCode: **Extensions → Install extension**, paste
   `https://github.com/cognixws/picode-artcraft`, review, **Install**, then
   turn it on in the workspaces where you want it.

## Security

- PhotoCraft's control channel needs a 256-bit token. PhotoCraft creates it
  on first launch in `%LOCALAPPDATA%\picode-artcraft\` (Windows) or
  `~/.picode-artcraft/` (Linux); it never goes into a command line or a log.
- **VectorCraft's, EffectCraft's and FilmCraft's control channels have no
  token**: while one runs with `--control`, any program on this machine can
  drive it over loopback. The extension only opens an app with control when
  an agent first uses it. Close the app when you are done if that matters on
  your machine.

## Requirements

- PiCode with extensions (ADR-0230).
- Any of PhotoCraft 0.2, VectorCraft 0.3, EffectCraft 0.3, FilmCraft 0.2
  (tested on Windows 11: 0.2.0, 0.3.1, 0.3.1, 0.2.1).
- Python 3.10+ on the machine running PiCode.

## License

Apache-2.0. The vendored documentation of the apps under
`skills/*/references/` is MIT OR Apache-2.0 from its authors; see
[third_party/README.md](third_party/README.md). Not affiliated with
ArtCraft or Storyteller.
