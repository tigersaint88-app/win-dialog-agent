"""MCP stdio server entry / MCP stdio 入口.

Same tool functions as Agents SDK wrappers, exposed via the official ``mcp`` package.
与 Agents SDK 共用同一批底层函数，通过 MCP stdio 对外发布。

Run / 启动::

    win-dialog-mcp
    # or
    python -m win_dialog_agent.server
    # or (uvx after publish)
    uvx win-dialog-agent
"""

from __future__ import annotations

import json
import logging
import sys
from typing import Any, Callable

from win_dialog_agent import dialogs, uia_fallback
from win_dialog_agent.config import get_settings
from win_dialog_agent.logging_utils import get_logger

logger = get_logger(__name__)


def _json(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def _create_mcp_app() -> Any:
    """Create FastMCP / MCPServer app with compatibility across mcp SDK versions."""
    settings = get_settings()
    logging.getLogger("win_dialog_agent").setLevel(settings.log_level.upper())

    instructions = (
        "Semantic Windows dialog automation for AI agents. "
        "Use dialog_* tools for standard #32770 dialogs; "
        "use uia_* tools for non-standard (WPF/WinUI/Electron) dialogs. "
        "Windows only."
    )

    # mcp SDK v2: MCPServer; v1: FastMCP (renamed — see MCP migration guide).
    server: Any = None
    try:
        from mcp.server import MCPServer  # type: ignore[attr-defined]

        try:
            server = MCPServer(
                "win-dialog-agent",
                version="0.1.0",
                instructions=instructions,
            )
        except TypeError:
            server = MCPServer("win-dialog-agent")
    except ImportError:
        server = None

    if server is None:
        try:
            from mcp.server.fastmcp import FastMCP

            try:
                server = FastMCP("win-dialog-agent", instructions=instructions)
            except TypeError:
                server = FastMCP("win-dialog-agent")
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "The 'mcp' package is required. Install with: pip install 'mcp>=1.6'"
            ) from exc

    def _tool(fn: Callable[..., Any]) -> Callable[..., Any]:
        """Register tool; support both ``@mcp.tool`` and ``@mcp.tool()`` styles."""
        deco = server.tool
        try:
            return deco()(fn)  # type: ignore[misc]
        except TypeError:
            return deco(fn)  # type: ignore[misc]

    @_tool
    def dialog_wait_for(
        title: str | None = None,
        class_name: str | None = None,
        timeout: float | None = None,
    ) -> str:
        """Wait for a Windows dialog and return handle info JSON."""
        info = dialogs.dialog_wait_for(title=title, class_name=class_name, timeout=timeout)
        return _json(info.to_dict())

    @_tool
    def dialog_list() -> str:
        """List visible top-level standard #32770 dialogs."""
        return _json([d.to_dict() for d in dialogs.dialog_list()])

    @_tool
    def dialog_describe(handle_id: str) -> str:
        """Return a control-tree summary for the dialog."""
        return _json(dialogs.dialog_describe(handle_id))

    @_tool
    def dialog_read_text(handle_id: str) -> str:
        """Read static / message text from the dialog."""
        return dialogs.dialog_read_text(handle_id)

    @_tool
    def dialog_click_button(handle_id: str, label: str) -> str:
        """Click a button by zh/en label or semantic key (save/ok/yes/...)."""
        return dialogs.dialog_click_button(handle_id, label)

    @_tool
    def dialog_set_text(handle_id: str, text: str, field: str | None = None) -> str:
        """Fill an edit field; refuses password controls."""
        return dialogs.dialog_set_text(handle_id, text, field=field)

    @_tool
    def dialog_handle_save_as(handle_id: str, path: str) -> str:
        """Save As: fill path, click Save, auto-confirm overwrite."""
        return dialogs.dialog_handle_save_as(handle_id, path)

    @_tool
    def dialog_handle_open_file(handle_id: str, path: str) -> str:
        """Open File: fill path and click Open."""
        return dialogs.dialog_handle_open_file(handle_id, path)

    @_tool
    def dialog_handle_messagebox(handle_id: str, choice: str) -> str:
        """Message box: return body text and click ok/cancel/yes/no."""
        return _json(dialogs.dialog_handle_messagebox(handle_id, choice))

    @_tool
    def uia_find(
        handle_id: str,
        control_type: str | None = None,
        text: str | None = None,
    ) -> str:
        """UIA fallback: find controls by type/text inside the dialog."""
        return _json(
            uia_fallback.uia_find(handle_id, control_type=control_type, text=text)
        )

    @_tool
    def uia_click(handle_id: str, control_id: str) -> str:
        """UIA fallback: click control by control_id."""
        return uia_fallback.uia_click(handle_id, control_id)

    @_tool
    def uia_set_text(handle_id: str, control_id: str, text: str) -> str:
        """UIA fallback: set text on control by control_id."""
        return uia_fallback.uia_set_text(handle_id, control_id, text)

    @_tool
    def uia_snapshot(handle_id: str) -> str:
        """UIA fallback: compact control tree JSON for unknown dialogs."""
        return _json(uia_fallback.uia_snapshot(handle_id))

    return server


def main() -> None:
    """CLI entry: run MCP server over stdio."""
    if sys.platform != "win32":
        logger.error("win-dialog-agent requires Windows / 本模块仅支持 Windows")
        raise SystemExit(1)

    app = _create_mcp_app()
    logger.info("Starting win-dialog-agent MCP server (stdio)")
    # Both FastMCP and MCPServer expose run(); default transport is stdio.
    run = getattr(app, "run", None)
    if run is None:  # pragma: no cover
        raise RuntimeError("MCP app has no run() method")
    try:
        run(transport="stdio")
    except TypeError:
        run()


if __name__ == "__main__":
    main()
