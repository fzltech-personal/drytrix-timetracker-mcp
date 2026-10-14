from drytrix_timetracker_mcp.config import Settings
from drytrix_timetracker_mcp.server import build_server

SETTINGS = Settings(
    base_url="https://time.example.com",
    api_token="tt_x",
    timeout=30.0,
    verify_ssl=True,
    enable_write=False,
    per_page=100,
)


def test_build_server_constructs():
    # Regression: mcp>=2 renamed FastMCP -> MCPServer; this import must hold.
    assert build_server(SETTINGS).name == "drytrix-timetracker-mcp"
