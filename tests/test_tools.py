import pytest

from drytrix_timetracker_mcp import tools
from drytrix_timetracker_mcp.client import TimeTrackerError


class FakeClient:
    def __init__(self, responses=None):
        self.responses = responses or {}
        self.get_calls = []
        self.pag_calls = []

    def get(self, path, params=None):
        self.get_calls.append((path, params))
        return self.responses.get(path, {})

    def paginate(self, path, params=None, key=None):
        self.pag_calls.append((path, params, key))
        return iter(self.responses.get(path, []))


def _params_for(fc, path):
    return next(params for (p, params) in fc.get_calls if p == path)


def test_get_hours_summary_normalizes_end_of_day():
    fc = FakeClient(
        {"reports/summary": {"summary": {"total_hours": 76.0}}, "users/me": {"id": 2}}
    )
    tools.get_hours_summary(fc, "2026-09-01", "2026-09-30")
    params = _params_for(fc, "reports/summary")
    assert params["start_date"] == "2026-09-01T00:00:00"
    assert params["end_date"] == "2026-09-30T23:59:59"
    assert params["user_id"] == 2


def test_hours_by_day_aggregates():
    fc = FakeClient(
        {
            "users/me": {"id": 2},
            "time-entries": [
                {"start_time": "2026-09-30T08:00:00", "duration_hours": 8.0}
            ],
        }
    )
    out = tools.hours_by_day(fc, "2026-09-01", "2026-09-30")
    assert out["total_hours"] == 8.0 and out["days"][0]["date"] == "2026-09-30"
    assert "note" not in out


def test_current_user_id_returns_none_without_read_users():
    class Denied(FakeClient):
        def get(self, path, params=None):
            raise TimeTrackerError(
                403,
                "requires read:users",
                error_code="forbidden",
                required_scope="read:users",
            )

    assert tools.current_user_id(Denied()) is None


def test_hours_by_day_pins_to_token_user():
    fc = FakeClient({"users/me": {"id": 2}, "time-entries": []})
    tools.hours_by_day(fc, "2026-09-01", "2026-09-30")
    assert fc.pag_calls[-1][1].get("user_id") == 2


def test_hours_by_day_notes_when_user_unresolved():
    class Denied(FakeClient):
        def get(self, path, params=None):
            if path == "users/me":
                raise TimeTrackerError(403, "requires read:users")
            return super().get(path, params)

    fc = Denied({"time-entries": []})
    out = tools.hours_by_day(fc, "2026-09-01", "2026-09-30")
    assert "note" in out


def test_unknown_endpoint_message():
    class Missing(FakeClient):
        def get(self, path, params=None):
            raise TimeTrackerError(404, "Resource not found", error_code="not_found")

    with pytest.raises(TimeTrackerError):
        tools.api_info(Missing())


def test_get_hours_summary_notes_when_user_unresolved():
    class Denied(FakeClient):
        def get(self, path, params=None):
            if path == "users/me":
                raise TimeTrackerError(403, "requires read:users")
            return super().get(path, params)

    fc = Denied({"reports/summary": {"summary": {"total_hours": 76.0}}})
    out = tools.get_hours_summary(fc, "2026-09-01", "2026-09-30")
    assert "note" in out
    assert out["summary"]["total_hours"] == 76.0
