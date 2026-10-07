---
name: designcraft
description: Lay out pages in DesignCraft (an open-source InDesign-style page-layout app) through the designcraft MCP tools — documents, text frames and stories, styles, placed images, then look at the page and export PNG or save the native .designcraft file, in the app the human is watching.
---

# Page layout in DesignCraft through the tools

DesignCraft runs on the human's desktop and they watch the pages take shape. Every action is
a command; the dedicated tools cover documents, text, images and looking.

## Loop

1. `app_open` (optionally with a `.designcraft` `file`) to start where the human can watch;
   any other tool also opens the app. The extension points the human's Agent screen at the
   app (`screen: following this window`); only on `screen: not followed`, with PiCode's
   `computer` tool, take one screenshot of the returned `window`. The app is on port 7981
   (its own default, 7979, is VectorCraft's).
2. `new_document` (preset, size, columns, margins, bleed, facing pages) or `open_document`.
   `inspect_document` lists the pages, items (ids, bounds), stories (overset text) and styles
   — never close or overwrite the human's own documents.
3. Build: `execute {command: "frame.create", params: {rect: [x0,y0,x1,y1], content: "text",
   text: "…"}}` (coordinates are points, y down; a Letter page is 612 × 792), then
   `set_story_text` / `get_story`, `execute type.char`, `style.paragraph.apply`; `place_image
   {path}` puts a picture on the page. Several commands in one call: `batch`.
4. Look: `render_page {page, scale}` renders the page headless (preferred: it does not touch
   the window) or `screenshot` (the whole window — it brings the window to the front).
   Check for overset text in `inspect_document`; fix what reads wrong.
5. `export_png {path}` for a page, `save_document {path}` for the native `.designcraft`.

Anything without its own tool is a command: `list_commands {filter}` (id, params doc, whether
it is enabled now), then `execute`. `references/commands.tsv`
is the whole index (432 commands in 0.2.1) to grep offline.

## Paths

Absolute paths or paths relative to the workspace; PiCode turns them into the path Windows
sees.

## Dialogs

`dialog_set {field, value}`, `dialog_confirm` and `dialog_cancel` fill and close a dialog a
command opened. A command with all its params runs without a dialog.

## The human's window

`ui_inspect`, `ui_set`, `select_tool`, `pointer`, `click`, `drag`, `key`, `type_text` and
`menu_list` drive the live window like a person; prefer commands for the layout itself.

## References

- `references/agents.md`, `references/mcp.md` and `references/control-protocol.md`:
  DesignCraft's own documentation (v0.2.1, MIT/Apache-2.0, vendored unchanged).
- `references/commands.tsv`: id, label, menu and shortcut of every command (`Cmd` is `Ctrl`
  on Windows).
