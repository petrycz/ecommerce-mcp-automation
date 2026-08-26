from decimal import Decimal

import pytest

from ecommerce_mcp.clients.shopify_client import ShopifyClient
from ecommerce_mcp.config import Settings


def _mock_settings() -> Settings:
    return Settings(mock_mode=True, shopify_mock=True, meta_mock=True)


@pytest.mark.asyncio
async def test_get_orders_follows_pagination():
    async with ShopifyClient(_mock_settings()) as client:
        orders = await client.get_orders()

    # 3 orders on fixture page 1 + 2 on page 2
    assert len(orders) == 5
    assert {o.name for o in orders} == {"#1001", "#1002", "#1003", "#1004", "#1005"}


@pytest.mark.asyncio
async def test_get_cogs_by_variant_resolves_real_lookup_chain():
    async with ShopifyClient(_mock_settings()) as client:
        costs = await client.get_cogs_by_variant({44001, 44005})

    assert costs[44001] == Decimal("8.50")
    assert costs[44005] == Decimal("6.25")


@pytest.mark.asyncio
async def test_get_cogs_by_variant_treats_null_cost_as_zero():
    # A live store can have an inventory item with no cost ever entered —
    # this shouldn't raise, it should resolve to 0 (regression: real dev
    # store hit this via a sample product with cost=null).
    async with ShopifyClient(_mock_settings()) as client:
        costs = await client.get_cogs_by_variant({44099})

    assert costs[44099] == Decimal(0)


@pytest.mark.asyncio
async def test_daily_pnl_excludes_refunded_orders():
    async with ShopifyClient(_mock_settings()) as client:
        pnl = await client.daily_pnl()

    # order #1003 (refunded) must not count toward revenue/order_count
    assert pnl.order_count == 4
    assert pnl.revenue == Decimal("84.97") + Decimal("24.99") + Decimal("104.96") + Decimal("29.99")
    assert pnl.gross_profit == pnl.revenue - pnl.cogs
    assert pnl.cogs > 0
