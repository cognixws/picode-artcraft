# picode-artcraft

A [PiCode](https://cognix.ws) extension that lets your agents
work in the ArtCraft team's open-source **Crafting Apps** —
[PhotoCraft](https://github.com/storytold/photocraft) (images, Photoshop-style),
[VectorCraft](https://github.com/storytold/vectorcraft) (vector art,
Illustrator-style), [EffectCraft](https://github.com/storytold/effectcraft)
(motion graphics, After Effects-style) and
[FilmCraft](https://github.com/storytold/filmcraft) (video editing,
Premiere-style), [LightCraft](https://github.com/storytold/lightcraft)
(photo development, Lightroom-style), [DesignCraft](https://github.com/storytold/designcraft)
(page layout, InDesign-style) and [PrintCraft](https://github.com/storytold/printcraft)
(PDFs, Acrobat-style). The agent works in the real app window while you watch, and
saves into the workspace.

> v0.5 — seven apps and a page. Plan and next steps in [docs/plan.md](docs/plan.md).

## How it works

Both apps are built for agents: every menu item, tool and dialog is a command,
and each ships its own MCP server (`photocraft-cli mcp`, `vectorcraft-cli mcp`)
that can drive a running window over a loopback control channel. This
extension adds what PiCode needs around them:

- **One MCP server per app** (`photocraft`, `vectorcraft`, `effectcraft`,
  `filmcraft`, `lightcraft`, `designcraft`, `printcraft`) with the app's own
  tools plus `app_status`, `app_open` and `app_path`. LightCraft's 359 `cmd_*`
  shortcut tools (each is `run_command` with a fixed id) are not listed, to
  keep the agent's tool list small; calling one by name still works.
- **PrintCraft is different**: its MCP server edits PDFs without a window, only
  inside the workspace folder; the extension adds `ui_*` tools that drive the
  real window (open a PDF, inspect, click, key, screenshot) so the human sees the
  result. The window is opened with a control file that holds a random loopback
  port and token, in `%LOCALAPPDATA%\picode-artcraft`. The first call opens the app on your
  desktop with its control channel on; every call is then forwarded to the
  app's own MCP server, bridged to that window.
- **Paths**: PhotoCraft is opened with the workspace as its only file root
  (it refuses anything outside it); VectorCraft gets paths translated to what
  its OS sees; the others get absolute paths in path-like arguments
  translated, and `app_path` converts a workspace path for command params.
- **The Agent screen**: the extension holds `screen:follow` ("Point your
  agent's screen at the app it drives") and points the panel beside the agent
  at the app's window itself, on `app_open` and on the first tool that opens
  the app — no Computer tool needed. On a PiCode without that door it falls
  back: `app_open` returns the window and the skills tell an agent with the
  `computer` tool to take one screenshot of it.
- **One skill per app** with the working loop, and the app's own agent and
  control-protocol docs plus a command index as references.
- **A page** (Apps → Crafting Apps, or *Open Crafting Apps* in the workspace
  menu): which apps are installed and open, an **Open** button, and a
  **Snapshot** of an app's window taken without bringing it to the front
  (DesignCraft shows its current page instead: its window screenshot raises the
  window). **Open with** on `.pcraft`, `.psd`, `.vectorcraft`, `.svg`, `.ecproj`,
  `.fcproj`, `.designcraft` and `.pdf` files opens the file in its app. A small background program
  (`server/craft_page.py`, standard library only) answers the page; it uses
  `workspaces:read` to find the workspace's folder, PhotoCraft's files root.
- **Turns itself on** in a workspace with a `.pcraft`, `.vectorcraft`,
  `.ecproj` or `.fcproj` file.

On Windows with PiCode inside WSL, the Windows builds run through WSL
interop: the app's CLI reaches the app on Windows' own loopback, so no
mirrored networking is needed.

## Install

1. Install the apps. On Windows the portable zips are enough
   (`<app>-<v>-windows-x64-portable.zip` from each repository's releases),
   unzipped to `<drive>:\Apps\PhotoCraft`, `VectorCraft`, `EffectCraft`,
   `FilmCraft`, `LightCraft`, `DesignCraft`, `PrintCraft`. Other places: `Program Files`, `AppData\Local\Programs`, or
   set `PICODE_<APP>_DIR` (e.g. `PICODE_FILMCRAFT_DIR`) to the folder holding
   the app and its `-cli`. `PICODE_<APP>_PORT` moves an app off its default
   control port (PhotoCraft 7878, VectorCraft 7979, FilmCraft 9876,
   EffectCraft 9877, LightCraft 7980, DesignCraft 7981 — not its own default
   7979, which is VectorCraft's; PrintCraft uses a control file, not a port).
2. In PiCode: **Extensions → Install extension**, paste
   `https://github.com/cognixws/picode-artcraft`, review, **Install**, then
   turn it on in the workspaces where you want it.

## Security

- PhotoCraft's control channel needs a 256-bit token. PhotoCraft creates it
  on first launch in `%LOCALAPPDATA%\picode-artcraft\` (Windows) or
  `~/.picode-artcraft/` (Linux); it never goes into a command line or a log.
- **VectorCraft's, EffectCraft's, FilmCraft's, LightCraft's and DesignCraft's
  control channels have no token**: while one runs with `--control`, any program
  on this machine can drive it over loopback. The extension only opens an app with control when
  an agent first uses it. Close the app when you are done if that matters on
  your machine.

## Requirements

- PiCode with extensions (ADR-0230). v0.3 declares `screen:follow`, which
  needs a PiCode with the screen-follow door (ADR-0230 amendment of
  2026-10-06); an older PiCode refuses the install — use v0.2.1 there.
- Any of PhotoCraft 0.2, VectorCraft 0.3, EffectCraft 0.3, FilmCraft 0.2,
  LightCraft 0.2, DesignCraft 0.2, PrintCraft 0.2 (tested on Windows 11:
  0.2.0, 0.3.1, 0.3.1, 0.2.1, 0.2.1, 0.2.1, 0.2.1).
- Python 3.10+ on the machine running PiCode. `ffmpeg` (optional) shrinks a
  large window snapshot for the page.

## License

Apache-2.0. The vendored documentation of the apps under
`skills/*/references/` is MIT OR Apache-2.0 from its authors; see
[third_party/README.md](third_party/README.md). Not affiliated with
ArtCraft or Storyteller.
