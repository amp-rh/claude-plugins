"""Sippy MCP Server."""

import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client import SippyClient

app = Server("sippy")
client = SippyClient()


def format_result(data: Any) -> str:
    """Format data as JSON for output."""
    return json.dumps(data, indent=2, default=str)


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Sippy tools."""
    return [
        Tool(
            name="sippy_get_releases",
            description="Get list of available OpenShift releases from Sippy with metadata including GA dates and capabilities",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="sippy_get_jobs",
            description="Get all CI jobs for a specific OpenShift release",
            inputSchema={
                "type": "object",
                "properties": {
                    "release": {
                        "type": "string",
                        "description": "Release version (e.g., '4.19', '4.20')",
                    },
                },
                "required": ["release"],
            },
        ),
        Tool(
            name="sippy_get_health",
            description="Get release health indicators (install success, bootstrap, infrastructure, upgrade rates)",
            inputSchema={
                "type": "object",
                "properties": {
                    "release": {
                        "type": "string",
                        "description": "Release version (e.g., '4.19')",
                    },
                },
                "required": ["release"],
            },
        ),
        Tool(
            name="sippy_get_tests",
            description="Get test results for a release, including pass/fail rates and Jira components",
            inputSchema={
                "type": "object",
                "properties": {
                    "release": {
                        "type": "string",
                        "description": "Release version (e.g., '4.19')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of test results (default: 100)",
                        "default": 100,
                    },
                },
                "required": ["release"],
            },
        ),
        Tool(
            name="sippy_search_jobs",
            description="Search for CI jobs with flexible filters (name, variant, pass percentage)",
            inputSchema={
                "type": "object",
                "properties": {
                    "release": {
                        "type": "string",
                        "description": "Release version (e.g., '4.19')",
                    },
                    "name_contains": {
                        "type": "string",
                        "description": "Filter jobs where name contains this string (case-insensitive)",
                    },
                    "variant_contains": {
                        "type": "string",
                        "description": "Filter jobs by variant (e.g., 'Platform:aws', 'Installer:hypershift')",
                    },
                    "min_pass_percentage": {
                        "type": "number",
                        "description": "Minimum pass percentage (0-100)",
                    },
                    "max_pass_percentage": {
                        "type": "number",
                        "description": "Maximum pass percentage (0-100) - useful for finding failing jobs",
                    },
                },
                "required": ["release"],
            },
        ),
        Tool(
            name="sippy_get_hypershift_jobs",
            description="Get ROSA HCP/Hypershift jobs for a release (Installer:hypershift variant)",
            inputSchema={
                "type": "object",
                "properties": {
                    "release": {
                        "type": "string",
                        "description": "Release version (e.g., '4.19')",
                    },
                },
                "required": ["release"],
            },
        ),
        Tool(
            name="sippy_get_failing_jobs",
            description="Get jobs below a pass percentage threshold (default: <90%)",
            inputSchema={
                "type": "object",
                "properties": {
                    "release": {
                        "type": "string",
                        "description": "Release version (e.g., '4.19')",
                    },
                    "max_pass_percentage": {
                        "type": "number",
                        "description": "Maximum pass percentage to include (default: 90)",
                        "default": 90,
                    },
                },
                "required": ["release"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "sippy_get_releases":
            result = client.get_releases()
        elif name == "sippy_get_jobs":
            result = client.get_jobs(arguments["release"])
        elif name == "sippy_get_health":
            result = client.get_health(arguments["release"])
        elif name == "sippy_get_tests":
            result = client.get_tests(
                arguments["release"],
                limit=arguments.get("limit", 100),
            )
        elif name == "sippy_search_jobs":
            result = client.search_jobs(
                arguments["release"],
                name_contains=arguments.get("name_contains"),
                variant_contains=arguments.get("variant_contains"),
                min_pass_percentage=arguments.get("min_pass_percentage"),
                max_pass_percentage=arguments.get("max_pass_percentage"),
            )
        elif name == "sippy_get_hypershift_jobs":
            result = client.get_hypershift_jobs(arguments["release"])
        elif name == "sippy_get_failing_jobs":
            result = client.get_failing_jobs(
                arguments["release"],
                max_pass_percentage=arguments.get("max_pass_percentage", 90),
            )
        else:
            raise ValueError(f"Unknown tool: {name}")

        return [TextContent(type="text", text=format_result(result))]

    except Exception as e:
        return [TextContent(type="text", text=f"Error: {e!s}")]


def main() -> None:
    """Run the MCP server."""
    import asyncio

    async def run():
        async with stdio_server() as (read_stream, write_stream):
            await app.run(read_stream, write_stream, app.create_initialization_options())

    asyncio.run(run())


if __name__ == "__main__":
    main()
