# win-dialog-agent

**EN:** Semantic Windows dialog automation for AI agents — OpenAI Agents SDK function tools + MCP stdio server.  
**中文：** 面向 AI Agent 的语义级 Windows 对话框操作模块（Agents SDK 工具 + MCP stdio 服务）。

> Agent says *“save to D:\out.txt”* — not *click (1024, 768)*.  
> Agent 说的是意图，不是坐标。

| | |
|---|---|
| **OS** | Windows 10 / 11 (x64) |
| **Python** | ≥ 3.10 |
| **License** | MIT |
| **Dialog class** | Fast path for `#32770`; UIA fallback for WPF / WinUI / Electron |

---

## Features / 功能

- **P0 semantic tools**: wait / list / describe / read / click / set text / Save As / Open / MessageBox  
  语义工具：等待、列举、描述、读文本、点按钮、填文本、另存为、打开、消息框
- **Bilingual buttons**: `保存` ≈ `Save(&S)` via community-editable [`aliases.py`](src/win_dialog_agent/aliases.py)  
  中英文按钮别名，欢迎 PR 扩充
- **P1 UIA fallback** for non-standard dialogs (with warning logs)  
  非标准对话框走通用 UIA，并打告警日志
- **Dual expose**: `@function_tool` (Agents SDK) + MCP stdio (`win-dialog-mcp`)  
  一份实现，两种暴露

---

## Install / 安装

```bash
# from this directory / 在本目录
pip install -e ".[dev]"

# or with uv
uv pip install -e ".[dev]"
```

Copy env template:

```bash
copy .env.example .env
```

---

## Quick start — Agents SDK / 快速开始

```python
from agents import Agent, Runner
from win_dialog_agent.tools import ALL_TOOLS

agent = Agent(
    name="DialogOperator",
    instructions=(
        "You operate Windows dialogs via tools. "
        "Prefer dialog_handle_save_as / dialog_handle_open_file / "
        "dialog_handle_messagebox for standard #32770 dialogs."
    ),
    tools=ALL_TOOLS,
)

# async example
# result = await Runner.run(agent, "Save the current Save As dialog to D:\\out.txt")
```

Core library API (no LLM required):

```python
from win_dialog_agent import dialogs

info = dialogs.dialog_wait_for(timeout=10)
dialogs.dialog_handle_save_as(info.handle_id, r"D:\out.txt")
```

---

## MCP server / MCP 服务

### Run locally

```bash
win-dialog-mcp
# or
python -m win_dialog_agent.server
```

### MCP client config (Cursor / Claude Desktop)

```json
{
  "mcpServers": {
    "win-dialog-agent": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/tigersaint88-app/win-dialog-agent",
        "win-dialog-mcp"
      ]
    }
  }
}
```

After PyPI publish you can simplify to `uvx win-dialog-agent`.

### Cursor Marketplace / Agent Plugin

This repo includes:

- `.cursor-plugin/plugin.json` — Cursor Plugin manifest
- `plugin.json` — Agent Plugins (open standard) manifest
- `mcp.json` — MCP server entry for marketplace install
- `skills/windows-dialog-ops/` — agent skill for dialog workflows

Submit / update listing: [cursor.com/marketplace/publish](https://cursor.com/marketplace/publish)  
Community directory: [cursor.directory](https://cursor.directory)

Local plugin test (optional): copy this repo into `~/.cursor/plugins/local/win-dialog-agent`, then Reload Window.

### Inspector self-test

```bash
npx @modelcontextprotocol/inspector win-dialog-mcp
```

Call `dialog_list` from the Inspector Tools tab.

### Catalog targets

Suitable for listing on [mcp.so](https://mcp.so), Smithery, Glama, and Windows 11 native MCP registry (follow Microsoft registration docs).

---

## Tool reference / 工具一览

### Discovery (P0)

| Tool | Args | Description |
|---|---|---|
| `dialog_wait_for` | `title?`, `class_name?`, `timeout?` | Wait for dialog → `handle_id` |
| `dialog_list` | — | List top-level `#32770` dialogs |
| `dialog_describe` | `handle_id` | Control tree summary for the LLM |

### Semantic actions (P0)

| Tool | Args | Description |
|---|---|---|
| `dialog_read_text` | `handle_id` | Read static / message text |
| `dialog_click_button` | `handle_id`, `label` | Click by zh/en label |
| `dialog_set_text` | `handle_id`, `text`, `field?` | Fill edit (refuses password) |
| `dialog_handle_save_as` | `handle_id`, `path` | Fill → Save → overwrite Yes |
| `dialog_handle_open_file` | `handle_id`, `path` | Fill → Open |
| `dialog_handle_messagebox` | `handle_id`, `choice` | `ok` / `cancel` / `yes` / `no` |

### UIA fallback (P1)

| Tool | Args | Description |
|---|---|---|
| `uia_find` | `handle_id`, `control_type?`, `text?` | Find controls |
| `uia_click` | `handle_id`, `control_id` | Click by id |
| `uia_set_text` | `handle_id`, `control_id`, `text` | Set text by id |
| `uia_snapshot` | `handle_id` | Compact control tree JSON |

---

## Architecture / 架构

```
dialog_wait_for / dialog_list
        │
        ▼
 class == #32770 ──yes──▶ semantic fast path (dialogs.py)
        │
        no
        ▼
 UIA fallback (uia_fallback.py) + warning log
```

- Find-window and do-action are separated for mockable unit tests.  
  找窗口与做动作分离，便于单测 mock。
- Timeouts / retries come from env (`WIN_DIALOG_*`), never hard-coded at call sites.  
  超时与重试全部走配置。
- Logs store text **hashes / digests**, not full dialog bodies or file contents.  
  日志只记摘要，不落用户正文。

---

## Safety notes / 安全与限制

1. **Elevation**: If the target dialog runs as Administrator, this process must too. Tools return a clear error instead of failing silently.  
   目标以管理员运行时，本进程也需管理员；错误信息明确，不静默失败。
2. **UAC secure desktop**: Not reachable via UIA — returns unsupported.  
   安全桌面上的对话框不可自动化。
3. **32/64-bit**: Match Python bitness to the target process when possible.  
   尽量与目标进程位数一致。
4. **Password fields**: `dialog_set_text` refuses password controls.  
   密码框拒绝写入。
5. **P0 has no coordinate clicks**: `dialogs.py` must not contain `click_input` / `move_mouse`.  
   P0 层禁止坐标点击。

---

## Development / 开发

```bash
pip install -e ".[dev]"
pytest
pytest -m integration   # real desktop scenarios
ruff check src tests
```

### Acceptance scenarios (manual) / 验收场景

1. Notepad → Ctrl+S → `dialog_wait_for` → `dialog_handle_save_as` → file on disk  
2. MessageBox → `dialog_read_text` → `dialog_handle_messagebox("yes")`  
3. Open dialog → `dialog_handle_open_file`  
4. Repeat on Chinese Windows (aliases `保存` / `确定`)  
5. Custom WPF dialog → `uia_*` + warning log  
6. MCP Inspector lists tools and calls `dialog_list`  
7. `rg "click_input|move_mouse" src/win_dialog_agent/dialogs.py` → zero hits  

---

## Contributing aliases / 贡献别名

The highest-leverage contribution is expanding button labels in  
[`src/win_dialog_agent/aliases.py`](src/win_dialog_agent/aliases.py).  
See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## License

MIT — see [LICENSE](LICENSE).
