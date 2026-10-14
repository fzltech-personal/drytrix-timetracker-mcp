"""Boundary tests: errors must reach the MCP client with their detail intact.

In mcp 2.x, a raised non-ToolError is wrapped as a generic
"Error executing tool <name>", which would drop the 403 scope and 404 text.
"""

import asyncio
import inspect

from drytrix_timetracker_mcp.client import TimeTrackerError
from drytrix_timetracker_mcp.config import Settings
from drytrix_timetracker_mcp.server import build_server

SETTINGS = Settings("https://time.example.com", "tt_x", 30.0, True, False, 100)


def _call(server, name, args):
    """Return whatever text the MCP client would see, raised or returned."""
    try:
        out = server.call_tool(name, args)
        if inspect.isawaitable(out):
            out = asyncio.run(out)
    except Exception as exc:  # noqa: BLE001 - the error text is the assertion target
        return str(exc)
    content = getattr(out, "content", out)
    try:
        return " ".join(getattr(part, "text", str(part)) for part in content)
    except TypeError:
        return str(out)


class DeniedClient:
    def get(self, path, params=None):
        raise TimeTrackerError(
            403,
            'This endpoint requires one of: "read:users"',
            error_code="forbidden",
            required_scope="read:users",
            available_scopes=["read:projects", "read:time_entries"],
        )


class MissingClient:
    def get(self, path, params=None):
        raise TimeTrackerError(404, "Resource not found", error_code="not_found")


class RecordingClient:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.calls = []

    def get(self, path, params=None):
        self.calls.append((path, params))
        return self.responses.get(path, {})

    def paginate(self, path, params=None, key=None):
        self.calls.append((path, params))
        return iter(())


def test_mcp_tool_surfaces_scope_error():
    text = _call(build_server(SETTINGS, client=DeniedClient()), "whoami", {})
    assert "read:users" in text


def test_mcp_tool_surfaces_404():
    text = _call(build_server(SETTINGS, client=MissingClient()), "api_info", {})
    assert "404" in text and "Resource not found" in text


def test_list_time_entries_forwards_user_id_and_include_active():
    rec = RecordingClient()
    _call(
        build_server(SETTINGS, client=rec),
        "list_time_entries",
        {"user_id": 7, "include_active": True},
    )
    params = [p for (path, p) in rec.calls if path == "time-entries"][-1]
    assert params.get("user_id") == 7
    assert params.get("include_active") is True


def test_get_hours_summary_forwards_user_id():
    rec = RecordingClient({"reports/summary": {"summary": {}}})
    _call(
        build_server(SETTINGS, client=rec),
        "get_hours_summary",
        {"start_date": "2026-09-01", "end_date": "2026-09-30", "user_id": 7},
    )
    params = [p for (path, p) in rec.calls if path == "reports/summary"][-1]
    assert params.get("user_id") == 7
