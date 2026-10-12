# Storage and recovery policy

This release adds no extension database, credential vault or durable UI setting.
The PiCode backup contract (`docs/architecture/backups.md` and
`internal/backup/inventory.json` in the core repository, read 2026-10-12) covers
extension databases, not arbitrary project trees or external native app homes.
The extension must not imply otherwise.

| Source | Owner / recovery | Snapshot treatment and reason |
|---|---|---|
| Workspace DOCX/PPTX/XLSX and existing creative files | Owner's workspace files; back up/reopen using project/file backups | Outside PiCode daemon snapshots; not an extension-owned data store |
| Existing `~/.picode-artcraft/<app>.json` launch metadata | Extension runtime; regenerated after a verified launch | Excluded runtime projection; stale metadata alone is never trusted |
| `~/.picode-artcraft/<app>.lock` | Extension process coordination | Excluded; OS lock state is not restorable and file contents carry no user data |
| Existing app launch logs and temporary screenshot files | Runtime diagnostics / disposable capture | Excluded runtime data; no new document content is intentionally logged |
| WordCraft native `control-key.local-<port>` | Upstream app; generated per window, removed on close | Excluded ephemeral control credential; CLI re-reads after reconnect; never copied into extension state |
| Native app settings, recent-file lists, recovery data and LightCraft library | Upstream apps; original locations remain authoritative | Not currently declared by PiCode backups; an explicit coverage debt, not claimed recoverable here |
| Page selection/search/previews | Browser memory | No persisted source; reload discards these |

`PICODE_CRAFT_STATE_DIR` can isolate runtime metadata for QA; default location and
older launch metadata remain compatible. Locks use existing runtime storage.
No cleanup or restore command deletes workspace files/native preferences. The
independent recovery fixture `test_recovery_does_not_trust_old_launch_state`
seeds an older launch record and proves a closed app is freshly launched and
rebound rather than trusting that record. Cross-process lock recovery is tested
by `test_cross_process_lock`. Workspace file round trips are measured separately.

Native preference/library coverage is still open: inventory and independent
recovery fixtures must be added to PiCode core in an explicitly scoped follow-up
before claiming daemon-backup recovery of those external stores. This does not
reduce an existing accepted coverage promise.
