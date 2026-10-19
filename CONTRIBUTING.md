# Contributing / 贡献指南

Thanks for helping make Windows dialog automation more reliable for AI agents.  
感谢你帮助把 AI Agent 的 Windows 对话框自动化做得更稳。

## Highest-impact PRs: aliases / 最有价值的 PR：别名表

Edit [`src/win_dialog_agent/aliases.py`](src/win_dialog_agent/aliases.py):

1. Add the **exact** caption you saw (including `(&S)` if present).  
   加上你见到的**完整**按钮文案（含快捷键标记也没关系）。
2. Put it in the correct semantic group (`save`, `open`, `ok`, …).  
   放进正确的语义分组。
3. Add a unit test in `tests/test_aliases.py` if the matching rule is non-obvious.  
   若匹配规则不直观，补一条单测。

Example:

```python
"save": [
    "保存",
    "Save",
    "저장",          # new locale you verified
    "Save(&S)",
],
```

## Code changes / 改代码

- Keep the module **independent** — do not import other packages from this monorepo.  
  保持模块独立，不要 import 本仓库其他工程代码。
- P0 (`dialogs.py`): **no** `click_input` / `move_mouse`.  
  P0 禁止坐标点击。
- Separate find-window from do-action so tests can mock the backend.  
  找窗口与做动作分离。
- Do not log full dialog bodies or file contents — use digests.  
  日志不要写完整正文或文件内容。

## Dev setup

```bash
pip install -e ".[dev]"
pytest
ruff check src tests
```

## PR checklist

- [ ] Tests pass (`pytest`)
- [ ] New public tools have English docstrings (model-facing)
- [ ] CHANGELOG.md updated under `[Unreleased]` or next version
- [ ] No secrets / `.env` committed
