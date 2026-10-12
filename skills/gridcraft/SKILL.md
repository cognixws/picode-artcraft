---
name: gridcraft
description: Work with spreadsheet data, formulas and charts in the real GridCraft window, read results through MCP, and save and reopen XLSX files into the workspace.
---

# Spreadsheets in GridCraft

1. `app_status`, then `app_open` (optional workspace `file`). The extension uses
   port 7983 to avoid VectorCraft. Do not replace another workspace's window or
   launch a second copy when the owner opened it without an agent connection.
   Screen-follow requires `screen: following this window`; otherwise take one
   computer screenshot of the returned window if that tool is available.
2. `new_workbook {}` for a blank workbook, or `open_workbook {path}`. Write
   `write_range {range: "A1", values: [["Item", "Cost"], ["Rent", 1200],
   ["Food", 400], ["Total", "=SUM(B2:B3)"]]}`. Strings starting with `=`
   are formulas: preserve literal user text deliberately rather than assuming.
3. Read `read_range {range: "B4"}` (1600 in the example) and the same range with
   `formulas: true`. `inspect_workbook` checks sheets/charts and used ranges.
   `format_range`, `insert_chart`, `list_commands`, `execute_command` and
   `list_functions` cover formatting and additional operations.
4. `save_workbook {path: "budget.xlsx"}`, reopen it, then read formulas and
   computed values again. CSV/TSV are data formats and do not preserve workbook
   formatting or charts; choose the output the owner actually needs.

`new_workbook` may open a built-in sample when `sample` is supplied; do not
invent sample data for a real task. Preserve the original workbook unless
replacement was requested. Do not claim complete Excel compatibility.

Dedicated file tools accept absolute/workspace-relative paths. `screenshot`
requires an output `path` and photographs the window; it is different from
reading cells. Use `app_path` for paths nested inside generic commands.
Translation is not a native sandbox; v0.5.0 loopback control has no documented
key. Work with workspace outputs and do not inspect other files unasked.

References: `references/mcp.md`, `references/control-protocol.md` and the
captured connected `references/tools.tsv` (v0.5.0, MIT).
