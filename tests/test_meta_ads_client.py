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
    assert {i.campaign_id for i in insights} == {"6001", "6002"}


@pytest.mark.asyncio
async def test_insight_roas_computed_from_purchase_value():
    async with MetaAdsClient(_mock_settings()) as client:
        insights = await client.get_insights()

    day_one = next(i for i in insights if i.date_start == "2026-08-23")
    assert day_one.spend == Decimal("142.37")
    assert day_one.purchase_value == Decimal("254.94")
    assert day_one.roas == Decimal("254.94") / Decimal("142.37")


@pytest.mark.asyncio
async def test_daily_ad_performance_aggregates_across_campaigns():
    async with MetaAdsClient(_mock_settings()) as client:
        summary = await client.daily_ad_performance()

    expected_spend = Decimal("142.37") + Decimal("158.02") + Decimal("171.55") + Decimal("64.18")
    assert summary.spend == expected_spend
    assert summary.purchases == 6 + 5 + 8 + 4
    assert summary.roas == summary.purchase_value / summary.spend
