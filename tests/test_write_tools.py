from drytrix_timetracker_mcp import tools


class FakeClient:
    def __init__(self):
        self.posts = []

    def post(self, path, json=None, headers=None):
        self.posts.append((path, json, headers or {}))
        return {"ok": True}


def test_start_timer_posts_project():
    fc = FakeClient()
    tools.start_timer(fc, project_id=1)
    assert fc.posts[0][0] == "timer/start" and fc.posts[0][1] == {"project_id": 1}


def test_stop_timer_posts():
    fc = FakeClient()
    tools.stop_timer(fc)
    assert fc.posts[0][0] == "timer/stop"


def test_create_time_entry_sends_idempotency_key():
    fc = FakeClient()
    tools.create_time_entry(fc, project_id=1, start_time="2026-10-14T08:00:00")
    path, payload, headers = fc.posts[0]
    assert path == "time-entries"
    assert payload["project_id"] == 1 and payload["start_time"] == "2026-10-14T08:00:00"
    assert "Idempotency-Key" in headers and headers["Idempotency-Key"]


def test_write_tools_absent_by_default():
    from drytrix_timetracker_mcp.server import registered_tool_names

    assert "start_timer" not in registered_tool_names(enable_write=False)
    assert "start_timer" in registered_tool_names(enable_write=True)
