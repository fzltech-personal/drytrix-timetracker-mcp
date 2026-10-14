import json
import pathlib

from drytrix_timetracker_mcp import aggregate

FIX = pathlib.Path(__file__).parent / "fixtures"


def test_time_entries_fixture_aggregates():
    data = json.loads((FIX / "time_entries_page1.json").read_text())
    out = aggregate.group_hours_by_day(data["time_entries"], tz="Europe/Amsterdam")
    assert out["total_entries"] == len(data["time_entries"])


def test_projects_fixture_shape():
    data = json.loads((FIX / "projects.json").read_text())
    assert {"id", "name", "status"} <= set(data["projects"][0])


def test_summary_fixture_shape():
    data = json.loads((FIX / "summary.json").read_text())
    assert {"total_hours", "total_entries"} <= set(data["summary"])


def test_users_me_forbidden_fixture_shape():
    data = json.loads((FIX / "users_me_forbidden.json").read_text())
    assert data["status"] == 403 and data["required_scope"] == "read:users"
