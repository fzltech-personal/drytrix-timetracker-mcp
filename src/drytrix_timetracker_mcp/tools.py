"""Tool implementations: thin wrappers over the REST API returning dicts.

Each function takes a client as its first argument so it can be driven by the
real ``TimeTrackerClient`` or a stub in tests.
"""

from __future__ import annotations

from typing import Any

from . import aggregate
from .client import TimeTrackerError


def api_info(client: Any) -> dict:
    """API version, timezone, and enabled modules (no auth required)."""
    return client.get("info")


def whoami(client: Any) -> dict:
    """The user the token authenticates as (requires ``read:users``)."""
    return client.get("users/me")


def current_user_id(client: Any) -> int | None:
    """Resolve the token's user id, or ``None`` when the scope is missing."""
    try:
        me = client.get("users/me") or {}
    except TimeTrackerError as exc:
        if exc.status in (401, 403):
            return None
        raise
    return me.get("id")


def instance_timezone(client: Any) -> str:
    """Instance timezone from ``/info``; ``UTC`` if unavailable."""
    try:
        info = client.get("info") or {}
    except TimeTrackerError:
        return "UTC"
    return info.get("timezone") or "UTC"


def list_projects(
    client: Any,
    status: str | None = None,
    client_id: int | None = None,
    page: int = 1,
    per_page: int | None = None,
) -> dict:
    params: dict[str, Any] = {"page": page}
    if status:
        params["status"] = status
    if client_id is not None:
        params["client_id"] = client_id
    if per_page:
        params["per_page"] = per_page
    return client.get("projects", params)


def list_time_entries(
    client: Any,
    start_date: str | None = None,
    end_date: str | None = None,
    project_id: int | None = None,
    billable: bool | None = None,
    user_id: int | None = None,
) -> dict:
    start, end = aggregate.normalize_range(start_date, end_date)
    params: dict[str, Any] = {}
    if start:
        params["start_date"] = start
    if end:
        params["end_date"] = end
    if project_id is not None:
        params["project_id"] = project_id
    if billable is not None:
        params["billable"] = billable
    if user_id is not None:
        params["user_id"] = user_id
    entries = list(client.paginate("time-entries", params, key="time_entries"))
    return {"time_entries": entries}


def _aggregate_params(
    client: Any,
    start_date: str,
    end_date: str,
    project_id: int | None,
    user_id: int | None,
) -> tuple[dict[str, Any], int | None]:
    start, end = aggregate.normalize_range(start_date, end_date)
    params: dict[str, Any] = {"start_date": start, "end_date": end}
    if project_id is not None:
        params["project_id"] = project_id
    resolved = user_id if user_id is not None else current_user_id(client)
    if resolved is not None:
        params["user_id"] = resolved
    return params, resolved


def get_hours_summary(
    client: Any,
    start_date: str,
    end_date: str,
    project_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    """Total/billable hours and per-project breakdown (requires ``read:reports``)."""
    params, _ = _aggregate_params(client, start_date, end_date, project_id, user_id)
    return client.get("reports/summary", params)


def hours_by_day(
    client: Any,
    start_date: str,
    end_date: str,
    project_id: int | None = None,
    user_id: int | None = None,
    tz: str | None = None,
) -> dict:
    """Per-day hours from time entries; the authoritative hours source."""
    params, resolved = _aggregate_params(client, start_date, end_date, project_id, user_id)
    entries = list(client.paginate("time-entries", params, key="time_entries"))
    timezone = tz or instance_timezone(client)
    result = aggregate.group_hours_by_day(entries, tz=timezone)
    if resolved is None:
        result["note"] = (
            "the token's user could not be resolved (missing read:users scope); "
            "results may span multiple users"
        )
    return result


def list_clients(client: Any) -> dict:
    """List clients (requires ``read:clients``)."""
    return client.get("clients")


def list_tasks(
    client: Any, project_id: int | None = None, status: str | None = None
) -> dict:
    """List tasks (requires ``read:tasks``)."""
    params: dict[str, Any] = {}
    if project_id is not None:
        params["project_id"] = project_id
    if status:
        params["status"] = status
    return client.get("tasks", params)


def search(
    client: Any, q: str, types: str | None = None, limit: int | None = None
) -> dict:
    """Global search (requires ``read:projects``)."""
    params: dict[str, Any] = {"q": q}
    if types:
        params["types"] = types
    if limit is not None:
        params["limit"] = limit
    return client.get("search", params)


def timer_status(client: Any) -> dict:
    """The active timer for the token's user (requires ``read:time_entries``)."""
    return client.get("timer/status")
