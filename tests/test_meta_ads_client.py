from decimal import Decimal

import pytest

from ecommerce_mcp.clients.meta_ads_client import MetaAdsClient
from ecommerce_mcp.config import Settings


def _mock_settings() -> Settings:
    return Settings(mock_mode=True, shopify_mock=True, meta_mock=True)


@pytest.mark.asyncio
async def test_get_insights_follows_cursor_pagination():
    async with MetaAdsClient(_mock_settings()) as client:
        insights = await client.get_insights()

    # 2 rows on fixture page 1 + 2 rows on page 2
    assert len(insights) == 4
    assert {i.campaign_id for i in insights} == {"6001", "6002", "6003", "6004"}


@pytest.mark.asyncio
async def test_insight_roas_computed_from_purchase_value():
    async with MetaAdsClient(_mock_settings()) as client:
        insights = await client.get_insights()

    prospecting = next(i for i in insights if i.campaign_id == "6001")
    assert prospecting.spend == Decimal("52.30")
    assert prospecting.purchase_value == Decimal("89.97")
    assert prospecting.roas == Decimal("89.97") / Decimal("52.30")


@pytest.mark.asyncio
async def test_daily_ad_performance_aggregates_across_campaigns():
    async with MetaAdsClient(_mock_settings()) as client:
        summary = await client.daily_ad_performance()

    expected_spend = Decimal("52.30") + Decimal("28.75") + Decimal("41.60") + Decimal("19.85")
    assert summary.spend == expected_spend
    assert summary.purchases == 3 + 2 + 2 + 1
    assert summary.roas == summary.purchase_value / summary.spend
