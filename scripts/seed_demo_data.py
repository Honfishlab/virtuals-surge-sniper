#!/usr/bin/env python3
"""Seed script for development/demo with synthetic token data."""
import asyncio
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

# Add project root to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.data_aggregator.aggregator import VirtualsDataAggregator
from app.cache.redis import CacheClient
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


async def seed_demo_tokens(cache: CacheClient) -> int:
    """Generate and cache demo tokens with realistic synthetic data."""

    demo_tokens: List[Dict[str, Any]] = [
        {
            'address': '0x' + 'a' * 39 + '1',
            'name': 'NeuralChat',
            'symbol': 'NCHAT',
            'agent_id': 'agent_neural_chat',
            'creator': '0x' + 'b' * 39 + '1',
            'description': 'AI assistant for complex reasoning tasks',
            'launched_at': datetime.now(timezone.utc) - timedelta(days=5),
            'age_days': 5.0,
            'bonding_progress': 72.5,
            'bonding_value': 45000,
            'current_price': 0.0045,
            'market_cap': 22500,
            'surge_multiplier': 3.2,
            'usage_jobs_24h': 1200,
            'usage_jobs_total': 5400,
            'alpha_score': 87.5,
            'accumulated_virtual': 32000,
        },
        {
            'address': '0x' + 'a' * 39 + '2',
            'name': 'CodeGen AI',
            'symbol': 'CGEN',
            'agent_id': 'agent_code_gen',
            'creator': '0x' + 'b' * 39 + '2',
            'description': 'Automated code generation and review',
            'launched_at': datetime.now(timezone.utc) - timedelta(days=12),
            'age_days': 12.0,
            'bonding_progress': 95.0,
            'bonding_value': 95000,
            'current_price': 0.012,
            'market_cap': 120000,
            'surge_multiplier': 1.8,
            'usage_jobs_24h': 3400,
            'usage_jobs_total': 28000,
            'alpha_score': 92.0,
            'accumulated_virtual': 88000,
        },
        {
            'address': '0x' + 'a' * 39 + '3',
            'name': 'DataInsight',
            'symbol': 'DSIGHT',
            'agent_id': 'agent_data_insight',
            'creator': '0x' + 'b' * 39 + '3',
            'description': 'Data analysis and visualization agent',
            'launched_at': datetime.now(timezone.utc) - timedelta(hours=18),
            'age_days': 0.75,
            'bonding_progress': 15.0,
            'bonding_value': 7500,
            'current_price': 0.0012,
            'market_cap': 6000,
            'surge_multiplier': 5.5,
            'usage_jobs_24h': 800,
            'usage_jobs_total': 800,
            'alpha_score': 78.3,
            'accumulated_virtual': 4500,
        },
        {
            'address': '0x' + 'a' * 39 + '4',
            'name': 'GameBot Pro',
            'symbol': 'GBOT',
            'agent_id': 'agent_gamebot',
            'creator': '0x' + 'b' * 39 + '4',
            'description': 'Gaming assistant with multi-game support',
            'launched_at': datetime.now(timezone.utc) - timedelta(days=30),
            'age_days': 30.0,
            'bonding_progress': 100.0,
            'bonding_value': 150000,
            'current_price': 0.025,
            'market_cap': 500000,
            'surge_multiplier': 1.2,
            'usage_jobs_24h': 12000,
            'usage_jobs_total': 180000,
            'alpha_score': 95.1,
            'accumulated_virtual': 142000,
        },
        {
            'address': '0x' + 'a' * 39 + '5',
            'name': 'MusicVerse',
            'symbol': 'MVERSE',
            'agent_id': 'agent_music',
            'creator': '0x' + 'b' * 39 + '5',
            'description': 'AI music generation and composition',
            'launched_at': datetime.now(timezone.utc) - timedelta(days=2),
            'age_days': 2.0,
            'bonding_progress': 45.0,
            'bonding_value': 22500,
            'current_price': 0.003,
            'market_cap': 15000,
            'surge_multiplier': 4.1,
            'usage_jobs_24h': 950,
            'usage_jobs_total': 1900,
            'alpha_score': 82.7,
            'accumulated_virtual': 18000,
        },
        {
            'address': '0x' + 'a' * 39 + '6',
            'name': 'FinanceWiz',
            'symbol': 'FWIZ',
            'agent_id': 'agent_finance',
            'creator': '0x' + 'b' * 39 + '6',
            'description': 'Financial analysis and portfolio tracking',
            'launched_at': datetime.now(timezone.utc) - timedelta(days=20),
            'age_days': 20.0,
            'bonding_progress': 88.0,
            'bonding_value': 88000,
            'current_price': 0.008,
            'market_cap': 80000,
            'surge_multiplier': 1.4,
            'usage_jobs_24h': 5600,
            'usage_jobs_total': 65000,
            'alpha_score': 88.9,
            'accumulated_virtual': 75000,
        },
    ]

    token_list: List[Dict[str, Any]] = []

    for d in demo_tokens:
        token = TokenData(
            address=d['address'],
            name=d['name'],
            symbol=d['symbol'],
            agent_id=d['agent_id'],
            creator=d['creator'],
            description=d['description'],
            age_days=d['age_days'],
            launched_at=d['launched_at'],
            bonding=BondingCurveMetrics(
                progress_percent=d['bonding_progress'],
                bonding_value_virtual=d['bonding_value'],
                current_supply=int(d['bonding_progress'] * 100000),
                total_supply=1000000,
                current_price=d['current_price'],
                is_on_curve=d['bonding_progress'] < 100.0,
                is_graduated=d['bonding_progress'] >= 100.0,
            ),
            price=PriceMetrics(
                current_price=d['current_price'],
                price_24h_ago=d['current_price'] / d['surge_multiplier'],
                price_change_24h=round((1 - 1/d['surge_multiplier']) * 100, 2),
                market_cap=d['market_cap'],
                fdv=d['market_cap'] * 10,
                volume_24h=d['current_price'] * d['usage_jobs_24h'] * 0.01,
                liquidity_usd=d['market_cap'] * 0.3,
            ),
            surge=SurgeMetrics(
                volume_multiplier=d['surge_multiplier'],
                activity_multiplier=d['surge_multiplier'] * 0.8,
                overall_surge_score=d['surge_multiplier'],
                is_surging=d['surge_multiplier'] >= 2.0,
            ),
            usage=UsageMetrics(
                acp_jobs_24h=d['usage_jobs_24h'],
                acp_jobs_total=d['usage_jobs_total'],
                estimated_revenue_usd=d['usage_jobs_24h'] * 0.005,
            ),
            alpha_score=AlphaScoreResult(
                overall_score=d['alpha_score'],
                surge_component=d['surge_multiplier'] * 20,
                usage_component=min(100, d['usage_jobs_24h'] / 120),
                bonding_component=d['bonding_progress'],
                trend_component=75.0,
            ),
            accumulated_virtual=d['accumulated_virtual'],
            token_type=TokenType.GRADUATED if d['bonding_progress'] >= 100.0 else TokenType.ON_CURVE,
            status=TokenStatus.ACTIVE,
        )
        token_list.append(token.model_dump())

    # Cache the token list
    await cache.set(CacheClient.token_list_key(), token_list, 30)

    # Also cache individual details
    for d in demo_tokens:
        key = CacheClient.token_detail_key(d['address'])
        for t in token_list:
            if t['address'] == d['address']:
                await cache.set(key, t, 60)
                break

    print(f'  Seeded {len(token_list)} demo tokens')
    print(f'  Surging: {sum(1 for t in token_list if t.get("surge", {}).get("is_surging", False))}')
    print(f'  Graduated: {sum(1 for t in token_list if t.get("token_type") == "graduated")}')

    return len(token_list)


async def main():
    """Run the seed script."""
    redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')

    print('=== Seeding Demo Data ===')
    print(f'  Redis: {redis_url}')

    cache = CacheClient(redis_url)
    await cache.connect()

    count = await seed_demo_tokens(cache)
    await cache.close()

    print(f'Done. Seeded {count} tokens.')


if __name__ == '__main__':
    asyncio.run(main())
