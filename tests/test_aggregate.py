from drytrix_timetracker_mcp import aggregate


def test_normalize_range_date_only():
    assert aggregate.normalize_range("2026-09-01", "2026-09-30") == (
        "2026-09-01T00:00:00",
        "2026-09-30T23:59:59",
    )


def test_normalize_range_passthrough_and_none():
    assert aggregate.normalize_range(None, None) == (None, None)
    assert aggregate.normalize_range("2026-09-01T05:00:00", None) == (
        "2026-09-01T05:00:00",
        None,
    )


def test_group_hours_by_day_basic():
    entries = [
        {"start_time": "2026-09-02T08:00:00", "duration_hours": 8.0},
        {"start_time": "2026-09-02T13:00:00", "duration_hours": 4.0},
        {"start_time": "2026-09-30T08:00:00", "duration_hours": 8.0},
    ]
    out = aggregate.group_hours_by_day(entries, tz="Europe/Amsterdam")
    assert out["total_hours"] == 20.0 and out["total_entries"] == 3
    assert out["days"][0] == {"date": "2026-09-02", "hours": 12.0, "entries": 2}
    assert out["days"][-1] == {"date": "2026-09-30", "hours": 8.0, "entries": 1}


def test_group_hours_empty():
    assert aggregate.group_hours_by_day([], tz="UTC") == {
        "timezone": "UTC",
        "days": [],
        "total_hours": 0.0,
        "total_entries": 0,
    }


def test_group_hours_skips_active_entries_without_duration():
    entries = [{"start_time": "2026-09-02T08:00:00", "duration_hours": None}]
    assert aggregate.group_hours_by_day(entries, tz="UTC")["total_hours"] == 0.0
