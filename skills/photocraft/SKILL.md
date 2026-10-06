---
name: photocraft
description: Edit raster images in PhotoCraft (an open-source Photoshop-style editor) through the photocraft MCP tools — open or create a document in the app the human is watching, run engine commands (adjustments, filters, layers, selections, fills, text), look at the result, and save into the workspace.
---

# Editing images in PhotoCraft through the tools

PhotoCraft runs on the human's desktop and they watch it change. Every menu
item, tool and dialog is one engine command, so you edit by running commands,
not by pointing and clicking.

## Loop

1. `app_open` (optionally with `file`) to start where the human can watch;
   any other tool also opens the app on first use. The extension points
   the human's Agent screen at the app itself (`screen: following this
   window`). Only when it answers `screen: not followed` and you have
   PiCode's `computer` tool, call it once with `action: screenshot,
   window: <the returned window>` so the panel follows the app.
2. `doc_open {path}` or `doc_new {width, height}`. `session_list` shows what
   is already open — the human may have their own documents there: never
   close or overwrite one you did not open.
3. Find the command: `command_list {filter}` (ids, menu paths, parameter
   docs, whether it is enabled now). `references/commands.tsv` is the whole
   index for 0.2.0 to grep offline.
4. Run it: `command_run {id, params}` — the key is `id`, not `command`.
   Several in one go: `command_batch {steps:[{id, params}], stop_on_error}`.
5. Look before you say it is done: `doc_render_preview` (flattened PNG) or
   `ui_screenshot` (the window). `doc_inspect` gives the layer tree,
   history, selection and active layer.
6. `doc_save {path}`: `.pcraft` is the lossless native format; `.psd`,
   `.png`, `.jpg`, `.tif`, `.webp`, `.exr` export by extension.

## Paths

PhotoCraft only reads and writes below the workspace folder (it was opened
with the workspace as its automation root). Give paths relative to the
workspace (`art/cover.png`); an absolute path inside the workspace is also
accepted. A parent folder must already exist before saving into it.

If `app_status` shows another `files_root`, PhotoCraft was opened for another
workspace: work under that root or ask the human to close PhotoCraft.

## Useful commands

| Goal | Command (params) |
|---|---|
| Fill | `edit.fill` (`contents: "color"`, `color: "#rrggbb"`) |
| Curves / levels as adjustment layers | `layer.newAdjustmentLayer.curves` (`points`), `layer.newAdjustmentLayer.levels` |
| Sharpen / blur | `filter.sharpen.smartSharpen` (`amount`), `filter.blur.gaussianBlur` (`radius`) |
| Invert | `image.adjustments.invert` |

| Painterly ageing | `filter.gallery.texturizer` (`texture: "canvas"`), `filter.gallery.craquelure` (`crackSpacing`, `crackDepth`, `crackBrightness`), `filter.gallery.filmGrain` |
| Warm tone | `layer.newAdjustmentLayer.photoFilter` (`filter: "sepia"`, `density`) |

Check the exact parameters with `command_list` before the first use: the
parameter doc is a compact signature (`"amount":%=100` means a percentage,
default 100).

## The human's window

`ui_inspect` reads the live UI (tool, panels, dialogs, menu tree);
`ui_menu_invoke`, `ui_set` and `ui_pointer` drive it like a person. Prefer
commands; use the UI tools when the human asks to see a specific tool in use
or a command opens a dialog. Shortcuts in the index say `Cmd`: that is `Ctrl`
on Windows.

## References

- `references/mcp.md` and `references/control-protocol.md`: PhotoCraft's own
  documentation (v0.2.0, MIT/Apache-2.0, vendored unchanged).
- `references/commands.tsv`: id, label, menu and shortcut of every command.
