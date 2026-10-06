---
name: filmcraft
description: Edit video in FilmCraft (an open-source Premiere Pro-style editor) through the filmcraft MCP tools — import media, build a sequence, cut, trim, add titles, transitions and audio in the app the human is watching, look at frames and export H.264/ProRes into the workspace.
---

# Editing video in FilmCraft through the tools

FilmCraft runs on the human's desktop and they watch the timeline grow.
Every edit is an undoable engine command.

## Loop

1. `app_open` (optionally with a `.fcproj` `file`) to start where the human
   can watch; any other tool also opens the app on first use. It returns the
   app's `window`: if you have PiCode's `computer` tool, call it once with
   `action: screenshot, window: <that id>` so the human's Agent screen panel
   follows FilmCraft. The app may open on its demo project: start a new one
   (`file.newProject`, then `file.newSequence` or `file.newSequenceFromClip`)
   rather than editing the demo.
2. Import: `media_import {text}` — absolute paths, one per line (MP4/MOV,
   WAV/MP3/FLAC, PNG/JPEG…). The answer gives the new item ids.
3. Look up ids: `project_inspect`, `sequence_inspect` (tracks, clips, start
   and duration). Time is in ticks — 254016000000 per second — but commands
   also take `seconds`, `frame` or `timecode`.
4. Edit: `command_list {filter}` → `command_run {id, params}` (the key is
   `id`); several at once with `command_batch {steps}`. Source-monitor edits:
   `source.open`, `source.insert`, `source.overwrite`; `timeline.razor
   {seconds}` to cut.
5. Look: `render_frame {seconds, max_side}` or `ui_screenshot`. Undo a
   wrong step with `command_run {id: "edit.undo"}`.
6. Export: `command_run {id: "file.exportMedia", params: {path, format:
   "h264"}}` (or `export.quick`); list presets with `export.presets.list`.
   Save the project with `file.save` / `file.saveAs {path}`.

## Pitfalls (found in a real run)

- `file.newSequence {fromItem}` already places that clip on the timeline; a
  `source.insert` after it duplicates the clip. Use `fromItem` only for the
  sequence settings, or leave it out and insert every clip yourself.
- Insert in order: `playhead.set {seconds}` → `source.open {item}` →
  `source.insert`. A still image lasts 5 s.
- Stills and media of another size come in at 100 % and get cropped: select
  them (`timeline.select {clips:[...]}`) and run `clip.scaleToFrameSize`.
- `graphics.newText {text, position, size, seconds, track, time}`: `position`
  is the text's left anchor, `track` is the video track index (V2 = 1),
  `time` is in ticks.
- Cross dissolves: `timeline.select {clips:[...]}` then
  `trim.applyDefaultTransition`.
- `file.exportMedia` returns a job at once; the file is complete when its
  size stops changing.

## Paths

Give absolute paths in `media_import` and in command params (`path`,
`paths`): they are translated for the app. For a path relative to the
workspace, ask `app_path` first.

## The human's window

`ui_elements` lists clickable ids, and `ui_click`, `ui_drag`, `ui_key`,
`ui_type` operate the live app like a person — useful to show a step on
screen. Prefer commands for the edit itself.

## References

- `references/agents.md` (tools, conventions, long exports) and
  `references/control-protocol.md`: FilmCraft's own docs, v0.2.1,
  MIT/Apache-2.0, vendored unchanged.
- `references/commands.tsv`: id, label, menu and shortcut of every command
  (`Cmd` is `Ctrl` on Windows).
