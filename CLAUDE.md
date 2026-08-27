# CLAUDE.md

Conventions for working on this repo with Claude Code.

## What this is

A sample Claude Code + MCP automation: Shopify + Meta Ads data exposed as MCP
tools, and a reporting agent that pulls both into a formatted daily P&L / ad
performance spreadsheet. See `README.md` for the full picture — this file is
about *how to work in the codebase*, not what it does.

## Running things

```bash
python -m venv .venv && source .venv/bin/activate   # or: uv sync
pip install -e ".[dev]"

pytest                                               # full test suite
ruff check src tests                                 # lint
python -m ecommerce_mcp.reporting.daily_report       # generate the report (mock mode by default)
python -m ecommerce_mcp.mcp_servers.shopify_server   # run a single MCP server standalone
```

Mock mode (`MOCK_MODE=true`, the default) requires zero credentials. See
`.env.example` for live-mode variables.

## Architecture

```
clients/          typed API clients — real endpoints, real auth, real
                   pagination/error handling. Transport swaps mock<->live
                   (clients/http.py); everything else is identical either way.
mcp_servers/       thin MCP tool wrappers around the clients (FastMCP-style
                   `MCPServer`, mcp>=2.0 API — this is NOT the old `FastMCP`
                   import path from mcp v1).
reporting/         daily_report.py orchestrates both clients concurrently;
                   spreadsheet.py builds the openpyxl workbook.
fixtures/          realistic mock payloads + mock_api.py, an in-process
                   FastAPI app mounted via httpx.ASGITransport (no real
                   socket, no subprocess — see clients/http.py).
```

**Golden rule:** a client function should never know or care whether it's
being called in mock or live mode. If you're tempted to add an `if mock:`
branch inside `shopify_client.py` or `meta_ads_client.py`, the mock behavior
belongs in `fixtures/mock_api.py` instead.

## Conventions

- **Async throughout.** All client I/O is `async def` over `httpx.AsyncClient`
  — required for the ASGI mock transport, and the right shape for MCP tool
  handlers regardless. Don't add a sync wrapper.
- **Pydantic models at the API boundary.** Client methods return typed models
  (`Order`, `AdInsight`, `DailyPnL`, ...), not raw dicts. MCP tools call
  `.model_dump(mode="json")` at the tool boundary, not before.
- **Money is `Decimal`, never `float`,** everywhere except the final
  openpyxl cell value (openpyxl needs numeric types it can format — cast to
  `float` only at that last step in `spreadsheet.py`).
- **New API calls get a docstring naming the real endpoint** they correspond
  to (e.g. "GET /admin/api/{version}/orders.json") — this repo's entire value
  as a portfolio piece is that the integration code is genuine, not a mock
  pretending to be one. Don't lose that when extending it.
- **Fixtures mirror real response shapes**, including the fields you're not
  using yet, where practical. If the real API wouldn't return a field this
  simply, don't invent a fixture that does (see `shopify_client.py`'s
  variant → inventory_item → cost lookup for the pattern: it's a real
  two-hop lookup because Shopify's API actually requires one).
- **One vertical slice at a time.** When adding a third integration or a new
  report metric, land the client + its tests before wiring it into
  `daily_report.py` / `spreadsheet.py` — matches how this repo itself was
  built (Shopify slice, then Meta slice, then reporting).

## Testing

Tests run entirely against mock mode (`Settings(mock_mode=True, ...)`) — no
network, no credentials, fast. When adding a client method, add a test that
exercises it through the real pagination/lookup path, not just a
happy-path single call — that's what caught real bugs during development
(e.g. `ASGITransport` requiring an async client, not sync).

## Honesty guardrails

This repo is a labeled *sample* built against public API documentation, not
a system that has run a live store. Keep it that way:

- Don't add anything that implies production traffic, real customer data, or
  a live business behind this code.
- Mock fixtures should stay clearly synthetic (placeholder store/product
  names, round-ish numbers) — not styled to look like a redacted real export.
- If you wire up live credentials for testing, never commit `.env` or any
  captured live API response.
