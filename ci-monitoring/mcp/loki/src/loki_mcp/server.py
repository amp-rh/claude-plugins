"""Loki MCP Server for CI log analysis."""

import json
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from .client import LokiClient
from . import queries

app = Server("loki")
client = LokiClient()


def format_result(data: Any) -> str:
    """Format data as JSON for output."""
    return json.dumps(data, indent=2, default=str)


def simplify_log_result(result: dict[str, Any], max_entries: int = 50) -> dict[str, Any]:
    """Simplify Loki result for readable output.

    Extracts log lines from the nested Loki response format.
    """
    if result.get("status") != "success":
        return result

    data = result.get("data", {})
    result_type = data.get("resultType", "")

    if result_type == "streams":
        # Extract log entries from streams
        streams = data.get("result", [])
        entries = []
        for stream in streams:
            labels = stream.get("stream", {})
            job = labels.get("job", "unknown")
            for value in stream.get("values", []):
                timestamp, line = value[0], value[1]
                entries.append({
                    "timestamp": timestamp,
                    "job": job,
                    "line": line[:500] if len(line) > 500 else line,  # Truncate long lines
                })
                if len(entries) >= max_entries:
                    break
            if len(entries) >= max_entries:
                break

        return {
            "status": "success",
            "total_streams": len(streams),
            "entries_shown": len(entries),
            "entries": entries,
        }

    return result


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Loki tools."""
    return [
        Tool(
            name="loki_query",
            description="Execute a raw LogQL query against Loki CI logs",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "LogQL query string (e.g., '{job=~\".*\"} |~ \"error\"')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum entries to return (default: 100)",
                        "default": 100,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="loki_query_range",
            description="Execute a LogQL query with time range for CI logs",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "LogQL query string",
                    },
                    "start": {
                        "type": "string",
                        "description": "Start time (RFC3339, e.g., '2024-01-01T00:00:00Z' or relative like '-24h')",
                    },
                    "end": {
                        "type": "string",
                        "description": "End time (RFC3339 or relative). Default: now",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum entries to return (default: 100)",
                        "default": 100,
                    },
                },
                "required": ["query"],
            },
        ),
        Tool(
            name="loki_labels",
            description="List available labels in Loki (useful for exploring what's indexed)",
            inputSchema={
                "type": "object",
                "properties": {},
            },
        ),
        Tool(
            name="loki_label_values",
            description="Get values for a specific label (e.g., get all job names)",
            inputSchema={
                "type": "object",
                "properties": {
                    "label": {
                        "type": "string",
                        "description": "Label name (e.g., 'job', 'namespace')",
                    },
                },
                "required": ["label"],
            },
        ),
        Tool(
            name="loki_aws_quota_errors",
            description="Find AWS quota/limit exceeded errors in CI logs (VPC, EC2, EBS limits)",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_filter": {
                        "type": "string",
                        "description": "Optional job name filter regex (e.g., 'lp-interop|konflux')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum entries to return (default: 50)",
                        "default": 50,
                    },
                    "mpiit_scope": {
                        "type": "boolean",
                        "description": "If true, filter to MPIIT jobs only (lp-interop, konflux, etc.)",
                        "default": False,
                    },
                },
            },
        ),
        Tool(
            name="loki_vpc_limit_errors",
            description="Find VPC-specific limit errors (VpcLimitExceeded, subnet, security group limits)",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_filter": {
                        "type": "string",
                        "description": "Optional job name filter regex",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum entries to return (default: 50)",
                        "default": 50,
                    },
                },
            },
        ),
        Tool(
            name="loki_orphaned_vpcs",
            description="Find deprovision failures that may leave orphaned VPCs (cleanup errors)",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_filter": {
                        "type": "string",
                        "description": "Optional job name filter regex",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum entries to return (default: 50)",
                        "default": 50,
                    },
                },
            },
        ),
        Tool(
            name="loki_node_availability",
            description="Find node availability issues (insufficient capacity, worker not ready)",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_filter": {
                        "type": "string",
                        "description": "Optional job name filter regex",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum entries to return (default: 50)",
                        "default": 50,
                    },
                },
            },
        ),
        Tool(
            name="loki_ipi_install_failures",
            description="Find IPI install failures related to VPC/network issues",
            inputSchema={
                "type": "object",
                "properties": {
                    "job_filter": {
                        "type": "string",
                        "description": "Optional job name filter regex",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum entries to return (default: 50)",
                        "default": 50,
                    },
                },
            },
        ),
        Tool(
            name="loki_mpiit_failures",
            description="Find all failures in MPIIT-scoped jobs (lp-interop, rosa-hypershift, konflux, interop-opp)",
            inputSchema={
                "type": "object",
                "properties": {
                    "error_pattern": {
                        "type": "string",
                        "description": "Optional error pattern to filter (e.g., 'VpcLimitExceeded')",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum entries to return (default: 50)",
                        "default": 50,
                    },
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Handle tool calls."""
    try:
        if name == "loki_query":
            result = client.query(
                arguments["query"],
                limit=arguments.get("limit", 100),
            )
            result = simplify_log_result(result)

        elif name == "loki_query_range":
            result = client.query_range(
                arguments["query"],
                start=arguments.get("start"),
                end=arguments.get("end"),
                limit=arguments.get("limit", 100),
            )
            result = simplify_log_result(result)

        elif name == "loki_labels":
            result = client.labels()

        elif name == "loki_label_values":
            result = client.label_values(arguments["label"])

        elif name == "loki_aws_quota_errors":
            if arguments.get("mpiit_scope"):
                query = queries.get_mpiit_scoped_query(queries.AWS_QUOTA_ERRORS)
            else:
                query = queries.build_scoped_query(
                    queries.AWS_QUOTA_ERRORS,
                    arguments.get("job_filter"),
                )
            result = client.query(query, limit=arguments.get("limit", 50))
            result = simplify_log_result(result, max_entries=arguments.get("limit", 50))

        elif name == "loki_vpc_limit_errors":
            query = queries.build_scoped_query(
                queries.VPC_LIMIT_ERRORS,
                arguments.get("job_filter"),
            )
            result = client.query(query, limit=arguments.get("limit", 50))
            result = simplify_log_result(result, max_entries=arguments.get("limit", 50))

        elif name == "loki_orphaned_vpcs":
            query = queries.build_scoped_query(
                queries.ORPHANED_VPC_PATTERNS,
                arguments.get("job_filter"),
            )
            result = client.query(query, limit=arguments.get("limit", 50))
            result = simplify_log_result(result, max_entries=arguments.get("limit", 50))

        elif name == "loki_node_availability":
            query = queries.build_scoped_query(
                queries.NODE_AVAILABILITY,
                arguments.get("job_filter"),
            )
            result = client.query(query, limit=arguments.get("limit", 50))
            result = simplify_log_result(result, max_entries=arguments.get("limit", 50))

        elif name == "loki_ipi_install_failures":
            query = queries.build_scoped_query(
                queries.IPI_INSTALL_FAILURES,
                arguments.get("job_filter"),
            )
            result = client.query(query, limit=arguments.get("limit", 50))
            result = simplify_log_result(result, max_entries=arguments.get("limit", 50))

        elif name == "loki_mpiit_failures":
            base_query = queries.MPIIT_JOB_FILTER
            error_pattern = arguments.get("error_pattern")
            if error_pattern:
                # Add error pattern filter
                base_query = base_query.strip() + f' |~ "{error_pattern}"'
            else:
                # Just look for any errors
                base_query = base_query.strip() + ' |= "error"'

            result = client.query(base_query, limit=arguments.get("limit", 50))
            result = simplify_log_result(result, max_entries=arguments.get("limit", 50))

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
