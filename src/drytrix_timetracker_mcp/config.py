"""Configuration: environment variables plus an optional local ``.env`` file.

Resolution order per key: real environment -> ``.env`` values -> default.
The API token is never logged.
"""

from __future__ import annotations

import os
import pathlib
from dataclasses import dataclass
from typing import Mapping

TRUTHY = {"1", "true", "yes", "on"}

# Accepted token variable names, in precedence order.
TOKEN_KEYS = ("TIMETRACKER_API_KEY", "TT_API_TOKEN")


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True)
class Settings:
    base_url: str
    api_token: str
    timeout: float = 30.0
    verify_ssl: bool = True
    enable_write: bool = False
    per_page: int = 100


def read_dotenv(path: pathlib.Path) -> dict[str, str]:
    """Parse a ``KEY=VALUE`` file. Blank lines and ``#`` comments are ignored.

    Surrounding single or double quotes are stripped. A missing file yields {}.
    """
    path = pathlib.Path(path)
    if not path.is_file():
        return {}
    values: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            continue
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        values[key] = value
    return values


def _resolve(
    environ: Mapping[str, str],
    dotenv_values: Mapping[str, str],
    key: str,
) -> str | None:
    if key in environ:
        return environ[key]
    return dotenv_values.get(key)


def _truthy(value: str) -> bool:
    return value.strip().lower() in TRUTHY


def load_settings(
    environ: Mapping[str, str] | None = None,
    dotenv_values: Mapping[str, str] | None = None,
) -> Settings:
    environ = os.environ if environ is None else environ
    dotenv_values = {} if dotenv_values is None else dotenv_values

    base_url = _resolve(environ, dotenv_values, "TT_BASE_URL")
    if not base_url:
        raise ConfigError("TT_BASE_URL is required (e.g. https://time.example.com)")

    api_token = ""
    for key in TOKEN_KEYS:
        found = _resolve(environ, dotenv_values, key)
        if found:
            api_token = found
            break
    if not api_token:
        raise ConfigError(
            "an API token is required: set TIMETRACKER_API_KEY (or TT_API_TOKEN)"
        )

    timeout = float(_resolve(environ, dotenv_values, "TT_TIMEOUT") or 30.0)
    verify_ssl = _truthy(_resolve(environ, dotenv_values, "TT_VERIFY_SSL") or "true")
    enable_write = _truthy(
        _resolve(environ, dotenv_values, "TT_ENABLE_WRITE") or "false"
    )
    per_page = int(_resolve(environ, dotenv_values, "TT_PER_PAGE") or 100)

    return Settings(
        base_url=base_url.rstrip("/"),
        api_token=api_token,
        timeout=timeout,
        verify_ssl=verify_ssl,
        enable_write=enable_write,
        per_page=per_page,
    )
