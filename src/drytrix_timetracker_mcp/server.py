"""FastMCP server wiring for drytrix-timetracker-mcp."""

from __future__ import annotations

from pathlib import Path

from mcp.server.fastmcp import FastMCP

from . import tools
from .client import TimeTrackerClient
from .config import Settings, load_settings, read_dotenv

READ_TOOL_NAMES = {
    "api_info",
    "whoami",
    "list_projects",
    "list_time_entries",
    "get_hours_summary",
    "hours_by_day",
    "list_clients",
    "list_tasks",
    "search",
    "timer_status",
}


def build_server(settings: Settings, client: TimeTrackerClient | None = None) -> FastMCP:
    """Create the MCP server with the read tools registered."""
    client = client or TimeTrackerClient(settings)
    mcp = FastMCP("drytrix-timetracker-mcp")

    @mcp.tool()
    def api_info() -> dict:
        """Get the TimeTracker API version, timezone, and enabled modules (no auth)."""
        return tools.api_info(client)

    @mcp.tool()
    def whoami() -> dict:
        """Get the user this token authenticates as (needs read:users)."""
        return tools.whoami(client)

    @mcp.tool()
    def list_projects(status: str | None = None, client_id: int | None = None) -> dict:
        """List projects (needs read:projects)."""
        return tools.list_projects(client, status=status, client_id=client_id)

    @mcp.tool()
    def list_time_entries(
        start_date: str | None = None,
        end_date: str | None = None,
        project_id: int | None = None,
        billable: bool | None = None,
    ) -> dict:
        """List time entries in a date range (needs read:time_entries)."""
        return tools.list_time_entries(
            client,
            start_date=start_date,
            end_date=end_date,
            project_id=project_id,
            billable=billable,
        )

    @mcp.tool()
    def get_hours_summary(
        start_date: str, end_date: str, project_id: int | None = None
    ) -> dict:
        """Total and billable hours plus per-project breakdown (needs read:reports)."""
        return tools.get_hours_summary(
            client, start_date, end_date, project_id=project_id
        )

    @mcp.tool()
    def hours_by_day(
        start_date: str, end_date: str, project_id: int | None = None
    ) -> dict:
        """Per-day hours from time entries, the authoritative hours source (needs read:time_entries)."""
        return tools.hours_by_day(client, start_date, end_date, project_id=project_id)

    @mcp.tool()
    def list_clients() -> dict:
        """List clients (needs read:clients)."""
        return tools.list_clients(client)

    @mcp.tool()
    def list_tasks(project_id: int | None = None, status: str | None = None) -> dict:
        """List tasks (needs read:tasks)."""
        return tools.list_tasks(client, project_id=project_id, status=status)

    @mcp.tool()
    def search(q: str, types: str | None = None, limit: int | None = None) -> dict:
        """Search projects, tasks, clients, and entries (needs read:projects)."""
        return tools.search(client, q, types=types, limit=limit)

    @mcp.tool()
    def timer_status() -> dict:
        """Get the active timer for the token's user (needs read:time_entries)."""
        return tools.timer_status(client)

    return mcp


def main() -> None:
    settings = load_settings(dotenv_values=read_dotenv(Path(".env")))
    build_server(settings).run()
