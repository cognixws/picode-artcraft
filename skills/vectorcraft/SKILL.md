---
name: vectorcraft
description: Draw and edit vector art in VectorCraft (an open-source Illustrator-style app) through the vectorcraft MCP tools — shapes, paths, paint, type, effects, Pathfinder and transforms in the app the human is watching, then look at it and export SVG, PDF, PNG and more into the workspace.
---

# Drawing in VectorCraft through the tools

VectorCraft runs on the human's desktop and they watch the art appear. Every
menu action is a command; the dedicated tools cover drawing and looking.

## Loop

1. `app_open` (optionally with `file`) to start where the human can watch;
   any other tool also opens the app on first use. The extension points
   the human's Agent screen at the app itself (`screen: following this
   window`). Only when it answers `screen: not followed` and you have
   PiCode's `computer` tool, call it once with `action: screenshot,
   window: <the returned window>` so the panel follows the app.
2. `run_command {command: "file.new"}` for a new document, or `open_file`.
   `inspect_ui` lists what is open — never close or overwrite the human's own
   documents.
3. Draw: `draw_shape` (`rectangle`/`ellipse`: `x, y, width, height`;
   `polygon`: `cx, cy, radius, sides`; `star`: `cx, cy, radius1, radius2,
   points`; `line`: `x1, y1, x2, y2`), `draw_path` (`points` or SVG `d`),
   `add_text`. Paint with `fill`, `stroke`, `strokeWidth` on the call or
   `set_paint` afterwards.
4. Shape it: `pathfinder`, `transform`, `apply_effect`, `create_graph`,
   `text_wrap`; anything else through `list_commands {filter}` and
   `run_command {command, params}`. `references/commands.tsv` is the whole
   index for 0.3.1 to grep offline.
5. Look: `screenshot` (the artboard, or `window: true` for the app window)
   and `inspect_document` (artboards, layer tree with ids and bounds,
   selection). Fix what reads wrong before saying it is done.
6. `export {path}` by extension (`svg`, `pdf`, `png`, `jpg`, `webp`, `eps`,
   `dxf`, `psd`…) and `save_file {path}` for the native `.vectorcraft`.

## Coordinates and paint

Points in document space: y points down, the origin is the first artboard's
top-left, a new document is 612 × 792 (US Letter). New objects become the
selection and most commands act on the selection or on explicit `ids`.
Paint: `"#rrggbb"`, `"none"`, `[r,g,b]` (0–1), `{c,m,y,k}`, `{gray}`, or a
`{gradient: …}` / `{swatch: name}` object.

## Paths

Absolute paths or paths relative to the workspace; PiCode turns them into
the path Windows sees. `save_file` may answer `background: true` — the file
is written a moment later.

## Recipes (found in a real run)

- Delete objects: `run_command edit.clear {ids:[...]}`.
- Opacity and blend: `run_command transparency.set {ids, opacity: 0-100,
  blend: "Multiply"}` — soft shadows (sfumato) are dark shapes at 20–35 %
  Multiply with `apply_effect blur.gaussian {ids, params:{radius: 8}}`.
- Gradients on any fill: `{"gradient": {"kind": "linear"|"radial", "start":
  [x,y], "end": [x,y], "stops": [{"offset", "color", "opacity"?}]}}`.
- Later objects draw on top: plan the order back to front (background,
  figure, face, features, glaze).
- `draw_path {d}` with SVG path data is the fastest way to place a complex
  shape in one call.

## Dialogs

Give a command its params and it runs without a dialog; with no params some
commands open one in the app and answer `{"pending": "<dialog>"}`. The
`ui.dialog.*` methods of the control protocol are not commands, so
`run_command` cannot fill a dialog: run the command again with params, and
close a dialog you opened with `press_key {key: "Escape"}` (check with
`inspect_ui`). Closing a modified document asks to save first: do not discard
the human's work.

## References

- `references/mcp.md`: VectorCraft's own MCP guide (every tool, worked
  examples, masks, gradients, styles, export options), and
  `references/control-protocol.md` — v0.3.1, MIT/Apache-2.0, vendored
  unchanged.
- `references/commands.tsv`: id, label, menu and shortcut of every command
  (`Cmd` in a shortcut is `Ctrl` on Windows).
