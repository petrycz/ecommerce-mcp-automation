"""Typed client for the Shopify Admin REST API.

Real endpoints, real auth header, real Link-header pagination, real 429
backoff — identical code path whether talking to a live dev store or the
in-process mock transport (see `clients/http.py`). COGS isn't on the order
line item in Shopify's API, so `get_cogs_by_variant` does the real two-hop
lookup a live integration needs: variant -> inventory_item_id, then a
batched inventory_items fetch for `cost`.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Self

import httpx
from pydantic import BaseModel

from ecommerce_mcp.clients.http import build_shopify_client
from ecommerce_mcp.config import Settings, get_settings


class LineItem(BaseModel):
    id: int
    product_id: int
    variant_id: int
    sku: str | None = None  # Shopify allows variants with no SKU set
    title: str
    quantity: int
    price: Decimal


class Order(BaseModel):
    id: int
    name: str
    created_at: str
    currency: str
    financial_status: str
    total_price: Decimal
    subtotal_price: Decimal
    total_tax: Decimal
    total_discounts: Decimal
    line_items: list[LineItem]


class DailyPnL(BaseModel):
    order_count: int
    revenue: Decimal
    cogs: Decimal
    gross_profit: Decimal


class ShopifyClient:
    def __init__(self, settings: Settings | None = None):
        self._settings = settings or get_settings()
        self._version = self._settings.shopify_api_version
        self._http = build_shopify_client(
            store_domain=self._settings.shopify_store_domain,
            access_token=self._settings.shopify_access_token,
            mock=self._settings.shopify_is_mock,
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

    async def get_orders(self, *, status: str = "any", limit: int = 250) -> list[Order]:
        """Fetch all orders, following Link-header pagination to completion."""
        orders: list[Order] = []
        url = f"/admin/api/{self._version}/orders.json"
        params: dict[str, object] = {"status": status, "limit": limit}

        while url:
            response = await self._get(url, **params)
            params = {}  # subsequent requests use the full `next` URL as-is
            body = response.json()
            orders.extend(Order.model_validate(o) for o in body["orders"])
            url = self._next_link(response)

        return orders

    @staticmethod
    def _next_link(response: httpx.Response) -> str | None:
        link_header = response.headers.get("Link")
        if not link_header:
            return None
        for part in link_header.split(","):
            segment, _, rel = part.partition(";")
            if 'rel="next"' in rel:
                return segment.strip().strip("<>")
        return None

    async def get_cogs_by_variant(self, variant_ids: set[int]) -> dict[int, Decimal]:
        """Resolve unit cost per variant via its inventory item.

        Shopify doesn't expose cost on the order line item directly, so this
        mirrors the real lookup: fetch each variant for its
        `inventory_item_id`, then a single batched `inventory_items` request
        for the `cost` field. `cost` is nullable on a live store — a merchant
        may never have filled it in for a given item — and that's treated as
        zero cost rather than an error.
        """
        inventory_item_id_by_variant: dict[int, int] = {}
        for variant_id in variant_ids:
            response = await self._get(f"/admin/api/{self._version}/variants/{variant_id}.json")
            inventory_item_id_by_variant[variant_id] = response.json()["variant"]["inventory_item_id"]

        if not inventory_item_id_by_variant:
            return {}

        ids_param = ",".join(str(i) for i in set(inventory_item_id_by_variant.values()))
        response = await self._get(f"/admin/api/{self._version}/inventory_items.json", ids=ids_param)
        cost_by_inventory_item = {
            item["id"]: Decimal(item["cost"]) if item["cost"] is not None else Decimal(0)
            for item in response.json()["inventory_items"]
        }

        return {
            variant_id: cost_by_inventory_item[inventory_item_id]
            for variant_id, inventory_item_id in inventory_item_id_by_variant.items()
            if inventory_item_id in cost_by_inventory_item
        }

    async def daily_pnl(self, orders: list[Order] | None = None) -> DailyPnL:
        """Revenue, COGS, and gross profit across the given (or freshly fetched) orders.

        Refunded orders are excluded from revenue and COGS — a simplification
        appropriate for a daily snapshot; partial refunds/returns accounting
        would need the Refund resource, out of scope for this sample.
        """
        orders = orders if orders is not None else await self.get_orders()
        counted_orders = [o for o in orders if o.financial_status != "refunded"]

        variant_ids = {li.variant_id for o in counted_orders for li in o.line_items}
        cost_by_variant = await self.get_cogs_by_variant(variant_ids)

        revenue = sum((o.total_price for o in counted_orders), Decimal(0))
        cogs = sum(
            (
                cost_by_variant.get(li.variant_id, Decimal(0)) * li.quantity
                for o in counted_orders
                for li in o.line_items
            ),
            Decimal(0),
        )

        return DailyPnL(
            order_count=len(counted_orders),
            revenue=revenue,
            cogs=cogs,
            gross_profit=revenue - cogs,
        )
