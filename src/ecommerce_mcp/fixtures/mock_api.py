"""In-process fixture server mimicking the real Shopify Admin API and Meta
Marketing API response shapes (status codes, pagination headers/cursors).

This app is never bound to a real socket. It's mounted onto an
`httpx.ASGITransport` (see `clients/http.py`), so requests from the real
client code travel through genuine HTTP/ASGI routing and serialization —
only the network hop is skipped. That's what keeps `shopify_client.py` and
`meta_ads_client.py` identical in shape whether MOCK_MODE is on or off.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

FIXTURES_DIR = Path(__file__).parent


def _load(name: str) -> Any:
    return json.loads((FIXTURES_DIR / name).read_text())


app = FastAPI(title="Mock Shopify + Meta API")

_ORDERS_PAGES = [
    _load("shopify_orders_page1.json"),
    _load("shopify_orders_page2.json"),
]
_INVENTORY_ITEMS = {item["id"]: item for item in _load("shopify_inventory_items.json")["inventory_items"]}
_VARIANTS = _load("shopify_variants.json")
_META_PAGES = [
    _load("meta_insights_page1.json"),
    _load("meta_insights_page2.json"),
]


@app.get("/admin/api/{version}/orders.json")
def shopify_orders(version: str, request: Request, page_info: str | None = None, limit: int = 250):
    page_index = 0
    if page_info == "page2":
        page_index = 1
    body = _ORDERS_PAGES[page_index]

    headers = {}
    if page_index == 0:
        next_url = str(request.url.include_query_params(page_info="page2"))
        headers["Link"] = f'<{next_url}>; rel="next"'
    return JSONResponse(content=body, headers=headers)


@app.get("/admin/api/{version}/variants/{variant_id}.json")
def shopify_variant(version: str, variant_id: int):
    variant = _VARIANTS.get(str(variant_id))
    if variant is None:
        return JSONResponse(status_code=404, content={"errors": "Not Found"})
    return {"variant": variant}


@app.get("/admin/api/{version}/inventory_items.json")
def shopify_inventory_items(version: str, ids: str):
    requested_ids = {int(i) for i in ids.split(",")}
    items = [item for item_id, item in _INVENTORY_ITEMS.items() if item_id in requested_ids]
    return {"inventory_items": items}


@app.get("/{version}/act_{account_id}/insights")
def meta_insights(version: str, account_id: str, request: Request, after: str | None = None):
    page_index = 1 if after == "AaB2" else 0
    return _META_PAGES[page_index]
