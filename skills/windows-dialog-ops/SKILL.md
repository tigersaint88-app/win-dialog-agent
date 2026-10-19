---
name: windows-dialog-ops
description: >-
  Operate standard Windows dialogs (#32770) via win-dialog-agent MCP tools.
  Use when the user needs Save As, Open File, MessageBox, or other Win32 dialogs
  handled by an agent without coordinate clicks.
---

# Windows dialog operations

Prefer semantic MCP tools from `win-dialog-agent`:

1. `dialog_list` or `dialog_wait_for` → get `handle_id`
2. Use composites when possible:
   - `dialog_handle_save_as`
   - `dialog_handle_open_file`
   - `dialog_handle_messagebox` (`ok` / `cancel` / `yes` / `no`)
3. For unknown / non-`#32770` dialogs: `uia_snapshot` then `uia_find` / `uia_click` / `uia_set_text`

Rules:

- Do not use mouse coordinates for standard dialogs.
- Button labels may be Chinese or English (`保存` / `Save`, `确定` / `OK`).
- Never write into password fields.
- If elevation / UAC secure desktop blocks UIA, report the error clearly.
