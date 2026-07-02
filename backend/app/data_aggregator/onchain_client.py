"""
On-chain client for Base mainnet.

Interacts with Virtuals Protocol contracts:
- BondingV5: bonding curve state, pricing, graduation
- Virtuals Factory: token registry, creation events
- Agent registry for metadata

Requires BASE_RPC_URL env var (Alchemy, Infura, or public endpoint).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

from web3 import Web3
from web3.types import LogReceipt, TxReceipt

logger = logging.getLogger(__name__)

# BondingV5 ABI (minimal — core read functions)
# Full ABI should be fetched from block explorer or deployment artifacts.
BONDING_V5_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "_token", "type": "address"}],
        "name": "getCurveState",
        "outputs": [
            {"internalType": "uint256", "name": "totalSupply", "type": "uint256"},
            {"internalType": "uint256", "name": "supply", "type": "uint256"},
            {"internalType": "uint256", "name": "virtualsAccumulated", "type": "uint256"},
            {"internalType": "uint256", "name": "virtualsReserve", "type": "uint256"},
            {"internalType": "bool", "name": "isGraduated", "type": "bool"},
        ],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "_token", "type": "address"}],
        "name": "getPrice",
        "outputs": [{"internalType": "uint256", "name": "price", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [{"internalType": "address", "name": "_token", "type": "address"}],
        "name": "getQuote",
        "outputs": [{"internalType": "uint256", "name": "virtualsRequired", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "totalVirtualsSupply",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getVirtualsReserve",
        "outputs": [{"internalType": "uint256", "name": "", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]

# Virtuals Factory ABI (minimal)
FACTORY_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "", "type": "address"}],
        "name": "agentTokens",
        "outputs": [{"internalType": "address", "name": "", "type": "address"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "agent", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "token", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "timestamp", "type": "uint256"},
        ],
        "name": "TokenCreated",
        "type": "event",
    },
]

# BondingV5 events
BONDING_EVENTS = [
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "token", "type": "address"},
            {"indexed": True, "internalType": "address", "name": "buyer", "type": "address"},
            {"indexed": False, "internalType": "uint256", "name": "virtualsPaid", "type": "uint256"},
            {"indexed": False, "internalType": "uint256", "name": "tokensBought", "type": "uint256"},
        ],
        "name": "BondPurchase",
        "type": "event",
    },
    {
        "anonymous": False,
        "inputs": [
            {"indexed": True, "internalType": "address", "name": "token", "type": "address"},
        ],
        "name": "BondGraduated",
        "type": "event",
    },
]


class OnChainClient:
    """Handles all on-chain reads from Base mainnet."""

    def __init__(self, rpc_url: str = "") -> None:
        from app.config import settings

        self.rpc_url = rpc_url or settings.base_rpc_url
        self.w3: Web3 = Web3(Web3.HTTPProvider(self.rpc_url))
        self._factory: Optional[Any] = None
        self._bonding_v5: Optional[Any] = None
        self._virtual_token: Optional[Any] = None
        self._initialized = False

        # Virtuals Protocol contract addresses from config
        self.factory_address = settings.factory_address
        self.bonding_v5_address = settings.bonding_v5_address
        self.virtual_token_address = settings.virtual_token_address

    @property
    def connected(self) -> bool:
        try:
            return self.w3.is_connected()
        except Exception:
            return False

    def _ensure_initialized(self) -> None:
        if self._initialized:
            return
        if self.factory_address and self.factory_address != "0x" * 20:
            self._factory = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.factory_address),
                abi=FACTORY_ABI,
            )
        if self.bonding_v5_address and self.bonding_v5_address != "0x" * 20:
            self._bonding_v5 = self.w3.eth.contract(
                address=Web3.to_checksum_address(self.bonding_v5_address),
                abi=BONDING_V5_ABI,
            )
        self._initialized = True

    # ── Bonding Curve Reads ─────────────────────────────────────────────

    def get_curve_state(self, token_address: str) -> Optional[Dict[str, Any]]:
        """Get full bonding curve state for a token.

        Returns dict with:
            total_supply, supply, virtuals_accumulated,
            virtuals_reserve, is_graduated
        """
        if not self._bonding_v5:
            logger.warning("BondingV5 contract not configured")
            return None

        try:
            checksum = Web3.to_checksum_address(token_address)
            result = self._bonding_v5.functions.getCurveState(checksum).call()
            return {
                "total_supply": int(result[0]),
                "supply": int(result[1]),
                "virtuals_accumulated": int(result[2]),
                "virtuals_reserve": int(result[3]),
                "is_graduated": bool(result[4]),
            }
        except Exception as exc:
            logger.error("get_curve_state error for %s: %s", token_address, exc)
            return None

    def get_price(self, token_address: str) -> Optional[float]:
        """Get current price on the bonding curve (in VIRTUAL per token)."""
        if not self._bonding_v5:
            return None
        try:
            checksum = Web3.to_checksum_address(token_address)
            raw_price = self._bonding_v5.functions.getPrice(checksum).call()
            # Assuming 18 decimals
            return int(raw_price) / 1e18
        except Exception as exc:
            logger.error("get_price error for %s: %s", token_address, exc)
            return None

    def get_quote(self, token_address: str, token_amount: int = 1_000) -> Optional[int]:
        """Get how much VIRTUAL is needed to buy `token_amount` tokens."""
        if not self._bonding_v5:
            return None
        try:
            checksum = Web3.to_checksum_address(token_address)
            result = self._bonding_v5.functions.getQuote(checksum, token_amount).call()
            return int(result)
        except Exception as exc:
            logger.error("get_quote error for %s: %s", token_address, exc)
            return None

    def get_progress_percent(self, token_address: str) -> float:
        """Calculate bonding curve progress (0-100%)."""
        state = self.get_curve_state(token_address)
        if not state:
            return 0.0
        total = state.get("total_supply", 10_000_000)
        supply = state.get("supply", 0)
        if total <= 0:
            return 100.0
        return round((supply / total) * 100.0, 2)

    # ── Factory Reads ───────────────────────────────────────────────────

    def get_agent_token(self, agent_address: str) -> Optional[str]:
        """Map agent address → token contract address via factory."""
        if not self._factory:
            return None
        try:
            checksum = Web3.to_checksum_address(agent_address)
            result = self._factory.functions.agentTokens(checksum).call()
            return Web3.to_checksum_address(result) if result else None
        except Exception:
            return None

    def get_token_created_events(
        self,
        from_block: int = 0,
        to_block: int = 0,
        limit: int = 1000,
    ) -> List[Dict[str, Any]]:
        """Fetch TokenCreated events (newly launched tokens)."""
        if not self._factory:
            return []

        try:
            to_block = to_block or self.w3.eth.block_number
            logs = self._factory.events.TokenCreated().get_logs(
                fromBlock=from_block or (to_block - 50_000),  # ~1 day on Base
                toBlock=to_block,
            )
            events = []
            for log in logs[:limit]:
                events.append({
                    "agent": log.args.agent,
                    "token": log.args.token,
                    "timestamp": int(log.args.timestamp),
                    "block_number": log.blockNumber,
                    "transaction_hash": log.transactionHash.hex(),
                })
            return events
        except Exception as exc:
            logger.error("get_token_created_events error: %s", exc)
            return []

    def get_bonding_events(
        self,
        token_address: str,
        from_block: int = 0,
        to_block: int = 0,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """Fetch BondPurchase / BondGraduation events for a token."""
        if not self._bonding_v5:
            return []

        try:
            checksum = Web3.to_checksum_address(token_address)
            to_block = to_block or self.w3.eth.block_number
            logs = self._bonding_v5.events.BondPurchase().get_logs(
                fromBlock=from_block or (to_block - 50_000),
                toBlock=to_block,
                arguments={"token": checksum},
            )
            events = []
            for log in logs[:limit]:
                events.append({
                    "token": log.args.token,
                    "buyer": log.args.buyer,
                    "virtuals_paid": int(log.args.virtualsPaid),
                    "tokens_bought": int(log.args.tokensBought),
                    "block_number": log.blockNumber,
                })
            return events
        except Exception as exc:
            logger.error("get_bonding_events error: %s", exc)
            return []

    # ── Balance / Treasury ──────────────────────────────────────────────

    def get_balance(self, address: str, token_address: str = "0x" * 20) -> int:
        """Get ETH or ERC-20 token balance of an address."""
        try:
            checksum = Web3.to_checksum_address(address)
            if token_address == "0x" * 20:
                return self.w3.eth.get_balance(checksum)
            token_contract = self.w3.eth.contract(
                address=Web3.to_checksum_address(token_address),
                abi=[{
                    "constant": True,
                    "inputs": [{"name": "_owner", "type": "address"}],
                    "name": "balanceOf",
                    "outputs": [{"name": "balance", "type": "uint256"}],
                    "type": "function",
                }],
            )
            return int(token_contract.functions.balanceOf(checksum).call())
        except Exception as exc:
            logger.error("get_balance error: %s", exc)
            return 0

    # ── Block helpers ───────────────────────────────────────────────────

    def get_current_block(self) -> int:
        return self.w3.eth.block_number

    def get_block_timestamp(self, block_number: int) -> int:
        try:
            block = self.w3.eth.get_block(block_number)
            return block.get("timestamp", 0)
        except Exception:
            return 0

    def close(self) -> None:
        self.w3.provider.disconnect()

    async def __aenter__(self) -> "OnChainClient":
        return self

    async def __aexit__(self, *args: Any) -> None:
        self.close()
