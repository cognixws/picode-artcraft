# Crafting Apps extension architecture

The extension supplies ten independent v1 MCP servers and skills plus one
sandboxed HTML page. It uses PiCode's process, theme, context, links and events
runtime and the existing `screen:follow` and `workspaces:read` doors. No
Craft-specific route, database or UI component is added to PiCode core.

`server/catalog.json` owns app identity, supported file routes, connection
arguments, probe tools and dedicated path parameters. Both Python servers read
it; `/catalog` returns safe metadata to the page before native status arrives.
`picode-extension.json` remains the install-reviewed declaration. The package
check validates its app/skill names and the host's contribution limits.

| Layer | Responsibility |
|---|---|
| `craft_mcp.py` | Discovery, launch coordination, identity/protocol verification, workspace binding, upstream MCP forwarding and screen-follow |
| `craft_page.py` | Enabled workspace lookup; catalog/status; open/file/preview requests through the host-authenticated relay |
| `ui/domain.js` | Status/action decisions and combined filters |
| `ui/apps.js`, `apps.css` | Searchable catalog, detail/actions, preview and recoverable browser states |

The same per-app reentrant thread lock and file lock serialize page and MCP
callers. Launch checks both the listener and a read-only control call before
announcing readiness. Windows also checks the listener's process name; the
MCP initializer must name the expected app. A listener alone never establishes
readiness. An occupied foreign port is refused. A window without control is
never closed, restarted or replaced automatically. Configured ports must be
valid and unique among catalog entries (ADR-0001).

Existing launch metadata records which workspace opened a window. Live windows
bound to another workspace are refused rather than silently rebound; absent
metadata is reported as unknown, not as native filesystem confinement. Old
metadata without a live connection cannot prove an app is running. User file
paths are translated for WSL; most watched apps do not enforce a root. PhotoCraft
and PrintCraft retain their previous native-root handling. GUI Open with is
restricted to existing files in an enabled workspace. Paths in generic command
parameters use `app_path`; absolute path-like values are translated recursively.

WordCraft uses 7982, GridCraft 7983 and DeckCraft 7990, avoiding existing ports.
The upstream WordCraft CLI reads its own rotating key from its standard native
location. No key enters the manifest, page, command arguments or receipts.
Bridge reads have deadlines and short-lived page bridges are reaped. A lost
mutation answer is never automatically replayed because it may already have
changed the document. The owner checks the result before retrying.

PhotoCraft/VectorCraft/EffectCraft/FilmCraft/LightCraft/PrintCraft keep their
existing snapshot adapters. DesignCraft and WordCraft render a document page;
DeckCraft renders a slide. GridCraft reads live formatted cells A1:H12 because
its v0.5.0 unfocused window capture timed out in native QA. The UI names each
preview truthfully and keeps prior previews, marked stale, when refresh fails.
The native GridCraft screenshot tool remains available to agents; it has a
bounded error path, not a successful page-snapshot receipt.

Status polls the extension process every ten seconds only while visible. Native
apps can be changed outside PiCode, so its event feed cannot be the sole source;
extension events trigger workspace/status rechecks. Requests do not overlap.
Workspaces and prior app states survive failures with visible Retry. No badge
claims agent ownership/activity without telemetry. Search/selection/previews
stay in memory; no new durable UI preference store is introduced.

The desktop keeps list and detail side by side above 760px of iframe content;
narrow panes/phones show one at a time with Back. Each pane owns its scroll;
the iframe document does not add a nested scrollbar. Host tokens define every
color/control role. Pattern adaptation and sources are in
[the evolution plan](office-gui-evolution.md). Accessibility uses native buttons,
selects, search, details, focus rings and keyboard navigation; no homemade modal
or select library is needed for this dependency-free HTML surface.

The current host allows sixteen Open with entries and eight activation patterns.
The extension preserves its previous entries and adds Office formats within those
limits. `.doc` can be opened through the agent/page but has no host menu entry;
`.deckcraft` has Open with but no automatic activation pattern. DOCX/PPTX/XLSX
activate the extension. No host-limit or capability-group migration is implied.

See [storage policy](storage-contract.md), [validation](validation-office-gui.md)
and [launch decision](decisions/0001-verified-app-lifecycle.md).
