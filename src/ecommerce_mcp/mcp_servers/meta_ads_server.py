"""MCP server exposing Meta Ads performance data as tools.

Run directly (stdio transport) via:
    python -m ecommerce_mcp.mcp_servers.meta_ads_server

Reads MOCK_MODE / META_* from the environment (see .env.example) — defaults
to mock mode with zero credentials required.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from ecommerce_mcp.clients.meta_ads_client import MetaAdsClient

mcp = MCPServer("meta-ads")


@mcp.tool()
async def get_insights(level: str = "campaign") -> list[dict]:
    """Fetch daily ad insights (spend, impressions, clicks, purchases), paginated automatically.

    Args:
        level: Aggregation level — "campaign", "adset", "ad", or "account".
    """
    async with MetaAdsClient() as client:
        insights = await client.get_insights(level=level)
        return [insight.model_dump(mode="json") for insight in insights]


@mcp.tool()
async def get_daily_ad_performance() -> dict:
    """Aggregate spend, purchases, purchase value, and blended ROAS across all campaigns."""
    async with MetaAdsClient() as client:
        summary = await client.daily_ad_performance()
        return summary.model_dump(mode="json")


if __name__ == "__main__":
    mcp.run()
