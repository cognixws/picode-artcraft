# Office integrations and GUI validation

Branch: `feat/office-gui-plan`, extension v0.6.0. Measurements on 2026-10-12.
No production extension update, publication, merge or deploy is included.
PiCode core was read and built for scratch; its tracked files were not changed.

## Automated extension gates

`make ci-scoped` and `make close` run the static HTML/JavaScript package check,
manifest/catalog consistency and host contribution budgets, fourteen Python
lifecycle/RPC/stdio tests and two JavaScript decision-table/filter tests. All
passed. The stdio test covers all ten servers, including old protocol negotiation,
PrintCraft's UI extras and LightCraft's reduced advertised catalog.

Tests exercise no second launch across concurrent callers, process/thread locks,
foreign listener refusal, invalid connections and workspace mismatch, old runtime
metadata recovery, explicit file routing, invalid/outside GUI paths, no automatic
mutation replay and owned bridge-child cleanup. Platform-native POSIX behavior is
mock-tested, not measured with installed Linux apps.

The three added upstream schemas total 58,354 bytes: WordCraft 16 tools,
DeckCraft 25, GridCraft 21; each wrapper adds three tools (71 advertised total).
This is a raw schema-size measurement, not a measured model token/cost budget
across all supported CLIs. Existing v1 launch carriers and permission defaults
are retained.

## Browser and visual evidence

An owned PiCode scratch (`craftapps-evolution`, localhost:19326) built successfully
with `make web` and the Go embed build. The extension passed real preview/install,
workspace enablement and update there. `tests/browser_qa.py` uses the real host,
opaque iframe, process relay, runtime and theme. Its first capture uses actual
native discovery; state/error captures use labeled HTTP QA fixtures. Those
fixtures do not prove native provider/lifecycle behavior.

Browser assertions passed search and purpose/status filters, empty search and
Clear filters, keyboard selection, no duplicate open request, opening feedback,
preview error retention, workspace/status retry, disabled-process guidance,
desktop/narrow/phone routing and document/control geometry. The host overlay
audit returned `ok: true`; toolbar controls measured 36px with no misaligned rows.
The catalog's last row could be scrolled fully into view. No page errors occurred.

Screenshots live in PiCode's ignored `var/screenshots/craftapps-*.png`, not git:
actual desktop/bottom, loading/opening/connected preview, empty search, blocked,
workspace error/mismatch/empty/no-folder, uncontrolled app, status/preview error, host menu,
light mode, hover, narrow list/detail and mobile list/detail. A separate reviewer
read those images after corrections and returned **visual-review: PASS, browser
scope**. Initial cutoff/guidance and blocked-state indefinite loading defects were
fixed before the final verdict.

Visual card: overlay contained yes; labels readable yes; trigger usable yes;
clip/double-scroll/dead hover no; next action obvious yes. Browser mobile
screenshots do not certify a physical phone. Native WebView2 rendering is still
unverified.

## Real Windows/WSL app receipts

Official v0.5.0 Windows portable archives were checksum-verified and unpacked
under an owned QA directory on drive E. Test ports were 17982/17983/17990, with
isolated runtime/settings and no native preference reads where supported.
Production discovery folders and installed packages were not replaced.
Connected `tools/list` was captured for all three apps and its release docs and
licenses are vendored in the extension.

| App | Measured outcome | Limit |
|---|---|---|
| WordCraft | Wrapper opened native window; created paragraphs and bold text, saved DOCX, reopened and read exact text; bold OOXML independently inspected; invalid key refused; restart rotated the key and reconnect succeeded | Full DOCX fidelity, native print and layout parity are not established |
| DeckCraft | Wrapper opened native window; created slide/title/text box, saved PPTX, reopened and inspected the preserved slide text/shapes; rendered a slide | Full animation/theme/Office parity is not established |
| GridCraft | Wrapper opened native window; wrote data and formula, saved XLSX; independent headless reload read `=SUM(B2:B3)` and computed value 1600 | The first native reopen reused the in-memory workbook; the separate reload is the disk evidence |

WordCraft and DeckCraft previews returned real page/slide PNGs. GridCraft's
unfocused window screenshot timed out; the page instead exposes a bounded,
read-only formatted cell preview A1:H12, explicitly labeled as cells. Its native
screenshot tool remains forwarded with a deadline; window capture is an open
upstream/native acceptance debt. No screenshot of a window is claimed from cells.

Direct wrapper calls returned the native window identity with `screen: not
followed` because the standalone QA caller had no PiCode agent-bound credential.
That result is honest and does not certify the native Agent screen. The existing
screen-follow door is retained; final WebView2/agent-bound acceptance is separate.

## Agent acceptance

A fresh isolated Codex QA session read the three shipped skills. The first run
was blocked by the temporary MCP approval defaults; the second reached MCP but
lacked its explicit portable-app environment. These were QA setup failures, not
app content/fidelity receipts. The corrected configuration exposes only
`app_status`, `app_open` and each app's inspection/read tools, with approval for
those exact calls in the owner-authorized QA task. No mutation tools are enabled.

Environment variables are passed explicitly through each local MCP server's
`env`; a filtered CLI environment cannot be assumed to forward arbitrary
`PICODE_*` variables. The official
[Codex MCP configuration](https://learn.chatgpt.com/docs/extend/mcp?surface=cli)
and [per-tool configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference)
were checked. No user configuration or broad tool approval setting was changed.
The temporary native CLI login copy is removed in a finally block after each run.

Corrected real-agent result: **PASS for all three apps**. The agent opened each
existing QA fixture and verified DOCX text, PPTX slide content, and XLSX B4
formula/value through the shipped skills and native MCP wrappers. It acknowledged
no native screen-follow; no computer tool was available for its fallback.
It did not edit/overwrite files or close windows.

## Remaining acceptance

The open items and untested decision-table rows are recorded in
[the native acceptance topic](handoff/open/office-native-acceptance.md).
The extension remains on its isolated branch for review; updating an installed
extension changes its digest and requires reselecting the affected agent parts.
