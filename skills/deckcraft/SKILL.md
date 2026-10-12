---
name: deckcraft
description: Build presentations in the real DeckCraft window with MCP tools, inspect slides and render them, then save and reopen PPTX or native DeckCraft files in the workspace.
---

# Presentations in DeckCraft

1. `app_status`, then `app_open` (optional workspace `file`). The extension uses
   control port 7990. Respect another workspace or a window opened without an
   agent connection: ask the owner to save and close it instead of making a
   second copy. Screen-follow is confirmed only by `screen: following this window`;
   if unavailable, take one screenshot of the returned window when the computer
   tool is available.
2. `new_presentation {blank: true}` starts without a first slide. `add_slide
   {layout: "title", title, body}` adds one. Shapes/text use slide points; a
   16:9 slide is 960 × 540. `add_text_box {x, y, w, h, text, size}` adds text.
3. `inspect_document`, `inspect_slide {slide: 0}` and `render_slide {slide: 0}`
   verify structure, layout and content. Rendering a slide does not photograph
   the window. Use `list_commands` / `run_command` for remaining commands.
4. `save_presentation {path: "deck.pptx"}` or a `.deckcraft` path; reopen with
   `open_presentation` and inspect again. `export` provides delivery formats;
   inspect its schema before calling. Never claim broad PowerPoint fidelity.

Use dedicated tools for content and `call_app` for native UI state/input.
Start a full-screen show only when the owner asks to present. Do not overwrite
or close an existing owner presentation without authorization.

Dedicated file tools accept absolute/workspace-relative paths; use `app_path`
for relative paths nested inside generic commands. The native app's file access
is not confined by translation. Loopback control in v0.5.0 has no documented
key; do not describe it as authenticated. Existing files remain authoritative.

References: `references/mcp.md`, `references/control-protocol.md` and the
captured connected `references/tools.tsv` (v0.5.0, MIT).
