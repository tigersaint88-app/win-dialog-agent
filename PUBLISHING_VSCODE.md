# Publish to VS Code Extension Marketplace (path C)

**Publisher display name:** ForgeCopilot LLC  
**Publisher ID (immutable):** `forgecopilot`  
**Extension ID:** `forgecopilot.win-dialog-agent`

## 1. Create Marketplace publisher

1. Open https://marketplace.visualstudio.com/manage  
2. Sign in with a Microsoft account  
3. **Create publisher**
   - **ID:** `forgecopilot` (cannot change later)
   - **Name:** `ForgeCopilot LLC`
4. Create an Azure DevOps [Personal Access Token](https://code.visualstudio.com/api/working-with-extensions/publishing-extension#get-a-personal-access-token)
   - Organization: **All accessible organizations**
   - Scope: **Marketplace → Manage**

## 2. Login & publish

```bash
cd vscode-extension
npm install
npm run compile
npx vsce login forgecopilot
# paste PAT when prompted
npx vsce publish
```

Or package only:

```bash
npx vsce package
# upload the .vsix from https://marketplace.visualstudio.com/manage
```

## 3. Verify

- Listing: `https://marketplace.visualstudio.com/items?itemName=forgecopilot.win-dialog-agent`
- In VS Code: Extensions → search “Win Dialog Agent”
- Chat / Agent mode: MCP tools from `win-dialog-agent` appear after install

## Notes

- Extension only **registers** the MCP server; runtime is started with `uvx` from GitHub (or your settings override).
- Target OS is Windows; non-Windows hosts get an error on server resolve.
