---
name: effectcraft
description: Animate in EffectCraft (an open-source After Effects-style motion graphics app) through the effectcraft MCP tools — compositions, text and footage layers, keyframes, effects and expressions in the app the human is watching, then look at frames and render a video into the workspace.
---

# Motion graphics in EffectCraft through the tools

EffectCraft runs on the human's desktop and they watch the composition take
shape. Everything is an engine command; properties have paths.

## Loop

1. `app_open` (optionally with an `.ecproj` `file`) to start where the human
   can watch; any other tool also opens the app on first use. It returns the
   app's `window`: if you have PiCode's `computer` tool, call it once with
   `action: screenshot, window: <that id>` so the human's Agent screen panel
   follows EffectCraft.
2. Orient: `get_state` → `get_project` → `get_comp {}`.
3. `execute_command comp.new {name, width, height, frameRate, duration}`.
4. Layers: `execute_command layer.newText {text, size, fill}`,
   `layer.newSolid`, footage through `file.import {paths: [...]}` then a layer
   from the item. Each returns `{layer}`.
5. Animate: `add_keyframe {layer, path, keys:[{time, value}], interpolation}`
   (`transform/position`, `transform/scale`, `transform/opacity`,
   `transform/rotation`…); `set_property` for static values or an
   `expression` (`"time*90"`).
6. Effects: `list_effects {filter}` → `add_effect {layer, effect, values}`;
   tune with `set_property {path: "effects/#1/<param>"}`.
7. Look: `render_frame {time, max_side}` — check the start, middle and end.
8. Render the video: `execute_command renderQueue.add {comp, format: h264
   | prores | webm | png, output}` then `execute_command renderQueue.render
   {wait: true}`. Save the project with `save_project {path}` (`.ecproj`).

## Paths

Two kinds: **property paths** (`transform/position`, `effects/#1/blurriness`)
are never touched; **file paths** in `open_project`, `save_project`,
`render_frame` and `screenshot` may be relative to the workspace. Inside
`execute_command` params (`file.import` `paths`, `renderQueue.add`
`output`) give absolute paths — they are translated for the app — or ask
`app_path` first.

## References

- `references/agents.md` (tools, cookbook, tracking, roto, text, scripts) and
  `references/control-protocol.md`: EffectCraft's own docs, v0.3.1,
  MIT/Apache-2.0, vendored unchanged.
- `references/commands.tsv`: id, label, menu and shortcut of every command
  (`Cmd` is `Ctrl` on Windows). `describe_command` gives a command's params
  and JSON Schema.
