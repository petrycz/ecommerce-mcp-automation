"""Typed client for the Meta Marketing API (ad insights).

Real endpoint, real bearer auth, real cursor-based pagination (`paging.next`
/ `paging.cursors.after`), real error/rate-limit handling — identical code
path in mock or live mode (see `clients/http.py`). `actions` and
`action_values` are Meta's generic conversion-event arrays; this client
extracts the `purchase` action specifically to compute ROAS.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Self

import httpx
from pydantic import BaseModel

from ecommerce_mcp.clients.http import build_meta_client
from ecommerce_mcp.config import Settings, get_settings


class AdInsight(BaseModel):
    date_start: str
    date_stop: str
    campaign_id: str
    campaign_name: str
    spend: Decimal
    impressions: int
    clicks: int
    reach: int
    purchases: int = 0
    purchase_value: Decimal = Decimal(0)

    @property
    def roas(self) -> Decimal | None:
        """Return on ad spend: purchase revenue / spend. None if spend is zero."""
        if self.spend == 0:
            return None
        return self.purchase_value / self.spend


class AdPerformanceSummary(BaseModel):
    spend: Decimal
    impressions: int
    clicks: int
    purchases: int
    purchase_value: Decimal
    roas: Decimal | None


def _extract_action_value(actions: list[dict], action_type: str) -> Decimal:
    for action in actions:
        if action["action_type"] == action_type:
            return Decimal(action["value"])
    return Decimal(0)


class MetaAdsClient:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._version = self._settings.meta_api_version
        self._account_id = self._settings.meta_ad_account_id or "act_1234567890"
        self._http = build_meta_client(
            access_token=self._settings.meta_access_token,
            mock=self._settings.meta_is_mock,
        )

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.aclose()

    async def _get(self, url: str, **params: object) -> httpx.Response:
        response: httpx.Response | None = None
        for _attempt in range(5):
            response = await self._http.get(url, params=params or None)
            if response.status_code == 429:
                retry_after = float(response.headers.get("Retry-After", 1))
                await asyncio.sleep(retry_after)
                continue
            response.raise_for_status()
            return response
        assert response is not None
        response.raise_for_status()
        return response

    async def get_insights(
        self, *, time_increment: int = 1, level: str = "campaign"
    ) -> list[AdInsight]:
        """Fetch ad insights, following `paging.next` cursor pagination to completion."""
        insights: list[AdInsight] = []
        url = f"/{self._version}/{self._account_id}/insights"
        params: dict[str, object] = {
            "level": level,
            "time_increment": time_increment,
            "fields": "spend,impressions,clicks,reach,actions,action_values,campaign_id,campaign_name",
        }

        while url:
            response = await self._get(url, **params)
            params = {}  # `paging.next` is a fully-formed URL
            body = response.json()
            for row in body["data"]:
                insights.append(
                    AdInsight(
                        date_start=row["date_start"],
                        date_stop=row["date_stop"],
                        campaign_id=row["campaign_id"],
                        campaign_name=row["campaign_name"],
                        spend=Decimal(row["spend"]),
                        impressions=int(row["impressions"]),
                        clicks=int(row["clicks"]),
                        reach=int(row["reach"]),
                        purchases=int(_extract_action_value(row.get("actions", []), "purchase")),
                        purchase_value=_extract_action_value(row.get("action_values", []), "purchase"),
                    )
                )
            url = body.get("paging", {}).get("next")

        return insights

    async def daily_ad_performance(
        self, insights: list[AdInsight] | None = None
    ) -> AdPerformanceSummary:
        """Aggregate spend, conversions, and blended ROAS across all campaigns."""
        insights = insights if insights is not None else await self.get_insights()

        spend = sum((i.spend for i in insights), Decimal(0))
        purchase_value = sum((i.purchase_value for i in insights), Decimal(0))

        return AdPerformanceSummary(
            spend=spend,
            impressions=sum(i.impressions for i in insights),
            clicks=sum(i.clicks for i in insights),
            purchases=sum(i.purchases for i in insights),
            purchase_value=purchase_value,
            roas=(purchase_value / spend) if spend else None,
        )
