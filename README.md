# drytrix-timetracker-mcp

A [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server for
**[DRYTRIX/TimeTracker](https://github.com/DRYTRIX/TimeTracker)** — the
self-hosted, open-source time-tracking app. It exposes your tracked hours,
projects, and reports as MCP tools over TimeTracker's stable **`/api/v1` REST
API**, so any MCP client (OpenCode, Claude Desktop, …) can query your time data
in natural language.

It is configured entirely through environment variables; nothing is baked in.

## Requirements

- Python 3.11+
- A running TimeTracker instance (tested on **v5.13.4**; targets **v5.13+**)
- An API token created in TimeTracker under
  **Admin → Security & Access → Api-tokens**

### Recommended token scopes

`read:time_entries`, `read:projects`, `read:reports`, `read:users`,
`read:clients`, `read:tasks`. Add `write:time_entries` only if you enable the
write tools. Missing scopes degrade gracefully — a tool that lacks its scope
returns a clear `403` naming the scope.

## Install & run

```bash
uvx drytrix-timetracker-mcp
```

or install it:

```bash
uv tool install drytrix-timetracker-mcp
```

## Configuration

Environment variables (a local `.env` in the working directory is also read):

| Variable | Required | Default | Meaning |
|---|---|---|---|
| `TT_BASE_URL` | yes | — | Instance root, e.g. `https://time.example.com` |
| `TIMETRACKER_API_KEY` | yes | — | API token (`tt_…`); `TT_API_TOKEN` is an alias |
| `TT_TIMEOUT` | no | `30` | Per-request timeout (seconds) |
| `TT_VERIFY_SSL` | no | `true` | Verify TLS certificates |
| `TT_ENABLE_WRITE` | no | `false` | Register the write tools |
| `TT_PER_PAGE` | no | `100` | Page size for paginated reads |

### MCP client config

```json
{
  "mcpServers": {
    "timetracker": {
      "command": "uvx",
      "args": ["drytrix-timetracker-mcp"],
      "env": {
        "TT_BASE_URL": "https://time.example.com",
        "TIMETRACKER_API_KEY": "tt_your_token_here"
      }
    }
  }
}
```

## Tools

### Read (always available)

| Tool | Scope | What it does |
|---|---|---|
| `api_info` | — | API version, timezone, enabled modules |
| `whoami` | `read:users` | The user the token authenticates as |
| `list_projects` | `read:projects` | List projects |
| `list_time_entries` | `read:time_entries` | Time entries in a date range |
| `get_hours_summary` | `read:reports` | Total/billable hours + per-project breakdown |
| `hours_by_day` | `read:time_entries` | **Per-day hours — the authoritative hours figure** |
| `list_clients` | `read:clients` | List clients |
| `list_tasks` | `read:tasks` | List tasks |
| `search` | `read:projects` | Global search |
| `timer_status` | `read:time_entries` | The active timer |

### Write (only when `TT_ENABLE_WRITE=true`, scope `write:time_entries`)

`start_timer`, `stop_timer`, `pause_timer`, `resume_timer`, `create_time_entry`

## Notes

- **`hours_by_day` is preferred over `get_hours_summary`.** TimeTracker's
  `/reports/summary` treats a date-only `end_date` as midnight and silently
  drops the final day; this server normalizes ranges and computes `hours_by_day`
  directly from time entries, so the two can disagree. `hours_by_day` is right.
- Aggregates are scoped to the token's own user. Without the `read:users` scope
  the user cannot be resolved, and the result carries a note that it may span
  users.
- Endpoints that don't exist on your version return a clear error rather than a
  stack trace.

## License

MIT
