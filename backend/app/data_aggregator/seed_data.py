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
        {"name": "SOL Agent", "symbol": "SOLAG", "token_type": TokenType.ON_CURVE},
        {"name": "ETH Oracle", "symbol": "EORCL", "token_type": TokenType.GRADUATED},
        {"name": "BTC Swarm", "symbol": "BTCW", "token_type": TokenType.ON_CURVE},
        {"name": "POLY Math", "symbol": "POLYM", "token_type": TokenType.ON_CURVE},
        {"name": "AVAX Nexus", "symbol": "AVNX", "token_type": TokenType.GRADUATED},
        {"name": "ARB Trade", "symbol": "ARBT", "token_type": TokenType.ON_CURVE},
        {"name": "OP Synth", "symbol": "OPSNT", "token_type": TokenType.ON_CURVE},
        {"name": "NEAR Vision", "symbol": "NRVSN", "token_type": TokenType.GRADUATED},
        {"name": "SUI Chat", "symbol": "SUCHT", "token_type": TokenType.ON_CURVE},
        {"name": "TON Voice", "symbol": "TONVC", "token_type": TokenType.ON_CURVE},
        {"name": "INJ Trader", "symbol": "INJTR", "token_type": TokenType.GRADUATED},
        {"name": "ATOM Forge", "symbol": "ATMFG", "token_type": TokenType.ON_CURVE},
        {"name": "DYDX Flux", "symbol": "DYDXX", "token_type": TokenType.ON_CURVE},
        {"name": "GRT Index", "symbol": "GRTIX", "token_type": TokenType.GRADUATED},
        {"name": "FTM Speed", "symbol": "FTMSD", "token_type": TokenType.ON_CURVE},
        {"name": "ONE Wallet", "symbol": "ONEWL", "token_type": TokenType.ON_CURVE},
        {"name": "ALGO Think", "symbol": "ALGTH", "token_type": TokenType.GRADUATED},
        {"name": "HBAR Stream", "symbol": "HBRSR", "token_type": TokenType.ON_CURVE},
        {"name": "CELO Mind", "symbol": "CELMD", "token_type": TokenType.ON_CURVE},
        {"name": "XTZ Forge", "symbol": "XTZFG", "token_type": TokenType.GRADUATED},
        {"name": "FLOW Play", "symbol": "FLOWP", "token_type": TokenType.ON_CURVE},
        {"name": "ICP Cloud", "symbol": "ICPCD", "token_type": TokenType.ON_CURVE},
        {"name": "KSM Stash", "symbol": "KSMSH", "token_type": TokenType.GRADUATED},
        {"name": "EGLS Vault", "symbol": "EGLSV", "token_type": TokenType.ON_CURVE},
        {"name": "ROSE Chain", "symbol": "ROSCH", "token_type": TokenType.ON_CURVE},
        {"name": "IMX Grid", "symbol": "IMXGD", "token_type": TokenType.GRADUATED},
        {"name": "GALA Wave", "symbol": "GALAW", "token_type": TokenType.ON_CURVE},
        {"name": "MANA Plot", "symbol": "MANAP", "token_type": TokenType.ON_CURVE},
        {"name": "SAND Realm", "symbol": "SDRLM", "token_type": TokenType.GRADUATED},
        {"name": "AXS War", "symbol": "AXSWR", "token_type": TokenType.ON_CURVE},
        {"name": "ENJ Mint", "symbol": "ENJMN", "token_type": TokenType.ON_CURVE},
        {"name": "CHZ Blaze", "symbol": "CHZBL", "token_type": TokenType.GRADUATED},
        {"name": "BAT Ad", "symbol": "BTAD", "token_type": TokenType.ON_CURVE},
        {"name": "ZRX Swap", "symbol": "ZRXSW", "token_type": TokenType.ON_CURVE},
        {"name": "COMP Vault", "symbol": "CMPVL", "token_type": TokenType.GRADUATED},
        {"name": "MKR DAO", "symbol": "MKRDAO", "token_type": TokenType.ON_CURVE},
        {"name": "AAVE Pulse", "symbol": "AAVPL", "token_type": TokenType.ON_CURVE},
        {"name": "UNI Flow", "symbol": "UNIFL", "token_type": TokenType.GRADUATED},
        {"name": "SHIB Burn", "symbol": "SHBRN", "token_type": TokenType.ON_CURVE},
        {"name": "DOGE Moon", "symbol": "DOGMN", "token_type": TokenType.ON_CURVE},
        {"name": "PEPE Coin", "symbol": "PEPEC", "token_type": TokenType.GRADUATED},
        {"name": "FLOKI Saga", "symbol": "FLKS", "token_type": TokenType.ON_CURVE},
        {"name": "BONK Wave", "symbol": "BNKWV", "token_type": TokenType.ON_CURVE},
        {"name": "WIF Dog", "symbol": "WIFDG", "token_type": TokenType.GRADUATED},
        {"name": "POP Cat", "symbol": "POPC", "token_type": TokenType.ON_CURVE},
        {"name": "TURBO Speed", "symbol": "TURBS", "token_type": TokenType.ON_CURVE},
        {"name": "MOG Lord", "symbol": "MOGLD", "token_type": TokenType.GRADUATED},
        {"name": "BRETT Bit", "symbol": "BRETT", "token_type": TokenType.ON_CURVE},
        {"name": "TOSHI Myth", "symbol": "TSHMY", "token_type": TokenType.ON_CURVE},
        {"name": "DEGEN AI", "symbol": "DEGAI", "token_type": TokenType.GRADUATED},
        {"name": "AI Agent", "symbol": "AIAE", "token_type": TokenType.ON_CURVE},
        {"name": "NNET Neural", "symbol": "NNET", "token_type": TokenType.ON_CURVE},
        {"name": "RL Agent", "symbol": "RLAG", "token_type": TokenType.GRADUATED},
        {"name": "GAN Bot", "symbol": "GANBT", "token_type": TokenType.ON_CURVE},
        {"name": "BERT Chat", "symbol": "BERTC", "token_type": TokenType.ON_CURVE},
        {"name": "LLAMA Gen", "symbol": "LLAGN", "token_type": TokenType.GRADUATED},
        {"name": "MISTRAL", "symbol": "MIST", "token_type": TokenType.ON_CURVE},
        {"name": "QWEN Mind", "symbol": "QWENM", "token_type": TokenType.ON_CURVE},
        {"name": "CODER AI", "symbol": "CDR", "token_type": TokenType.GRADUATED},
        {"name": "PROMPT", "symbol": "PRMPT", "token_type": TokenType.ON_CURVE},
        {"name": "VISION AI", "symbol": "VSAI", "token_type": TokenType.ON_CURVE},
        {"name": "AUDIO Bot", "symbol": "AUDBT", "token_type": TokenType.GRADUATED},
        {"name": "VIDEO Gen", "symbol": "VDGN", "token_type": TokenType.ON_CURVE},
        {"name": "IMAGE Synth", "symbol": "IMGS", "token_type": TokenType.ON_CURVE},
        {"name": "TEXT Gen", "symbol": "TXGN", "token_type": TokenType.GRADUATED},
        {"name": "CODE Review", "symbol": "CODRV", "token_type": TokenType.ON_CURVE},
        {"name": "DATA Proc", "symbol": "DTPR", "token_type": TokenType.ON_CURVE},
        {"name": "ML Train", "symbol": "MLTR", "token_type": TokenType.GRADUATED},
        {"name": "DL Inference", "symbol": "DLINF", "token_type": TokenType.ON_CURVE},
        {"name": "RLHF Bot", "symbol": "RLHFB", "token_type": TokenType.ON_CURVE},
        {"name": "TRANSFORM", "symbol": "TRFR", "token_type": TokenType.GRADUATED},
        {"name": "EMBED Vector", "symbol": "EMBV", "token_type": TokenType.ON_CURVE},
        {"name": "KV Store", "symbol": "KVST", "token_type": TokenType.ON_CURVE},
        {"name": "GRAPH DB", "symbol": "GRDB", "token_type": TokenType.GRADUATED},
        {"name": "TIME Series", "symbol": "TIMES", "token_type": TokenType.ON_CURVE},
        {"name": "NLP Proc", "symbol": "NLP", "token_type": TokenType.ON_CURVE},
        {"name": "CV Vision", "symbol": "CVVSN", "token_type": TokenType.GRADUATED},
        {"name": "Speech Bot", "symbol": "SPCHB", "token_type": TokenType.ON_CURVE},
        {"name": "Lang Sys", "symbol": "LNGS", "token_type": TokenType.ON_CURVE},
        {"name": "Code Gen", "symbol": "CDGN", "token_type": TokenType.GRADUATED},
        {"name": "Test Auto", "symbol": "TSTA", "token_type": TokenType.ON_CURVE},
        {"name": "Debug AI", "symbol": "DBGAI", "token_type": TokenType.ON_CURVE},
        {"name": "Ops Agent", "symbol": "OPSAG", "token_type": TokenType.GRADUATED},
        {"name": "SEC Monitor", "symbol": "SECMN", "token_type": TokenType.ON_CURVE},
        {"name": "DEPLOY Bot", "symbol": "DPBT", "token_type": TokenType.ON_CURVE},
        {"name": "SCALE Agent", "symbol": "SCAG", "token_type": TokenType.GRADUATED},
        {"name": "QUERY DB", "symbol": "QRDB", "token_type": TokenType.ON_CURVE},
        {"name": "INDEX SQL", "symbol": "IDXSQL", "token_type": TokenType.ON_CURVE},
        {"name": "CACHE Mem", "symbol": "CHCM", "token_type": TokenType.GRADUATED},
        {"name": "QUEUE Msg", "symbol": "QMSG", "token_type": TokenType.ON_CURVE},
        {"name": "STREAM Bio", "symbol": "STMBO", "token_type": TokenType.ON_CURVE},
        {"name": "SYNC Live", "symbol": "SYNL", "token_type": TokenType.GRADUATED},
        {"name": "MESH Net", "symbol": "MESH", "token_type": TokenType.ON_CURVE},
        {"name": "EDGE Comp", "symbol": "EDGC", "token_type": TokenType.ON_CURVE},
        {"name": "GRID Infra", "symbol": "GRDINF", "token_type": TokenType.GRADUATED},
        {"name": "NODE Mesh", "symbol": "NODM", "token_type": TokenType.ON_CURVE},
        {"name": "HASH Chain", "symbol": "HSCH", "token_type": TokenType.ON_CURVE},
        {"name": "SIG Verify", "symbol": "SIGV", "token_type": TokenType.GRADUATED},
        {"name": "KEY Exchange", "symbol": "KEYX", "token_type": TokenType.ON_CURVE},
        {"name": "CERT Auth", "symbol": "CERT", "token_type": TokenType.ON_CURVE},
        {"name": "PROOF ZK", "symbol": "PRFZK", "token_type": TokenType.GRADUATED},
        {"name": "STATE Root", "symbol": "STR", "token_type": TokenType.ON_CURVE},
        {"name": "TX Pool", "symbol": "TXPL", "token_type": TokenType.ON_CURVE},
        {"name": "BLOCK Prod", "symbol": "BLKP", "token_type": TokenType.GRADUATED},
        {"name": "VALIDATE", "symbol": "VALD", "token_type": TokenType.ON_CURVE},
        {"name": "MINER AI", "symbol": "MNRA", "token_type": TokenType.ON_CURVE},
        {"name": "STAKE Bot", "symbol": "STKBT", "token_type": TokenType.GRADUATED},
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
