---
name: printcraft
description: Work with PDFs in PrintCraft (an open-source Acrobat-style PDF workbench) through the printcraft MCP tools — read, search, combine, split, organize pages, comment, fill forms, redact, sign and save PDFs in the workspace, and open them in the real window for the human to see.
---

# PDFs in PrintCraft through the tools

PrintCraft's MCP server is different from the other Crafting Apps: it edits PDFs **without
a window**, in memory, only under the workspace folder. The real window is a second channel
(`ui_*`) that you use to *show* the result. So the loop is: edit with the document tools,
`doc_save`, then open the saved file in the window.

## Loop

1. `doc_open {path}` (a PDF in the workspace, relative or absolute) or `doc_create {from:
   "blank"|"images"|"text"}` returns a document id. `doc_list` shows what is open.
2. Read: `doc_info`, `text_extract {doc, pages}`, `text_find`, `page_render {doc, page,
   dpi}` (an image — look at it).
3. Edit: `page_rotate`, `page_delete`, `page_move`, `page_insert_blank`, `page_insert_file`,
   `page_extract`, `doc_combine`, `doc_split`, `page_add_text`, `page_add_image`, forms
   (`form_fields`, `form_fill`), `redact_mark` / `redact_apply`, `comment_add`, bookmarks,
   stamps, watermark… `references/tools.tsv` is the whole index (123 tools in 0.2.1). Edits
   are undoable (`edit_undo`) and stay in memory until `doc_save`. A wrong argument name is
   refused with the list of accepted ones, so read the error.
4. Save: `doc_save {doc, path}` — in place it is an incremental update (signatures stay
   valid); to a new path it is a full rewrite. The write is atomic. Never overwrite the
   human's PDF unless asked: save a copy.
5. Show it: `app_open {file}` (or `ui_open {path}`) opens the PDF in the real window and
   points the human's Agent screen at it (`screen: following this window`; only on `screen:
   not followed`, with PiCode's `computer` tool, take one screenshot of the returned
   `window`). `ui_screenshot` looks at the window; `ui_state` says which document and page
   it shows.

## What stays inside the workspace

PrintCraft was started with the workspace as its only root: paths outside it are refused
("is outside the allowed directory"). Give paths relative to the workspace, or absolute
inside it.

## The window (`ui_*`)

`ui_inspect {query}` (widgets with labels and ids), `ui_click {label}` or `{id}`, `ui_key
{key, modifiers: ["command"]}` (`command` is Ctrl on Windows), `ui_type {text}`,
`ui_command {id}` and `ui_commands` (every menu/tool command, e.g. `comment.square`),
`ui_open`, `ui_screenshot`. The window is the human's: do not close or change documents
they have open.

## References

- `references/readme.md` (the "Driving the app itself" and agent sections) and
  `references/automation.md`: PrintCraft's own documentation (v0.2.1, MIT/Apache-2.0,
  vendored unchanged).
- `references/tools.tsv`: name and first sentence of every document tool.
