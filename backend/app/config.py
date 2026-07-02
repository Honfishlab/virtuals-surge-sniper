"""Pydantic Settings — all config from environment variables."""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Base RPC
    base_rpc_url: str = "https://mainnet.base.org"
    base_ws_url: str = "wss://mainnet.base.org"

    # Virtuals Protocol Contracts on Base
    factory_address: str = "0x0000000000000000000000000000000000000000"
    bonding_v5_address: str = "0x1a540088125d00dd3990f9da45ca0859af4d3b01"
    virtual_token_address: str = "0x0b3e328455c4059EEb9e3f84b5543F74E24e7E1b"

    # Dune Analytics
    dune_api_key: str = ""

    # ACP API
    acp_auth_token: str = ""

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # ACP config root (for acp-cli)
    acp_config_root: str = "/app/acp-configs"

    # Cache TTLs (seconds)
    cache_ttl_token_list: int = 30
    cache_ttl_token_detail: int = 60
    cache_ttl_surge_alerts: int = 5
    cache_ttl_dune: int = 300

    # Surge engine thresholds
    surge_volume_multiplier: float = 2.0
    surge_activity_multiplier: float = 1.5

    # Alpha score weights
    alpha_weight_surge: float = 0.35
    alpha_weight_usage: float = 0.30
    alpha_weight_bonding: float = 0.20
    alpha_weight_trend: float = 0.15

    # Snipe config
    snipe_simulation_mode: bool = True


settings = Settings()
