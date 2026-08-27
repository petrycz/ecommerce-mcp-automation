"""Builds the httpx.Client each integration client uses.

The only difference between mock and live mode is the transport: live mode
opens a real socket to the real API host; mock mode routes requests through
an in-process ASGI app (`fixtures/mock_api.py`) serving realistic fixture
payloads. Everything above this layer — auth headers, query params,
pagination, error handling — is identical either way.
"""

from __future__ import annotations

import httpx

from ecommerce_mcp.fixtures.mock_api import app as mock_app


def build_shopify_client(
    *, store_domain: str | None, access_token: str | None, mock: bool
) -> httpx.AsyncClient:
    if mock:
        return httpx.AsyncClient(
            base_url="https://mock-dev-store.myshopify.com",
            transport=httpx.ASGITransport(app=mock_app),
            headers={"X-Shopify-Access-Token": "mock-token"},
        )

    if not store_domain or not access_token:
        raise ValueError(
            "SHOPIFY_STORE_DOMAIN and SHOPIFY_ACCESS_TOKEN are required for live mode"
        )
    return httpx.AsyncClient(
        base_url=f"https://{store_domain}",
        headers={"X-Shopify-Access-Token": access_token},
        timeout=30.0,
    )


def build_meta_client(
    *, access_token: str | None, mock: bool
) -> httpx.AsyncClient:
    if mock:
        return httpx.AsyncClient(
            base_url="https://graph.facebook.com",
            transport=httpx.ASGITransport(app=mock_app),
        )

    if not access_token:
        raise ValueError("META_ACCESS_TOKEN is required for live mode")
    return httpx.AsyncClient(
        base_url="https://graph.facebook.com",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30.0,
    )
