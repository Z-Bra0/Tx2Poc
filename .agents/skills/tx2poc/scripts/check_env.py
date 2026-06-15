from __future__ import annotations

import argparse
import os

ALCHEMY_CHAIN_MAP = {
    "ethereum": "eth-mainnet",
    "polygon": "polygon-mainnet",
    "arbitrum": "arb-mainnet",
    "base": "base-mainnet",
    "optimism": "opt-mainnet",
    "avalanche": "avax-mainnet",
    "bsc": "bnb-mainnet",
}

ETHERSCAN_CHAIN_IDS = {
    "ethereum": 1,
    "optimism": 10,
    "bsc": 56,
    "polygon": 137,
    "fantom": 250,
    "base": 8453,
    "arbitrum": 42161,
    "avalanche": 43114,
}

CHAIN_ALIASES = {
    "eth": "ethereum",
    "mainnet": "ethereum",
    "bnb": "bsc",
    "binance": "bsc",
}

def canonical_chain(chain: str) -> str:
    normalized = chain.lower()
    return CHAIN_ALIASES.get(normalized, normalized)


def check_fetch_env(chain: str) -> None:
    if chain not in ALCHEMY_CHAIN_MAP:
        supported = ", ".join(sorted(ALCHEMY_CHAIN_MAP))
        raise RuntimeError(f"Alchemy fetch unsupported for {chain}. Supported: {supported}")

    if not os.environ.get("ALCHEMY_API_KEY"):
        raise RuntimeError("Missing required environment variable(s): ALCHEMY_API_KEY")


def main() -> int:
    parser = argparse.ArgumentParser(description="Check tx2poc environment variables.")
    parser.add_argument("--chain", required=True, help="Chain name")
    parser.add_argument("--fetch", action="store_true", help="Require ALCHEMY_API_KEY for trace fetching")
    parser.add_argument("--metadata", action="store_true", help="Require ETHERSCAN_API_KEY for on-demand Etherscan curl queries")
    args = parser.parse_args()

    chain = canonical_chain(args.chain)
    if args.metadata and not os.environ.get("ETHERSCAN_API_KEY"):
        raise RuntimeError("Missing required environment variable(s): ETHERSCAN_API_KEY")
    if args.metadata and chain not in ETHERSCAN_CHAIN_IDS:
        supported = ", ".join(sorted(ETHERSCAN_CHAIN_IDS))
        raise RuntimeError(f"Etherscan metadata unsupported for {chain}. Supported: {supported}")
    if args.fetch:
        check_fetch_env(chain)
    else:
        print("Environment preflight ok.")
        return 0
    print("Environment preflight ok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
