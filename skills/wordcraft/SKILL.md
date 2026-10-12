---
name: wordcraft
description: Write, format and review documents in the real WordCraft window using its MCP tools, inspect the text, and save DOCX files into the workspace.
---

# Documents in WordCraft

Use the WordCraft MCP tools, not pixel typing, for document content. The extension
opens a native window; its default control port is 7982 to avoid DesignCraft.

1. `app_status`, then `app_open` (optionally with a workspace `file`). If another
   workspace owns the running window or the agent connection is unavailable,
   ask the owner to save and close it; never close or replace their documents.
   `screen: following this window` confirms PiCode's screen-follow request.
   If it says not followed and the computer tool is available, take one screenshot
   of the returned window. A window handle alone does not confirm screen-follow.
2. `new_document {template: "blank"}` for a new task, or `open_document {path}`.
   Use `type_text {text, paragraphs: true}` for paragraphs, `select_text` and
   `execute` for formatting. Discover command parameters with `list_commands`.
3. Verify with `get_text` and `inspect_document`; use `render_page {page: 1}`
   for the actual page. This is a document render, not a window screenshot.
4. `save_document {path: "report.docx"}` saves into the workspace. Reopen that
   file and inspect its text before claiming round-trip success.

For review tasks, name the agent through `execute` of `file.setAuthor`, and set
`review.trackChanges {value: true}` explicitly; toggling may turn tracking off.
Keep originals unless the owner requested replacement. DOCX compatibility is
limited to what you inspect after reopening; do not claim full Word parity.

Dedicated path tools accept absolute or workspace-relative paths. For paths
inside generic command parameters, use `app_path` first. Path translation is
not a native filesystem sandbox; the watched v0.5.0 app is not workspace-confined.
Its upstream CLI reads the rotating control key automatically. Never print,
copy or log the key, and never pass it in arguments.

References: release-tagged `references/mcp.md`, `references/control-protocol.md`
and the captured connected `references/tools.tsv` (v0.5.0, MIT).
