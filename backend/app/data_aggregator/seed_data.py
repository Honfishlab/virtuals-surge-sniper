"""Seed data for the dashboard - works without blockchain/RPC connections."""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.models import (
    AlphaScoreResult,
    BondingCurveMetrics,
    PriceMetrics,
    SurgeMetrics,
    TokenData,
    TokenStatus,
    TokenType,
    UsageMetrics,
)


async def get_seed_tokens() -> list[TokenData]:
    """Generate realistic seed token data for the dashboard."""
    now = datetime.now(timezone.utc)
    
    sample_tokens = [
        {"name": "VITAL Protocol", "symbol": "VITAL", "token_type": TokenType.ON_CURVE},
        {"name": "DEGEN AI", "symbol": "DEGEN", "token_type": TokenType.ON_CURVE},
        {"name": "VIRTUAL Finance", "symbol": "VIRTUAL", "token_type": TokenType.GRADUATED},
        {"name": "NODL Agent", "symbol": "NODL", "token_type": TokenType.ON_CURVE},
        {"name": "FET AI", "symbol": "FET", "token_type": TokenType.GRADUATED},
        {"name": "Bittensor Clone", "symbol": "BTCL", "token_type": TokenType.ON_CURVE},
        {"name": "LINDA AI", "symbol": "LINDA", "token_type": TokenType.ON_CURVE},
        {"name": "TIA Data", "symbol": "TIA", "token_type": TokenType.GRADUATED},
        {"name": "MOON Agent", "symbol": "MOON", "token_type": TokenType.ON_CURVE},
        {"name": "APE Finance", "symbol": "APE", "token_type": TokenType.GRADUATED},
    ]
    
    tokens = []
    for sample in sample_tokens:
        age_hours = random.uniform(0.5, 168)
        progress = round(random.uniform(5, 95), 2)
        alpha_score = round(random.uniform(30, 95), 2)
        
        is_surging = random.random() < 0.3
        
        if is_surging:
            surge_score = round(random.uniform(70, 99), 2)
            surge_multiplier = round(random.uniform(2.0, 8.0), 2)
        else:
            surge_score = round(random.uniform(20, 60), 2)
            surge_multiplier = round(random.uniform(1.0, 2.0), 2)
        
        bonding_value = round(random.uniform(100, 5000), 2)
        market_cap = round(bonding_value * random.uniform(5, 50), 2)
        current_price = round(random.uniform(0.0001, 0.5), 6)
        
        token = TokenData(
            address=f"0x{random.randint(0, 2**160):040x}",
            name=sample["name"],
            symbol=sample["symbol"],
            token_type=sample["token_type"],
            status=TokenStatus.ACTIVE,
            age_days=round(age_hours / 24, 2),
            launched_at=now - timedelta(hours=age_hours),
            bonding=BondingCurveMetrics(
                progress_percent=progress,
                bonding_value_virtual=bonding_value,
                current_supply=int(random.uniform(1e6, 1e9)),
                total_supply=int(1e9),
                current_price=current_price,
                is_on_curve=sample["token_type"] == TokenType.ON_CURVE,
                is_graduated=sample["token_type"] == TokenType.GRADUATED,
            ),
            price=PriceMetrics(
                current_price=current_price,
                price_24h_ago=round(current_price * random.uniform(0.9, 1.1), 6),
                price_change_24h=round(random.uniform(-20, 50), 2),
                market_cap=market_cap,
                fdv=round(market_cap * random.uniform(2, 10), 2),
                liquidity_usd=round(bonding_value * random.uniform(2, 5), 2),
                volume_24h=round(bonding_value * random.uniform(0.5, 10), 2),
                volume_7d=round(bonding_value * random.uniform(2, 20), 2),
            ),
            usage=UsageMetrics(
                acp_jobs_24h=random.randint(50, 100000),
                acp_jobs_total=random.randint(1000, 5000000),
                inference_calls_24h=random.randint(1000, 500000),
                micro_payments_24h=random.randint(100, 50000),
                estimated_revenue_usd=round(bonding_value * random.uniform(0.01, 0.2), 2),
            ),
            surge=SurgeMetrics(
                volume_multiplier=round(surge_multiplier, 2),
                activity_multiplier=round(surge_multiplier * random.uniform(0.8, 1.2), 2),
                overall_surge_score=surge_score,
                is_surging=is_surging,
                last_surge_detected=now - timedelta(minutes=random.randint(1, 120)) if is_surging else None,
            ),
            alpha_score=AlphaScoreResult(
                overall_score=alpha_score,
                surge_component=round(alpha_score * random.uniform(0.3, 0.5), 2),
                usage_component=round(alpha_score * random.uniform(0.2, 0.35), 2),
                bonding_component=round(alpha_score * random.uniform(0.15, 0.3), 2),
                trend_component=round(alpha_score * random.uniform(0.1, 0.25), 2),
                custom_weight=1.0,
            ),
            accumulated_virtual=round(bonding_value * random.uniform(0.5, 2.0), 2),
            treasury_revenue_usd=round(market_cap * random.uniform(0.001, 0.01), 2),
        )
        tokens.append(token)
    
    return tokens


async def get_seed_surges() -> list[dict]:
    """Generate seed surge alerts."""
    now = datetime.now(timezone.utc)
    
    surges = []
    surge_types = ["volume_spike", "activity_burst", "combined_surge", "new_momentum"]
    token_names = ["VITAL", "DEGEN", "NODL", "BTCL", "LINDA", "VIRTUAL", "FET", "TIA"]
    
    for i in range(random.randint(2, 5)):
        surges.append({
            "token_address": f"0x{random.randint(0, 2**160):040x}",
            "token_name": random.choice(token_names),
            "surge_type": random.choice(surge_types),
            "surge_score": round(random.uniform(70, 99), 2),
            "surge_multiplier": round(random.uniform(2.0, 10.0), 2),
            "timestamp": (now - timedelta(minutes=random.randint(1, 60))).isoformat(),
            "details": f"Sudden {random.choice(['volume', 'price', 'activity'])} spike detected",
        })
    
    return surges
