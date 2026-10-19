# Win Dialog Agent (VS Code)

**Publisher:** ForgeCopilot LLC

Semantic Windows dialog automation for AI agents. Registers an MCP stdio server so VS Code Agent / Chat can operate standard `#32770` dialogs (Save As, Open, MessageBox) without coordinate clicks.

## Requirements

- Windows 10 / 11
- VS Code `1.101+` (MCP server definition provider API)
- [`uv`](https://docs.astral.sh/uv/) on `PATH` (`uvx`), **or** change settings to use a local Python install

## Install (Marketplace)

Search **Win Dialog Agent** by **ForgeCopilot** in the Extensions view, or:

```bash
code --install-extension forgecopilot.win-dialog-agent
```

## Install (VSIX / local)

```bash
cd vscode-extension
npm install
npm run package
code --install-extension win-dialog-agent-0.1.0.vsix
```

## Settings

| Setting | Default | Meaning |
|---|---|---|
| `winDialogAgent.launchCommand` | `uvx` | Process used to start MCP |
| `winDialogAgent.launchArgs` | `--from git+https://github.com/tigersaint88-app/win-dialog-agent win-dialog-mcp` | Args for stdio MCP |

Local editable install example:

```json
{
  "winDialogAgent.launchCommand": "python",
  "winDialogAgent.launchArgs": ["-m", "win_dialog_agent.server"]
}
```

## Publish (maintainers)

See [PUBLISHING_VSCODE.md](../PUBLISHING_VSCODE.md).

## License

MIT © ForgeCopilot LLC
