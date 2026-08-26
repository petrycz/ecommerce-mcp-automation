"""MCP server exposing Shopify store data as tools.

Run directly (stdio transport) via:
    python -m ecommerce_mcp.mcp_servers.shopify_server

Or point Claude Code / Claude Desktop's MCP config at this module. Reads
MOCK_MODE / SHOPIFY_* from the environment (see .env.example) — defaults to
mock mode with zero credentials required.
"""

from __future__ import annotations

from mcp.server.mcpserver import MCPServer

from ecommerce_mcp.clients.shopify_client import ShopifyClient

mcp = MCPServer("shopify")


@mcp.tool()
async def get_orders(status: str = "any") -> list[dict]:
    """Fetch Shopify orders (paginated automatically).

    Args:
        status: Order status filter — "any", "open", "closed", or "cancelled".
    """
    async with ShopifyClient() as client:
        orders = await client.get_orders(status=status)
        return [order.model_dump(mode="json") for order in orders]


@mcp.tool()
async def get_daily_pnl() -> dict:
    """Revenue, COGS, and gross profit across the current order set.

    COGS is resolved per line item via the Shopify inventory item cost field.
    Refunded orders are excluded.
    """
    async with ShopifyClient() as client:
        pnl = await client.daily_pnl()
        return pnl.model_dump(mode="json")


if __name__ == "__main__":
    mcp.run()
