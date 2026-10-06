# Plan

## Why this shape

The owner wanted agents to use the ArtCraft team's apps "like a human",
watching them work. The first look went to the ArtCraft AI studio itself,
which only routes generations to cloud providers, has no local API, and is
under a "fair source" license that forbids competing products. The Crafting
Apps are different: native Rust editors (MIT OR Apache-2.0) whose every
action is a command, each with an MCP server that bridges to the running
window. Driving them by pixels through PiCode's computer tool would be worse
than their own channel (their egui UI does not expose an accessibility tree
the way a web view does), so the extension wires their MCP servers in
instead.

There are no official agent skills upstream (no `SKILL.md` in any storytold
repository on 2026-10-06), so the skills here are ours and the official docs
are vendored as their references.

## v0.1 (this release)

- `server/craft_mcp.py <app>`: lists the vendored tools + `app_status`,
  `app_open`; opens the app with `--control` on first use (PhotoCraft also
  with a token file and the workspace as read/write root); starts the app's
  CLI in bridge mode and forwards calls; translates paths.
- Skills `photocraft` and `vectorcraft`.
- Verified live on Windows 11 + WSL (2026-10-06): PhotoCraft `doc_new`,
  `edit.fill`, `doc_save` into the workspace (pixel checked), refusal of a
  path outside it; VectorCraft `file.new`, `draw_shape` star, `export` to
  SVG and PNG and `save_file` into the workspace.

## v0.1.1

- PiCode's Agent screen panel follows the window an agent last used through
  the `computer` tool. The apps are driven over their own channel, so the
  panel stayed empty on the first live run (2026-10-06). `app_open` and
  `app_status` now return the app's `window` (its Windows handle, the id the
  computer tool uses) and the skills tell the agent to take one screenshot
  of it. Agents without the computer tool still work; the panel just does
  not follow. A direct "follow this window" door for extensions would be an
  ADR-0230 amendment in PiCode.

## v0.2.0

- EffectCraft 0.3.1 and FilmCraft 0.2.1: their MCP servers (bridge to
  `--control 9877` / `9876`, no token), skills and vendored `agents.md` /
  `control-protocol.md`.
- `app_path` converts a workspace path for command params; absolute POSIX
  paths in path-like keys (`path`, `paths`, `file`, `out`…) are translated on
  their own for apps without a files root. Relative values are left alone:
  in EffectCraft `path` is also a property path (`transform/position`).
  FilmCraft's `media_import` takes paths one per line in `text`.
- `PICODE_<APP>_PORT` overrides a control port. Verified live (2026-10-06):
  FilmCraft `media_import` of a workspace PNG; EffectCraft `comp.new`,
  `save_project` and `render_frame` into the workspace.

## v0.2.1

- `app_open {file}` returns the opened file as an object, not as nested MCP
  content.
- An app the human opened by hand (no control channel) is reported by
  `app_status` (`running_without_control`) and refused by the other tools with
  a request to close it, instead of a second copy being opened.
- `app_open` resizes EffectCraft's window when it reports less than
  1000 × 600 (it sometimes comes back tiny).
- Skills: the pitfalls and recipes from the recorded run.
- Verified live, recorded (2026-10-06): one agent drew a Mona Lisa in
  VectorCraft (about 40 calls), aged it in PhotoCraft (texturizer, craquelure,
  grain, sepia, curves), animated it in EffectCraft (keyframes, titles,
  H.264 render) and cut a 20 s film in FilmCraft (three clips, labels,
  dissolves, H.264 export), with the Agent screen following each app.

## Next

- The other apps as they mature: LightCraft, PrintCraft, DesignCraft (same
  shape: one server per app). DesignCraft's default control port is 7979,
  VectorCraft's too — give it another default when it joins.
- A page (Apps → Crafting Apps) showing which apps are installed and open,
  with a window snapshot, and *Open with* for `.pcraft`, `.psd`,
  `.vectorcraft`, `.svg`.
- Headless mode for batch work nobody needs to watch (`--headless` /
  `photocraft-cli serve`).
- A tool list refreshed from the installed app at start instead of the
  vendored snapshot, when the installed version differs.

## Updating

When an app releases a new version: capture its `tools/list` in bridge mode
into `server/tools/<app>.json`, regenerate `references/commands.tsv`, vendor
the docs at the release tag, and update the versions in `third_party/README.md`.
