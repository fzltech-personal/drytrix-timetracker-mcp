"""HTTP client for the TimeTracker ``/api/v1`` REST API.

Handles bearer auth, structured errors, pagination, and 429 backoff. The API
token is never interpolated into any message.
"""

from __future__ import annotations

import time
from typing import Any, Callable, Iterator

import httpx

from .config import Settings


class TimeTrackerError(Exception):
    """A non-2xx response from the TimeTracker API."""

    def __init__(
        self,
        status: int,
        message: str,
        *,
        error_code: str | None = None,
        required_scope: str | None = None,
        available_scopes: list[str] | None = None,
        retry_after: float | None = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.message = message
        self.error_code = error_code
        self.required_scope = required_scope
        self.available_scopes = list(available_scopes or [])
        self.retry_after = retry_after

    def __str__(self) -> str:
        parts = [f"HTTP {self.status}: {self.message}"]
        if self.error_code:
            parts.append(f"({self.error_code})")
        if self.required_scope:
            parts.append(f"requires scope '{self.required_scope}'")
        return " ".join(parts)


def _retry_delay(response: httpx.Response) -> float:
    retry_after = response.headers.get("Retry-After")
    if retry_after:
        try:
            return float(retry_after)
        except ValueError:
            pass
    reset = response.headers.get("X-RateLimit-Reset")
    if reset:
        try:
            return max(0.0, float(reset) - time.time())
        except ValueError:
            pass
    return 1.0


class TimeTrackerClient:
    """Thin synchronous wrapper around the REST API."""

    MAX_RETRIES = 2

    def __init__(
        self,
        settings: Settings,
        *,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.settings = settings
        self._sleep = sleep
        self._base_url = settings.base_url.rstrip("/")
        self._client = httpx.Client(
            timeout=settings.timeout,
            verify=settings.verify_ssl,
            transport=transport,
            headers={
                "Authorization": f"Bearer {settings.api_token}",
                "Accept": "application/json",
            },
        )

    def _url(self, path: str) -> str:
        return f"{self._base_url}/api/v1/{path.lstrip('/')}"

    def _request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        url = self._url(path)
        response: httpx.Response | None = None
        for attempt in range(self.MAX_RETRIES + 1):
            response = self._client.request(
                method, url, params=params, json=json, headers=headers
            )
            if response.status_code == 429 and attempt < self.MAX_RETRIES:
                self._sleep(_retry_delay(response))
                continue
            break
        assert response is not None  # loop always assigns
        if response.status_code >= 400:
            raise self._error_from(response)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    @staticmethod
    def _error_from(response: httpx.Response) -> TimeTrackerError:
        body: Any = {}
        try:
            body = response.json()
        except Exception:
            body = {}
        if not isinstance(body, dict):
            body = {}
        message = (
            body.get("message")
            or body.get("error")
            or f"HTTP {response.status_code}"
        )
        return TimeTrackerError(
            response.status_code,
            message,
            error_code=body.get("error_code"),
            required_scope=body.get("required_scope"),
            available_scopes=body.get("available_scopes") or [],
        )

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> Any:
        return self._request("POST", path, json=json, headers=headers)

    def paginate(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        *,
        key: str,
    ) -> Iterator[dict[str, Any]]:
        """Yield every item across pages of a list endpoint.

        ``key`` is the resource-named key in the response (e.g. ``time_entries``).
        """
        query = dict(params or {})
        query.setdefault("per_page", self.settings.per_page)
        page = int(query.get("page", 1))
        while True:
            query["page"] = page
            data = self.get(path, query) or {}
            for item in data.get(key) or []:
                yield item
            pagination = data.get("pagination") or {}
            if not pagination.get("has_next"):
                break
            page += 1
