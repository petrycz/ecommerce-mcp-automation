"""Pulls today's Shopify orders/P&L and Meta Ads insights, then writes a
formatted daily report spreadsheet. No manual copy-paste, no intermediate
CSV — client models flow straight into the workbook.

Usage:
    python -m ecommerce_mcp.reporting.daily_report [output_path]

Defaults to mock mode; set MOCK_MODE=false (with SHOPIFY_*/META_* creds)
to pull live data.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from ecommerce_mcp.clients.meta_ads_client import MetaAdsClient
from ecommerce_mcp.clients.shopify_client import ShopifyClient
from ecommerce_mcp.reporting.spreadsheet import build_workbook

DEFAULT_OUTPUT = Path("examples/sample_daily_report.xlsx")


async def generate_report(output_path: Path = DEFAULT_OUTPUT) -> Path:
    async with ShopifyClient() as shopify, MetaAdsClient() as meta:
        orders, insights = await asyncio.gather(shopify.get_orders(), meta.get_insights())
        pnl, ad_summary = await asyncio.gather(
            shopify.daily_pnl(orders),
            meta.daily_ad_performance(insights),
        )

    workbook = build_workbook(
        report_date=datetime.now().astimezone().date(),
        pnl=pnl,
        orders=orders,
        ad_summary=ad_summary,
        insights=insights,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(output_path)
    return output_path


def main() -> None:
    output_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_OUTPUT
    saved_path = asyncio.run(generate_report(output_path))
    print(f"Wrote {saved_path}")


if __name__ == "__main__":
    main()
