"""Date-range normalization and per-day hours aggregation.

The day bucket is the instance timezone (from ``GET /api/v1/info``).
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable
from zoneinfo import ZoneInfo


def normalize_range(
    start_date: str | None, end_date: str | None
) -> tuple[str | None, str | None]:
    """Expand date-only bounds to explicit start/end-of-day.

    ``/reports/summary`` treats a date-only ``end_date`` as midnight, which
    silently drops the final day; expanding to ``23:59:59`` avoids that. Values
    that already carry a time are returned unchanged.
    """

    def _norm(value: str | None, *, end: bool) -> str | None:
        if value is None or value == "":
            return None
        if "T" in value or " " in value:
            return value
        return f"{value}T{'23:59:59' if end else '00:00:00'}"

    return _norm(start_date, end=False), _norm(end_date, end=True)


def group_hours_by_day(entries: Iterable[dict[str, Any]], tz: str) -> dict[str, Any]:
    """Group entries by local calendar day of their ``start_time``.

    Entries without ``duration_hours`` (running timers) are skipped.
    """
    try:
        zone = ZoneInfo(tz)
    except Exception as exc:  # noqa: BLE001 - surface any tzdata failure clearly
        raise ValueError(f"unknown timezone: {tz!r}") from exc

    buckets: dict[str, dict[str, Any]] = {}
    total_hours = 0.0
    total_entries = 0

    for entry in entries:
        hours = entry.get("duration_hours")
        start = entry.get("start_time")
        if hours is None or not start:
            continue
        moment = datetime.fromisoformat(start)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=zone)
        else:
            moment = moment.astimezone(zone)
        day = moment.date().isoformat()
        bucket = buckets.setdefault(day, {"date": day, "hours": 0.0, "entries": 0})
        bucket["hours"] += float(hours)
        bucket["entries"] += 1
        total_hours += float(hours)
        total_entries += 1

    return {
        "timezone": tz,
        "days": [buckets[key] for key in sorted(buckets)],
        "total_hours": total_hours,
        "total_entries": total_entries,
    }
