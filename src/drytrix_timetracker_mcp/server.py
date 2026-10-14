"""MCP server wiring for drytrix-timetracker-mcp."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from . import tools
from .client import TimeTrackerClient, TimeTrackerError
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

WRITE_TOOL_NAMES = {
    "start_timer",
    "stop_timer",
    "pause_timer",
    "resume_timer",
    "create_time_entry",
}


def registered_tool_names(enable_write: bool) -> set[str]:
    """The tool names the server registers for a given write setting."""
    names = set(READ_TOOL_NAMES)
    if enable_write:
        names |= WRITE_TOOL_NAMES
    return names


def _surface(fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
    """Call a tool, re-raising API errors as MCP ``ToolError``.

    Without this, mcp 2.x wraps the exception as a generic
    "Error executing tool <name>" and the 401/403 scope, 404 text, and 429
    detail never reach the client.
    """
    try:
        return fn(*args, **kwargs)
    except TimeTrackerError as exc:
        raise ToolError(str(exc)) from exc


def build_server(settings: Settings, client: TimeTrackerClient | None = None) -> MCPServer:
    """Create the MCP server with the read tools registered."""
    client = client or TimeTrackerClient(settings)
    mcp = MCPServer("drytrix-timetracker-mcp")

    @mcp.tool()
    def api_info() -> dict:
        """Get the TimeTracker API version, timezone, and enabled modules (no auth)."""
        return _surface(tools.api_info, client)

    @mcp.tool()
    def whoami() -> dict:
        """Get the user this token authenticates as (needs read:users)."""
        return _surface(tools.whoami, client)

    @mcp.tool()
    def list_projects(status: str | None = None, client_id: int | None = None) -> dict:
        """List projects (needs read:projects)."""
        return _surface(tools.list_projects, client, status=status, client_id=client_id)

    @mcp.tool()
    def list_time_entries(
        start_date: str | None = None,
        end_date: str | None = None,
        project_id: int | None = None,
        billable: bool | None = None,
        user_id: int | None = None,
        include_active: bool | None = None,
    ) -> dict:
        """List time entries in a date range (needs read:time_entries)."""
        return _surface(
            tools.list_time_entries,
            client,
            start_date=start_date,
            end_date=end_date,
            project_id=project_id,
            billable=billable,
            user_id=user_id,
            include_active=include_active,
        )

    @mcp.tool()
    def get_hours_summary(
        start_date: str,
        end_date: str,
        project_id: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """Total and billable hours plus per-project breakdown (needs read:reports)."""
        return _surface(
            tools.get_hours_summary,
            client,
            start_date,
            end_date,
            project_id=project_id,
            user_id=user_id,
        )

    @mcp.tool()
    def hours_by_day(
        start_date: str,
        end_date: str,
        project_id: int | None = None,
        user_id: int | None = None,
    ) -> dict:
        """Per-day hours from time entries, the authoritative hours source (needs read:time_entries)."""
        return _surface(
            tools.hours_by_day,
            client,
            start_date,
            end_date,
            project_id=project_id,
            user_id=user_id,
        )

    @mcp.tool()
    def list_clients() -> dict:
        """List clients (needs read:clients)."""
        return _surface(tools.list_clients, client)

    @mcp.tool()
    def list_tasks(project_id: int | None = None, status: str | None = None) -> dict:
        """List tasks (needs read:tasks)."""
        return _surface(tools.list_tasks, client, project_id=project_id, status=status)

    @mcp.tool()
    def search(q: str, types: str | None = None, limit: int | None = None) -> dict:
        """Search projects, tasks, clients, and entries (needs read:projects)."""
        return _surface(tools.search, client, q, types=types, limit=limit)

    @mcp.tool()
    def timer_status() -> dict:
        """Get the active timer for the token's user (needs read:time_entries)."""
        return _surface(tools.timer_status, client)

    if settings.enable_write:

        @mcp.tool()
        def start_timer(
            project_id: int | None = None,
            client_id: int | None = None,
            task_id: int | None = None,
        ) -> dict:
            """Start a timer (needs write:time_entries)."""
            return _surface(
                tools.start_timer,
                client,
                project_id=project_id,
                client_id=client_id,
                task_id=task_id,
            )

        @mcp.tool()
        def stop_timer() -> dict:
            """Stop the active timer (needs write:time_entries)."""
            return _surface(tools.stop_timer, client)

        @mcp.tool()
        def pause_timer() -> dict:
            """Pause the active timer (needs write:time_entries)."""
            return _surface(tools.pause_timer, client)

        @mcp.tool()
        def resume_timer() -> dict:
            """Resume a paused timer (needs write:time_entries)."""
            return _surface(tools.resume_timer, client)

        @mcp.tool()
        def create_time_entry(
            project_id: int,
            start_time: str,
            end_time: str | None = None,
            notes: str | None = None,
            tags: str | None = None,
            billable: bool = True,
        ) -> dict:
            """Create a time entry (needs write:time_entries)."""
            return _surface(
                tools.create_time_entry,
                client,
                project_id=project_id,
                start_time=start_time,
                end_time=end_time,
                notes=notes,
                tags=tags,
                billable=billable,
            )

    return mcp


def main() -> None:
    settings = load_settings(dotenv_values=read_dotenv(Path(".env")))
    build_server(settings).run()
