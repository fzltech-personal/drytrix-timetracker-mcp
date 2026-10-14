import os

import pytest

from drytrix_timetracker_mcp import client as c
from drytrix_timetracker_mcp import tools
from drytrix_timetracker_mcp.config import Settings

pytestmark = pytest.mark.skipif(
    not (os.getenv("TT_BASE_URL") and os.getenv("TIMETRACKER_API_KEY")),
    reason="integration: set TT_BASE_URL and TIMETRACKER_API_KEY",
)


def _client():
    settings = Settings(
        os.environ["TT_BASE_URL"],
        os.environ["TIMETRACKER_API_KEY"],
        30.0,
        True,
        False,
        100,
    )
    return c.TimeTrackerClient(settings)


def test_api_info_reachable():
    assert "api_version" in tools.api_info(_client())


def test_hours_by_day_runs():
    out = tools.hours_by_day(_client(), "2026-09-01", "2026-09-30")
    assert "total_hours" in out and "days" in out
