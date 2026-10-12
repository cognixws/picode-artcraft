# Office integration and GUI evolution research

- Branch: `feat/office-gui-plan`; baseline: `ac69723` (extension v0.5.0).
- Audited the seven existing app integrations and the extension-owned GUI.
- Read the owner-provided screenshot visually: current clarity and hierarchy FAIL.
- Read the tweet image: WordCraft, DeckCraft and GridCraft v0.5.0 confirmed.
- Read all three apps' release-tagged v0.5.0 MCP and control documentation.
- Added `docs/office-gui-evolution.md`: evidence, protocol matrix and risks.
- Plan includes reference benchmarks, list/detail wireframe, delivery slices,
  state/action decision table and distinct browser/native acceptance gates.
- Shared catalog, connection verification, port collisions, workspace routing,
  concurrency and truthful status are prerequisites for the proposed GUI.
- Local document structural checks passed; no runtime or UI implementation.
- Extension has no Makefile or `close-summary` target; PiCode core `make close`
  does not gate this separate extension repository.
- No native tests, installation, extension update, publication, deploy or merge.
- Proposed GUI visual acceptance remains UNVERIFIED; the wireframe is intent.
- Next: owner review of the plan, then implement and verify one slice at a time.
