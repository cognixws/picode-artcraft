---
name: lightcraft
description: Develop and organize photos in LightCraft (an open-source Lightroom-style raw developer and photo library) through the lightcraft MCP tools — query the library, adjust exposure, tone and colour non-destructively, apply presets, crop, look at the render and export, in the app the human is watching.
---

# Developing photos in LightCraft through the tools

LightCraft runs on the human's desktop and they watch the photo change. Edits are
non-destructive and undoable: the original file is never rewritten.

## The library is the human's

LightCraft keeps one persistent library (by default `Pictures\LightCraft Library` on
Windows); the app and the agent share it. Treat it as the human's photo catalog:

- Look before you change anything: `query_photos`, then work on the photos you were asked
  about. Never delete, reject or rate photos you were not asked to.
- `import` defaults to `mode: "add"` (the files stay where they are). Use
  `mode: "copy"` into a workspace folder when asked to gather files; **never
  `mode: "move"`** unless the human asked for exactly that.
- Everything is undoable (`cmd_edit_undo` through `run_command {command: "edit.undo"}`):
  undo a wrong step rather than fixing it with another.

## Loop

1. `app_open` to start where the human can watch (any other tool also opens the app). The
   extension points the human's Agent screen at the app (`screen: following this window`);
   only on `screen: not followed`, with PiCode's `computer` tool, take one screenshot of the
   returned `window`.
2. `query_photos {filter?, sort?, limit?}` → photo ids. `select_photos` (or pass `id`) makes
   a photo the active one; most tools act on the active photo.
3. `list_controls` names the sliders (`light.exposure`, `light.contrast`…); `get_develop`
   reads a photo's settings; `set_develop {values: {"light.exposure": 0.7}}` changes them
   (one undo step). `apply_preset {preset, amount}` applies a preset (ids from
   `run_command {command: "presets.list"}`), `crop {rect: [x0,y0,x1,y1], angle}` in
   normalized 0..1 coordinates.
4. Look at the result: `render_photo {id}` (the develop result as an image) or `screenshot`
   (the whole window). Say what you see; adjust; render again.
5. `export {path}` for one photo (format from the extension) or `export {dir, ids, naming}`
   for a batch. Paths may be absolute or relative to the workspace.

Anything without its own tool is a command: `list_commands {filter}` → `run_command
{command, params}`. `references/commands.tsv` is the whole index (231 commands in 0.2.1) to
grep offline. The 359 `cmd_*` shortcut tools of the app are not listed here (they are
`run_command` with a fixed id); calling one by name still works.

## Paths

Absolute paths and paths relative to the workspace are translated for the app on Windows
(`import {paths: […]}`, `export`, `render_photo {path}`).

## The human's window

`inspect_ui`, `list_widgets`, `click`, `press_key`, `type_text` and `pointer_gesture` drive
the live window like a person; prefer commands for the edit itself.

## References

- `references/mcp.md` and `references/control-protocol.md`: LightCraft's own documentation
  (v0.2.1, MIT/Apache-2.0, vendored unchanged).
- `references/commands.tsv`: id, label, menu and shortcut of every command (`Cmd` is
  `Ctrl` on Windows).
