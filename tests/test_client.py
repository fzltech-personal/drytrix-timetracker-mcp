import httpx
import pytest
import respx

from drytrix_timetracker_mcp import client as c
from drytrix_timetracker_mcp.config import Settings

S = Settings(
    base_url="https://time.example.com",
    api_token="tt_secret",
    timeout=30.0,
    verify_ssl=True,
    enable_write=False,
    per_page=100,
)
BASE = "https://time.example.com/api/v1"


def make_client(**kw):
    return c.TimeTrackerClient(S, **kw)


@respx.mock
def test_sends_bearer_and_returns_json():
    route = respx.get(f"{BASE}/time-entries").mock(
        return_value=httpx.Response(
            200, json={"time_entries": [], "pagination": {"has_next": False}}
        )
    )
    out = make_client().get("time-entries")
    assert out == {"time_entries": [], "pagination": {"has_next": False}}
    assert route.calls[0].request.headers["authorization"] == "Bearer tt_secret"


@respx.mock
def test_403_surfaces_scope():
    body = {
        "error": "Insufficient permissions",
        "error_code": "forbidden",
        "message": "requires read:users",
        "required_scope": "read:users",
        "available_scopes": ["read:projects"],
    }
    respx.get(f"{BASE}/users/me").mock(return_value=httpx.Response(403, json=body))
    with pytest.raises(c.TimeTrackerError) as e:
        make_client().get("users/me")
    assert e.value.status == 403 and e.value.required_scope == "read:users"
    assert e.value.available_scopes == ["read:projects"]


@pytest.mark.parametrize("code", [401, 404])
@respx.mock
def test_401_404_clear_messages(code):
    respx.get(f"{BASE}/x").mock(
        return_value=httpx.Response(code, json={"error": "nope", "message": "nope"})
    )
    with pytest.raises(c.TimeTrackerError) as e:
        make_client().get("x")
    assert e.value.status == code


@respx.mock
def test_token_never_in_error():
    respx.get(f"{BASE}/x").mock(return_value=httpx.Response(500, text="boom"))
    with pytest.raises(c.TimeTrackerError) as e:
        make_client().get("x")
    assert "tt_secret" not in str(e.value)


@respx.mock
def test_429_retries_then_succeeds():
    slept = []
    respx.get(f"{BASE}/x").mock(
        side_effect=[
            httpx.Response(429, headers={"Retry-After": "2"}, json={"error": "slow"}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    out = make_client(sleep=slept.append).get("x")
    assert out == {"ok": True} and slept == [2.0]


@respx.mock
def test_paginate_walks_pages():
    respx.get(f"{BASE}/time-entries").mock(
        side_effect=[
            httpx.Response(
                200,
                json={"time_entries": [{"id": 1}], "pagination": {"has_next": True}},
            ),
            httpx.Response(
                200,
                json={"time_entries": [{"id": 2}], "pagination": {"has_next": False}},
            ),
        ]
    )
    ids = [e["id"] for e in make_client().paginate("time-entries", key="time_entries")]
    assert ids == [1, 2]


def test_error_str_includes_available_scopes():
    e = c.TimeTrackerError(
        403,
        "requires read:users",
        error_code="forbidden",
        required_scope="read:users",
        available_scopes=["read:projects", "read:time_entries"],
    )
    s = str(e)
    assert "read:users" in s and "read:projects" in s


def test_error_str_401_hint_and_no_duplication():
    e = c.TimeTrackerError(401, "HTTP 401")
    s = str(e)
    assert "token" in s.lower()
    assert "HTTP 401: HTTP 401" not in s
