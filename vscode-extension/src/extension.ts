import * as vscode from "vscode";

const PROVIDER_ID = "forgecopilot.win-dialog-agent";
const SERVER_LABEL = "win-dialog-agent";
const SERVER_VERSION = "0.1.0";

export function activate(context: vscode.ExtensionContext): void {
  const didChangeEmitter = new vscode.EventEmitter<void>();

  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("winDialogAgent")) {
        didChangeEmitter.fire();
      }
    }),
  );

  context.subscriptions.push(
    vscode.lm.registerMcpServerDefinitionProvider(PROVIDER_ID, {
      onDidChangeMcpServerDefinitions: didChangeEmitter.event,
      provideMcpServerDefinitions: async () => {
        const cfg = vscode.workspace.getConfiguration("winDialogAgent");
        const command = cfg.get<string>("launchCommand", "uvx");
        const args = cfg.get<string[]>("launchArgs", [
          "--from",
          "git+https://github.com/tigersaint88-app/win-dialog-agent",
          "win-dialog-mcp",
        ]);

        return [
          new vscode.McpStdioServerDefinition(
            SERVER_LABEL,
            command,
            args,
            {
              // Hint for operators / logs; server itself is Windows-only.
              WIN_DIALOG_LOG_LEVEL: "INFO",
            },
            SERVER_VERSION,
          ),
        ];
      },
      resolveMcpServerDefinition: async (server) => {
        if (process.platform !== "win32") {
          void vscode.window.showErrorMessage(
            "Win Dialog Agent requires Windows 10/11. This MCP server cannot start on this OS.",
          );
          return undefined;
        }
        return server;
      },
    }),
  );
}

export function deactivate(): void {
  // no-op
}
