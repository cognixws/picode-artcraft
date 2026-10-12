# Crafting Apps Office integrations and GUI

- Branch: `feat/office-gui-plan`; baseline `ac69723`; plan commit `9711004`.
- v0.6 adds ten-app shared catalog, verified serialized lifecycle and list/detail GUI.
- Existing seven stdio integrations retain tested compatibility.
- `make close`: 14 Python tests, two JS tests and package-limit checks passed.
- Scratch `make web`/build/install/update and browser QA passed; production untouched.
- visual-review: PASS for browser desktop/narrow/mobile, light/dark, empty/blocked,
  preview error, file opening/opened, workspace recovery and host-menu captures read.
- Host overlay audit `ok`; control alignment, keyboard/filter/actions and stale
  preview assertions passed with explicitly identified HTTP fixtures.
- Captured native tool schemas from pinned upstream v0.5.0 releases.
- Real DOCX formatted-text and PPTX content save/reopen fixtures passed.
- XLSX formula/value preservation passed independent disk reload.
- WordCraft invalid-key refusal, rotation and reconnect passed.
- Fresh Codex QA read the three skills and inspected all three native files using
  only exact authorized read/open tools and environment; PASS.
- Temporary authentication copies deleted after QA.
- Standalone screen-follow not acknowledged: no agent credential was available.
- GridCraft window capture timed out; live cell preview provided fallback.
- Foreground measurement changed once and is inconclusive; no no-focus claim.
- Native WebView2 and physical-phone acceptance remain UNVERIFIED.
- Remaining native acceptance tracked in `docs/handoff/open/office-native-acceptance.md`.
- No merge, publication, deploy or production extension update performed.
