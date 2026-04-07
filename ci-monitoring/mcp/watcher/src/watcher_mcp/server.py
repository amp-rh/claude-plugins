"""Watcher MCP Server - HCP/OPP triage workflows."""

import json
import os
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .clients.jira import JiraClient
from sippy_mcp.client import SippyClient
from .config import WatcherConfig, load_config
from .tools.registry import TOOLS, call_tool

app = Server("watcher")


def format_result(data: Any) -> str:
    """Format data as JSON for output."""
    return json.dumps(data, indent=2, default=str)


def create_clients(config: WatcherConfig) -> tuple[SippyClient, JiraClient]:
    """Create API clients from config."""
    sippy = SippyClient(base_url=config.sippy_url)

    jira_token = os.environ.get("JIRA_PERSONAL_TOKEN", "")
    jira = JiraClient(base_url=config.jira_url, token=jira_token)

    return sippy, jira


# Load config and create clients at module level
_config: WatcherConfig | None = None
_sippy: SippyClient | None = None
_jira: JiraClient | None = None


def _init_globals() -> tuple[WatcherConfig, SippyClient, JiraClient]:
    """Initialize global config and clients."""
    global _config, _sippy, _jira
    if _config is None:
        _config = load_config()
        _sippy, _jira = create_clients(_config)
    return _config, _sippy, _jira


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available watcher tools."""
    return TOOLS


@app.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    config, sippy, jira = _init_globals()

    try:
        result = await call_tool(
            name,
            arguments,
            sippy=sippy,
            jira=jira,
            config=config,
        )
        return [TextContent(type="text", text=format_result(result))]

    except Exception as e:
        error_result = {"error": str(e), "tool": name, "arguments": arguments}
        return [TextContent(type="text", text=format_result(error_result))]


def main() -> None:
    """Run the MCP server."""
    import asyncio

    # Initialize on startup
    _init_globals()

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
