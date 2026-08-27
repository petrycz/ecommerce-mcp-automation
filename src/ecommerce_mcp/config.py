"""Central configuration, loaded from environment variables (.env supported).

MOCK_MODE governs both integrations by default, but each can be forced
independently — e.g. a real Shopify dev store with Meta still mocked,
which is this repo's documented default (see README).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Global default; per-integration flags below override it when set.
    mock_mode: bool = True

    shopify_mock: bool | None = None
    shopify_store_domain: str | None = None  # e.g. "my-dev-store.myshopify.com"
    shopify_access_token: str | None = None
    shopify_api_version: str = "2024-10"

    meta_mock: bool | None = None
    meta_access_token: str | None = None
    meta_ad_account_id: str | None = None  # e.g. "act_1234567890"
    meta_api_version: str = "v21.0"

    @property
    def shopify_is_mock(self) -> bool:
        if self.shopify_mock is not None:
            return self.shopify_mock
        if self.shopify_store_domain and self.shopify_access_token:
            return False
        return self.mock_mode

    @property
    def meta_is_mock(self) -> bool:
        if self.meta_mock is not None:
            return self.meta_mock
        if self.meta_access_token and self.meta_ad_account_id:
            return False
        return self.mock_mode


@lru_cache
def get_settings() -> Settings:
    return Settings()
