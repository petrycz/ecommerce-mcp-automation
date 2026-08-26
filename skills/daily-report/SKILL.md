---
name: daily-report
description: Generate the daily Shopify + Meta Ads P&L and ad-performance report as a formatted .xlsx spreadsheet. Use when asked to run, generate, or refresh today's numbers, P&L, revenue/COGS/gross-profit, ad spend, or ROAS report.
---

# Daily P&L + Ad Performance Report

Produces a formatted spreadsheet combining same-day Shopify revenue/COGS/gross
profit with Meta Ads spend/ROAS — the workflow this whole repo exists to
demonstrate. No manual copy-paste: both sources are pulled and written to the
workbook in one run.

## When to use this skill

Trigger on requests like "run the daily report," "what's today's P&L," "pull
this week's ad performance," "regenerate the report," or "how's ROAS looking
today." Not for one-off questions about a single number — for those, call the
`get_daily_pnl` / `get_daily_ad_performance` MCP tools directly instead of
running the full workbook build.

## Running it

```bash
python -m ecommerce_mcp.reporting.daily_report [output_path]
```

- Defaults to `examples/sample_daily_report.xlsx` if no path is given.
- Defaults to mock mode (`MOCK_MODE=true`) — runs with zero credentials
  against realistic fixtures.
- For live data: set `SHOPIFY_STORE_DOMAIN` / `SHOPIFY_ACCESS_TOKEN` and/or
  `META_ACCESS_TOKEN` / `META_AD_ACCOUNT_ID` in `.env` (see `.env.example`).
  Each integration switches to live independently the moment its credentials
  are present — you don't need both to go live at once.

After running, report back the key numbers from the Summary sheet (revenue,
COGS, gross profit, ad spend, net profit, blended ROAS) rather than just
saying the file was written — that's the actual answer to "how are we doing
today."

## Architecture notes (for extending this skill)

- `src/ecommerce_mcp/clients/shopify_client.py` / `meta_ads_client.py` — typed
  API clients, real endpoints and pagination, mock/live swappable via
  `clients/http.py`.
- `src/ecommerce_mcp/mcp_servers/` — the same clients exposed as MCP tools,
  for ad hoc questions in a chat rather than a full report run.
- `src/ecommerce_mcp/reporting/daily_report.py` — orchestrates both clients
  concurrently and calls `spreadsheet.py` to build the workbook.

If asked to add a new metric (e.g. discount rate, CPA), it likely belongs as
a computed property on the relevant client model, then a new row/column in
`spreadsheet.py` — not a one-off calculation in the report script.
