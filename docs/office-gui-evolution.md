# Crafting Apps: Office integration and GUI evolution

Status: owner approved implementation on 2026-10-12. This document preserves
the proposed direction; implementation outcomes and limits are recorded in
[validation-office-gui.md](validation-office-gui.md).
Work branch: `feat/office-gui-plan`; baseline: `ac69723` (extension v0.5.0).

## Evidence and scope

The [owner's tweet](https://x.com/feliperabeloep/status/2109390898962292865)
mentions Word, PowerPoint and Excel. Its image was inspected and identifies
WordCraft, DeckCraft and GridCraft v0.5.0. The supplied PiCode screenshot shows
the current seven-app page. Source inspection confirms seven MCP entries,
seven skills, a Python process and `ui/apps.html`; the extension lives outside
the PiCode core. Extend that repository to ten apps, preserving existing tools.

The visible problems are repetitive cards without app identity, repeated state
essays, little guidance by purpose and uneven use of space. Source inspection
adds duplicated catalog/file mappings across the bridge, server and page;
window presence is presented as agent readiness without a protocol check;
non-WSL fixed-port status returns no listeners; workspace fetch errors are
silently treated as an empty list. Existing polling observes external native
apps, so a PiCode feed alone cannot replace it.

## New integrations

Read the release-tagged MCP and control documentation, then capture schemas
from the exact installed release. Main-branch documentation is newer and must
not be treated as a v0.5.0 capability promise.

| App | First supported workflow | Upstream v0.5.0 connection | Required adaptation |
|---|---|---|---|
| WordCraft | Create/edit a document, inspect text, save/reopen DOCX | `mcp --connect 127.0.0.1:7981`; per-window control key | Allocate a port different from DesignCraft's 7981; let the upstream CLI read its key; verify reconnect after rotation |
| DeckCraft | Create slides with text/shapes, inspect, save/reopen PPTX | `mcp --connect PORT`; docs use 7990 | Native `.deckcraft` and `.pptx`; render-slide preview distinct from window snapshot |
| GridCraft | Write cells/formulas, read results, save/reopen XLSX | `mcp --connect 7979` | Allocate a port different from VectorCraft's 7979; explicit `.xlsx`/native routing; CSV needs a deliberate app choice |

Sources: [WordCraft MCP](https://github.com/storytold/wordcraft/blob/v0.5.0/docs/mcp.md),
[control](https://github.com/storytold/wordcraft/blob/v0.5.0/docs/control-protocol.md);
[DeckCraft MCP](https://github.com/storytold/deckcraft/blob/v0.5.0/docs/mcp.md),
[control](https://github.com/storytold/deckcraft/blob/v0.5.0/docs/control-protocol.md);
[GridCraft MCP](https://github.com/storytold/gridcraft/blob/v0.5.0/docs/mcp.md),
[control](https://github.com/storytold/gridcraft/blob/v0.5.0/docs/control-protocol.md).

Keep watched native operation as the first integration slice. Headless work is
a separately selected later mode; a successful headless call cannot imply a
visible window. Do not promise Microsoft Office parity or round-trip fidelity
outside the tested fixtures. Installation starts as an official download link,
not an automatic installer or updater.

## Visual direction

Use a compact catalog and a selected-app detail pane. One identifiable icon,
purpose and short state per app; one primary action in the detail pane. Search
matches names and tasks. Filter by purpose: All, Documents, Images, Motion.
WordCraft, DeckCraft, GridCraft, DesignCraft and PrintCraft belong to Documents;
the remaining apps retain their specific purpose labels. Do not move apps
between groups when their runtime state changes; expose status as a filter.

```text
Crafting Apps                 Workspace [Project]   Refresh
Search apps or tasks…        All | Documents | Images | Motion
─────────────────────────────────────────────────────────────
APP CATALOG                  SELECTED APP
[icon] WordCraft   Ready      [icon] WordCraft
       Documents             Write and format documents
[icon] DeckCraft  Not found   Ready to open             [Open]
       Presentations         ────────────────────────────────
[icon] GridCraft     Open     Preview / window snapshot
       Spreadsheets          (only when explicitly requested)
…                            Files • connection details
```

The sketch is layout intent, not a rendered or validated GUI. At narrow pane
widths show the catalog and detail sequentially with Back; the phone keeps
the same actions. Use PiCode's extension tokens, shared 36px control height,
visible keyboard focus, semantic controls and reduced-motion support. App
identity uses licensed upstream icons where available, otherwise existing
host icon primitives; no second theme palette. Keep snapshots in the selected
detail to prevent grid height jumps. Label rendered content and window photos
accurately. No fake preview, agent activity or installation state.

### Benchmarks and adaptations

| Reference inspected | Adaptation | What this establishes |
|---|---|---|
| Craft Launcher in the tweet image | Distinct icons, purpose, install state and contextual action | Visual evidence from one screenshot; no behavior verification |
| [Raycast Settings](https://manual.raycast.com/settings) | Searchable, compact navigation; secondary configuration after selection | Documentary reference for search, compactness and keyboard access |
| [VS Code Extensions](https://code.visualstudio.com/docs/configure/extensions/extension-marketplace) | Search/filter catalog and separate item details | Documentary reference; avoid editor chrome and irrelevant marketplace features |
| [Linear search](https://linear.app/docs/search) | Fast task-oriented search and keyboard reachability | Documentary reference; responsiveness remains our acceptance measurement |
| PiCode `docs/benchmarks/2026-10-09-extensions-list.md` and Cursor bar | List/detail layout, dense readable rows, truthful states and skeletons | Existing product benchmark adapted to an extension-owned iframe |

External docs were read on 2026-10-12. These are pattern references, not
authenticated interaction or a comparative performance study.

## State and action decision table

These rows are proposed behavior. Implement table-driven bridge/domain tests
and browser coverage, or retain an explicit unverified row at handoff.

| Conditions | State and action | Verification |
|---|---|---|
| Extension process unavailable | One blocked line + open extension settings | Bridge refusal + blocked screenshot |
| Workspace lookup failed | Keep last valid selection; show Retry; block unresolved opens | Error response + retry test |
| No enabled workspace / folder unavailable | One line + choose/configure workspace | Empty/blocked screenshot |
| App not installed | Not installed + official download link | Discovery fixture + link test |
| Installed, no window | Ready to open + Open | Discovery and launch fixture |
| Opening | Opening feedback immediately; prevent duplicate launch | Concurrent launch test + slow screenshot |
| Window present, control unavailable or wrong key | Open without agent connection + visible recovery action | Native/protocol fixture; never auto-close a human window |
| Port belongs to another process | Connection conflict + diagnostics; do not adopt it | Identity/handshake test |
| Authenticated/verified control available | Open + snapshot/content preview as supported | Real handshake; window alone is insufficient |
| Open in a different workspace/root | Explain mismatch; refuse silent rebinding | Two-workspace test |
| File extension ambiguous | Ask which compatible app; no silent import | Routing test (CSV and shared image formats) |
| Snapshot fails or raises the foreground window | Preserve last preview; label stale/error; use render if measured safe | Foreground handle before/after + image inspection |
| Status refresh fails | Keep last results; mark freshness unknown + Retry | Offline/recovery browser test |
| Concurrent GUI and agent calls | Reuse verified session; serialize conflicting opens; refuse unsafe workspace switches | Race test across separate MCP/process callers |

No activity badge names an agent without actual ownership telemetry. An open
app is not proof that an agent is using it. No new global close/restart action
is implied by this plan.

## Delivery sequence

| Slice | Concrete output | Exit evidence |
|---|---|---|
| 0 — Research (this branch) | Scope, source-backed protocol matrix, visual direction and decision table | Screenshot inspection and tagged upstream docs |
| 1 — Catalog and lifecycle | Shared app catalog, explicit connection adapters, truthful status, collision/concurrency handling | Seven-app regression fixtures and decision-table tests |
| 2 — Office adapters | Three MCP entries, captured tool catalogs, three skills, licenses/references, file routing and screen follow | Real create/edit/save/reopen per app on pinned releases |
| 3 — GUI refinement | Searchable list/detail, identity, task grouping, contextual actions, selected preview and recovery states | Scratch desktop/narrow/mobile screenshots read by reviewer |
| 4 — End-to-end acceptance | Agent uses each new skill; native screen follows correct window; existing apps still work | Separate scratch/browser, Windows/WebView2 and native app receipts |
| 5 — Review-ready release | Version/docs/changelog/handoff, installation/update compatibility | Extension checks green; integration/update is separately recorded |

### Architecture and compatibility

Reuse the standard-library Python bridge and the current extension doors
(`screen:follow`, `workspaces:read`, process, theme, context and links). Define
app metadata once and return a safe public catalog to the page; keep adapter
logic explicit where protocols differ. Add no app-specific code to PiCode core.
Do not bundle a frontend framework just for this surface; semantic HTML and
existing tokens fit the current extension page.

Prefer retaining the current v1 per-app MCP launch contract for this slice.
Measure the new tool-schema budget across supported launch carriers; converting
to capability groups/v2 is a separate choice, not a prerequisite. An extension
update changes its digest and may require reselecting agent parts; document
that lifecycle rather than implying tools become live in existing sessions.

Before any implementation adds or moves state, inventory workspace outputs,
extension data, app-native settings/libraries and WordCraft's ephemeral keys.
Read the PiCode backup contract/inventory; declare inclusion/exclusion and
recovery fixtures. A workspace path translation is not a filesystem sandbox:
validate actual native enforcement on the pinned version. Newer WordCraft
main documents headless root flags and rejects their combination with connect;
that does not establish confined watched operation in v0.5.0. A change to a
documented protocol, security, persistence or process decision needs the
appropriate ADR/owner decision before crossing that boundary.

Native install discovery, release-specific startup flags, workspace confinement,
snapshot focus behavior and two-agent concurrency remain unverified. The
existing Linux status limitation must be fixed/tested or explicitly retained
as a platform debt; do not label a Windows-only measurement cross-platform.

## Acceptance bar

For each new app: inspect real structure, edit, save, reopen and compare a
fixture; check native window identity, reconnect and screen-follow separately.
Include DOCX text/styles, PPTX slide/text/shape preservation and XLSX formula
and computed-value preservation. No broad fidelity claim follows from these.

For GUI: first-load skeleton; preserved data on refresh; missing app/process/
workspace; errors and retry; empty search; opening; active selection; preview
failure; dark/light; keyboard; narrow pane and phone. Feedback target is under
100ms, not fabricated completion. Read screenshots and measure host overlay
audit after overlays; also inspect iframe-local overflow/geometry. Apply the
repository's five-question visual card. Browser PASS never substitutes for
Windows/WebView2 or physical-phone acceptance.
