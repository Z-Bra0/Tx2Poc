from __future__ import annotations

import argparse
import datetime
import json
import os
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DATA_DIR = SKILL_ROOT / "data"
SELECTORS_PATH = DATA_DIR / "common_signatures_2k.json"
KNOWN_ADDRESSES_PATH = DATA_DIR / "known_addresses.json"

ALCHEMY_CHAIN_MAP = {
    "ethereum": "eth-mainnet",
    "polygon": "polygon-mainnet",
    "arbitrum": "arb-mainnet",
    "base": "base-mainnet",
    "optimism": "opt-mainnet",
    "avalanche": "avax-mainnet",
    "bsc": "bnb-mainnet",
}

# Public Blockscout instances. Each exposes a keyless JSON-RPC proxy at
# `/api/eth-rpc` (tx/receipt/block) and a Parity-style trace at
# `/api/v2/transactions/{hash}/raw-trace`.
BLOCKSCOUT_CHAIN_MAP = {
    "ethereum": "https://eth.blockscout.com",
    "optimism": "https://explorer.optimism.io",
    "base": "https://base.blockscout.com",
    "arbitrum": "https://arbitrum.blockscout.com",
    "polygon": "https://polygon.blockscout.com",
    "gnosis": "https://gnosis.blockscout.com",
}

TRACE_SOURCES = ("auto", "alchemy", "blockscout")

# Parity `callType`/trace `type` -> geth callTracer frame type.
PARITY_CALL_TYPE_MAP = {
    "call": "CALL",
    "callcode": "CALLCODE",
    "delegatecall": "DELEGATECALL",
    "staticcall": "STATICCALL",
}

CHAIN_ALIASES = {
    "eth": "ethereum",
    "mainnet": "ethereum",
    "bnb": "bsc",
    "binance": "bsc",
}

TOKEN_FUNCTIONS = {
    "allowance",
    "approve",
    "balanceOf",
    "decimals",
    "name",
    "symbol",
    "totalSupply",
    "transfer",
    "transferFrom",
}

INFRA_FUNCTIONS = {
    "exactInput",
    "exactOutput",
    "flashLoan",
    "pancakeV3SwapCallback",
    "slot0",
    "swap",
    "token0",
    "token1",
    "uniswapV3SwapCallback",
}

VULNERABLE_HINT_FUNCTIONS = {
    "borrow",
    "claim",
    "deposit",
    "harvest",
    "liquidate",
    "liquidateBorrow",
    "mint",
    "redeem",
    "stake",
    "supply",
    "unstake",
    "withdraw",
}

COLLAPSE_THRESHOLD = 2
MAX_WINDOW = 8
LOOP_DETAIL_MIN_FRAMES = 25
LOOP_ACTION_LIMIT = 14
LOOP_HOT_CALL_LIMIT = 8
MAX_LOOP_SUMMARIES = 80
LOOP_HOTSPOT_LIMIT = 12
READ_SUBTREE_HOT_CALL_LIMIT = 5
READ_SUBTREE_MIN_FRAMES = 10
COMPACT_INTERNAL_DEPTH = 29

LOW_SIGNAL_LOOP_FUNCTIONS = (TOKEN_FUNCTIONS - {"transfer", "transferFrom"}) | {
    "allowance",
    "coins",
    "decimals",
    "getFlashLoanFeePer",
    "getFlashLoanFeePercentage",
    "name",
    "observe",
    "slot0",
    "symbol",
    "token0",
    "token1",
    "totalSupply",
    "virtual_price",
}

LOW_SIGNAL_SUMMARY_FUNCTIONS = LOW_SIGNAL_LOOP_FUNCTIONS | {
    "fulfillBasicOrder_",
    "fulfillBasicOrder_efficient_6GL6yc",
}

READ_SUBTREE_FUNCTIONS = {
    "debt",
    "getAssetPrice",
    "getPrice",
    "getReserveData",
    "getReserveNormalizedIncome",
    "getReserveNormalizedVariableDebt",
    "getUserAccountData",
    "latestAnswer",
    "latestRoundData",
    "price",
    "price_oracle",
    "scaledTotalSupply",
    "virtual_price",
}

SEMANTIC_LOOP_FUNCTIONS = VULNERABLE_HINT_FUNCTIONS | {
    "create_loan",
    "exchange",
    "executeOperation",
    "flash",
    "flashLoan",
    "getAssetPrice",
    "liquidationCall",
    "onFlashLoan",
    "onMorphoFlashLoan",
    "receiveFlashLoan",
    "repay",
    "setUserUseReserveAsCollateral",
    "swap",
    "uniswapV3FlashCall",
    "uniswapV3SwapCallback",
}

ACTION_LIMIT = 1200
CALLBACK_EDGE_LIMIT = 80
CALL_EVIDENCE_LIMIT = 160
CALL_EVIDENCE_RAW_LIMIT = 1024
DELEGATECALL_PAIR_LIMIT = 120
DELEGATECALL_PAIR_FRAME_LIMIT = 20

ACTION_FUNCTIONS = SEMANTIC_LOOP_FUNCTIONS | {
    "approve",
    "transfer",
    "transferFrom",
}

STATIC_INPUT_ARGS = {
    "allowance": [("owner", "address"), ("spender", "address")],
    "approve": [("spender", "address"), ("amount", "uint256")],
    "balanceOf": [("account", "address")],
    "transfer": [("to", "address"), ("amount", "uint256")],
    "transferFrom": [("from", "address"), ("to", "address"), ("amount", "uint256")],
    "getPoolTokens": [("pool_id", "bytes32")],
    "create_loan": [("collateral_amount", "uint256"), ("debt_amount", "uint256"), ("n", "uint256")],
    "exchange": [("i", "int128"), ("j", "int128"), ("dx", "uint256"), ("min_dy", "uint256"), ("receiver", "address")],
    "deposit": [("asset", "address"), ("amount", "uint256"), ("on_behalf_of", "address"), ("referral_code", "uint16")],
    "setUserUseReserveAsCollateral": [("asset", "address"), ("use_as_collateral", "bool")],
    "borrow": [("asset", "address"), ("amount", "uint256"), ("interest_rate_mode", "uint256"), ("referral_code", "uint16"), ("on_behalf_of", "address")],
    "withdraw": [("asset_or_amount", "uint256"), ("amount", "uint256"), ("to", "address")],
    "liquidationCall": [("collateral_asset", "address"), ("debt_asset", "address"), ("user", "address"), ("debt_to_cover", "uint256"), ("receive_a_token", "bool")],
    "repay": [("asset", "address"), ("amount", "uint256"), ("rate_mode", "uint256"), ("on_behalf_of", "address")],
    "flash": [("recipient", "address"), ("amount0", "uint256"), ("amount1", "uint256")],
    "onMorphoFlashLoan": [("amount", "uint256")],
    "onFlashLoan": [("initiator", "address"), ("token", "address"), ("amount", "uint256"), ("fee", "uint256")],
    "uniswapV3FlashCallback": [("fee0", "uint256"), ("fee1", "uint256")],
    "uniswapV3SwapCallback": [("amount0_delta", "int256"), ("amount1_delta", "int256")],
}

STATIC_OUTPUT_ARGS = {
    "allowance": [("allowance", "uint256")],
    "approve": [("success", "bool")],
    "balanceOf": [("balance", "uint256")],
    "decimals": [("decimals", "uint8")],
    "getPoolId": [("pool_id", "bytes32")],
    "getVault": [("vault", "address")],
    "token0": [("token0", "address")],
    "token1": [("token1", "address")],
    "totalSupply": [("total_supply", "uint256")],
    "transfer": [("success", "bool")],
    "transferFrom": [("success", "bool")],
}

def find_repo_root(start: Path) -> Path:
    for path in (start, *start.parents):
        if (path / "foundry.toml").exists() and (path / "cases").exists():
            return path.resolve()
    return start.resolve()


REPO_ROOT = find_repo_root(Path.cwd())
CASE_ROOT = REPO_ROOT / "cases"


def set_workspace_root(workspace_root: str | None) -> None:
    global REPO_ROOT, CASE_ROOT
    if workspace_root:
        REPO_ROOT = Path(workspace_root).expanduser().resolve()
    else:
        REPO_ROOT = find_repo_root(Path.cwd())
    CASE_ROOT = REPO_ROOT / "cases"


def canonical_chain(chain: str) -> str:
    normalized = chain.lower()
    return CHAIN_ALIASES.get(normalized, normalized)


def resolve_case_dir(output_dir: str) -> Path:
    output_path = Path(output_dir).expanduser()
    if not output_path.is_absolute():
        output_path = REPO_ROOT / output_path
    output_path = output_path.resolve()
    if output_path.parent != CASE_ROOT.resolve():
        raise RuntimeError("--output-dir must be a direct child of cases/")
    return output_path


def read_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)


def require_files(paths: list[Path]) -> None:
    for path in paths:
        if not path.exists():
            raise RuntimeError(f"{path.name} not found at {path}")


def json_http_post(url: str, payload: Any, timeout: int = 120) -> Any:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "User-Agent": "tx2poc/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def json_http_get(url: str, timeout: int = 120) -> Any:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "tx2poc/1.0",
        },
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error: {exc.reason}") from exc


def rpc_url(chain: str) -> str:
    chain = canonical_chain(chain)
    api_key = os.environ.get("ALCHEMY_API_KEY")
    if not api_key:
        raise RuntimeError("ALCHEMY_API_KEY not set in environment")

    slug = ALCHEMY_CHAIN_MAP.get(chain)
    if not slug:
        supported = ", ".join(sorted(ALCHEMY_CHAIN_MAP))
        raise RuntimeError(f"Unsupported chain: {chain}. Supported: {supported}")
    return f"https://{slug}.g.alchemy.com/v2/{api_key}"


def resolve_source(source: str | None, chain: str | None = None) -> str:
    normalized = (source or "auto").lower()
    if normalized not in TRACE_SOURCES:
        supported = ", ".join(TRACE_SOURCES)
        raise RuntimeError(f"Unsupported source: {source}. Choose from {supported}")
    if normalized != "auto":
        return normalized
    if os.environ.get("ALCHEMY_API_KEY"):
        if chain and canonical_chain(chain) not in ALCHEMY_CHAIN_MAP:
            return "blockscout"
        return "alchemy"
    return "blockscout"


def blockscout_base(chain: str) -> str:
    chain = canonical_chain(chain)
    base = BLOCKSCOUT_CHAIN_MAP.get(chain)
    if not base:
        supported = ", ".join(sorted(BLOCKSCOUT_CHAIN_MAP))
        raise RuntimeError(f"Blockscout source unsupported for chain: {chain}. Supported: {supported}")
    return base


def rpc_endpoint(chain: str, source: str) -> str:
    if source == "blockscout":
        return f"{blockscout_base(chain)}/api/eth-rpc"
    return rpc_url(chain)


def parity_frame_type(entry: dict[str, Any]) -> str:
    trace_type = (entry.get("type") or "call").lower()
    if trace_type == "call":
        call_type = (entry.get("action", {}).get("callType") or "call").lower()
        return PARITY_CALL_TYPE_MAP.get(call_type, call_type.upper())
    if trace_type == "create":
        return "CREATE"
    if trace_type == "suicide":
        return "SELFDESTRUCT"
    return trace_type.upper()


def parity_entry_to_node(entry: dict[str, Any]) -> dict[str, Any]:
    action = entry.get("action") or {}
    result = entry.get("result") or {}
    node: dict[str, Any] = {
        "type": parity_frame_type(entry),
        "from": action.get("from") or action.get("address"),
        "to": action.get("to") or action.get("refundAddress") or result.get("address"),
        "value": action.get("value") or action.get("balance") or "0x0",
        "gas": action.get("gas", "0x0"),
        "gasUsed": result.get("gasUsed", "0x0"),
        "input": action.get("input") or action.get("init") or "0x",
        "output": result.get("output") or result.get("code"),
        "calls": [],
    }
    if entry.get("error"):
        node["error"] = entry["error"]
    return node


def parity_trace_to_calltracer(traces: Any) -> dict[str, Any]:
    if isinstance(traces, dict):
        message = traces.get("message") or traces.get("error") or json.dumps(traces)[:200]
        raise RuntimeError(f"Blockscout raw-trace error: {message}")
    if not isinstance(traces, list) or not traces:
        raise RuntimeError("Blockscout returned no trace frames (raw-trace empty)")

    ordered = sorted(traces, key=lambda entry: entry.get("traceAddress") or [])
    nodes: dict[tuple[int, ...], dict[str, Any]] = {}
    root: dict[str, Any] | None = None
    for entry in ordered:
        path = tuple(entry.get("traceAddress") or [])
        node = parity_entry_to_node(entry)
        nodes[path] = node
        if not path:
            root = node
            continue
        parent = nodes.get(path[:-1])
        if parent is None:
            raise RuntimeError(f"Blockscout trace missing parent for path {list(path)}")
        parent["calls"].append(node)
    if root is None:
        raise RuntimeError("Blockscout trace has no root frame (empty traceAddress)")
    return root


def rpc_call(url: str, method: str, params: list[Any]) -> Any:
    payload = json_http_post(url, {"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
    if "error" in payload:
        message = payload["error"].get("message", "unknown RPC error")
        raise RuntimeError(f"RPC error [{method}]: {message}")
    if "result" not in payload:
        raise RuntimeError(f"RPC returned no result for {method}")
    return payload["result"]


def evidence_dir(case_dir: Path) -> Path:
    return case_dir / "evidence"


def fetch_call_trace(chain: str, tx_hash: str, source: str, url: str) -> dict[str, Any]:
    if source == "blockscout":
        print("[4/4] raw-trace (Blockscout) ...")
        raw_url = f"{blockscout_base(chain)}/api/v2/transactions/{tx_hash}/raw-trace"
        return parity_trace_to_calltracer(json_http_get(raw_url))
    print("[4/4] debug_traceTransaction (callTracer) ...")
    return rpc_call(url, "debug_traceTransaction", [tx_hash, {"tracer": "callTracer"}])


def fetch_trace(chain: str, tx_hash: str, artifact_dir: Path, force: bool, source: str) -> None:
    raw_path = artifact_dir / "trace.raw.json"
    tx_path = artifact_dir / "tx.json"
    receipt_path = artifact_dir / "receipt.json"
    block_path = artifact_dir / "block.json"
    metadata_paths = [tx_path, receipt_path, block_path]
    if raw_path.exists() and all(path.exists() for path in metadata_paths) and not force:
        print(f"Skipping fetch; using existing {raw_path}")
        return

    url = rpc_endpoint(chain, source)
    print(f"Source:  {source}")
    print(f"Chain:   {canonical_chain(chain)}")
    print(f"Tx:      {tx_hash}")

    print("[1/4] eth_getTransactionByHash ...")
    tx_data = rpc_call(url, "eth_getTransactionByHash", [tx_hash])
    if not tx_data:
        raise RuntimeError(f"Transaction not found: {tx_hash}")

    print("[2/4] eth_getTransactionReceipt ...")
    receipt = rpc_call(url, "eth_getTransactionReceipt", [tx_hash])

    print("[3/4] eth_getBlockByNumber ...")
    block = rpc_call(url, "eth_getBlockByNumber", [tx_data["blockNumber"], False])

    write_json(tx_path, tx_data)
    write_json(receipt_path, receipt)
    write_json(block_path, block)
    if raw_path.exists() and not force:
        print(f"Skipping trace fetch; using existing {raw_path}")
        return

    trace = fetch_call_trace(chain, tx_hash, source, url)
    write_json(raw_path, trace)
    print(f"trace.raw.json written ({raw_path.stat().st_size / 1024:.1f} KB)")


def selector_from_input(input_data: str | None) -> str | None:
    return input_data[:10] if input_data and len(input_data) >= 10 else None


def flatten_frame(
    raw: dict[str, Any],
    parent_id: str | None,
    depth: int,
    counter: list[int],
    frames: list[dict[str, Any]],
) -> None:
    frame_id = f"c{counter[0]:04d}"
    counter[0] += 1
    frame = {
        "id": frame_id,
        "parentId": parent_id,
        "depth": depth,
        "seqIndex": len(frames),
        "type": raw.get("type", "CALL"),
        "from": raw["from"],
        "to": raw.get("to"),
        "value": raw.get("value", "0x0"),
        "gas": raw.get("gas", "0x0"),
        "gasUsed": raw.get("gasUsed", "0x0"),
        "input": raw.get("input", ""),
        "output": raw.get("output"),
        "error": raw.get("error"),
        "selector": selector_from_input(raw.get("input")),
        "childCount": len(raw.get("calls", [])),
    }
    frames.append(frame)
    for child in raw.get("calls", []):
        flatten_frame(child, frame_id, depth + 1, counter, frames)


def normalize_trace(artifact_dir: Path) -> list[dict[str, Any]]:
    raw_path = artifact_dir / "trace.raw.json"
    require_files([raw_path])
    raw = read_json(raw_path)
    frames: list[dict[str, Any]] = []
    flatten_frame(raw, None, 0, [0], frames)
    print(f"normalized trace ({len(frames)} frames, memory)")
    return frames


def resolve_selectors(case_dir: Path, frames: list[dict[str, Any]]) -> dict[str, str]:
    require_files([SELECTORS_PATH])
    known = read_json(SELECTORS_PATH)
    seen: set[str] = set()
    unique_selectors: list[str] = []
    for frame in frames:
        selector = frame.get("selector")
        if selector and selector not in seen:
            seen.add(selector)
            unique_selectors.append(selector)

    selector_map = {selector: known[selector] for selector in unique_selectors if selector in known}
    print(f"selectors resolved ({len(selector_map)}/{len(unique_selectors)}, memory)")
    return selector_map


def hex_to_int(hex_value: str | None) -> int:
    if not hex_value or hex_value in {"0x", "0x0"}:
        return 0
    try:
        return int(hex_value, 16)
    except ValueError:
        return 0


def hex_to_eth(hex_value: str | None) -> float:
    return hex_to_int(hex_value) / 10**18


def format_native_value(hex_value: str | None) -> str:
    value = hex_to_int(hex_value)
    if value == 0:
        return ""
    if value < 10**14:
        return f" {value}wei"
    return f" {value / 10**18:.4f}ETH"


def short_addr(address: str | None) -> str:
    return address[:10] if address else " " * 10


def normalized_addr(address: str | None) -> str:
    return address.lower() if address else ""


def selector_name(selector_map: dict[str, str], selector: str | None) -> str:
    if not selector:
        return "none"
    signature = selector_map.get(selector)
    return signature.split("(", 1)[0] if signature else selector


def frame_function(frame: dict[str, Any], selector_map: dict[str, str]) -> str:
    return selector_name(selector_map, frame.get("selector"))


def frame_key(frame: dict[str, Any]) -> str:
    return f"{frame.get('type', '')}|{frame.get('to') or ''}|{frame.get('selector') or ''}"


def call_label(frame: dict[str, Any], selector_map: dict[str, str], function_name: str | None = None) -> str:
    call_type = frame.get("type") or "CALL"
    if function_name is None:
        function_name = frame_function(frame, selector_map)
    target = normalized_addr(frame.get("to")) or "0x"
    return f"{call_type} {function_name}@{target}"


def append_unique(values: list[str], value: str, limit: int | None = None) -> None:
    if value and value not in values and (limit is None or len(values) < limit):
        values.append(value)


def calldata_words(input_data: str | None) -> list[str]:
    if not input_data or len(input_data) < 10:
        return []
    data = input_data[10:]
    return [data[index : index + 64] for index in range(0, len(data), 64) if len(data[index : index + 64]) == 64]


def hex_words(hex_data: str | None) -> list[str]:
    if not hex_data or hex_data in {"0x", "0x0"}:
        return []
    data = hex_data[2:] if hex_data.startswith("0x") else hex_data
    return [data[index : index + 64] for index in range(0, len(data), 64) if len(data[index : index + 64]) == 64]


def decode_static_value(word: str, abi_type: str) -> Any:
    if abi_type == "address":
        return "0x" + word[-40:].lower()
    if abi_type == "bytes32":
        return "0x" + word
    if abi_type == "bool":
        return bool(int(word, 16))
    if abi_type.startswith("uint"):
        return int(word, 16)
    if abi_type.startswith("int"):
        value = int(word, 16)
        bits = int(abi_type[3:] or "256")
        sign_bit = 1 << (bits - 1)
        return value - (1 << bits) if value & sign_bit else value
    return "0x" + word


def decode_static_args(frame: dict[str, Any], function_name: str) -> dict[str, Any]:
    specs = STATIC_INPUT_ARGS.get(function_name)
    if not specs:
        return {}
    words = calldata_words(frame.get("input"))
    decoded: dict[str, Any] = {}
    for index, (name, abi_type) in enumerate(specs):
        if index >= len(words):
            break
        decoded[name] = decode_static_value(words[index], abi_type)
    if function_name == "withdraw" and len(words) == 1:
        decoded = {"amount": decoded.get("asset_or_amount")}
    elif function_name == "withdraw" and "asset_or_amount" in decoded:
        decoded["asset"] = decoded.pop("asset_or_amount")
    return decoded


def evidence_signature(selector_map: dict[str, str], selector: str | None) -> str | None:
    if not selector:
        return None
    return selector_map.get(selector)


def evidence_function_name(selector_map: dict[str, str], selector: str | None) -> str:
    signature = evidence_signature(selector_map, selector)
    return signature.split("(", 1)[0] if signature else selector_name(selector_map, selector)


def decode_output(frame: dict[str, Any], selector_map: dict[str, str]) -> dict[str, Any]:
    function_name = evidence_function_name(selector_map, frame.get("selector"))
    specs = STATIC_OUTPUT_ARGS.get(function_name)
    if not specs:
        return {}

    words = hex_words(frame.get("output"))
    decoded: dict[str, Any] = {}
    for index, (name, abi_type) in enumerate(specs):
        if index >= len(words):
            break
        decoded[name] = decode_static_value(words[index], abi_type)
    return decoded


def clipped_raw(value: str, limit: int = CALL_EVIDENCE_RAW_LIMIT) -> dict[str, Any]:
    if len(value) <= limit:
        return {"value": value, "truncated": False}
    return {"value": value[:limit], "truncated": True}


def ancestor_path(frame: dict[str, Any], by_id: dict[str, dict[str, Any]], limit: int = 6) -> list[str]:
    ancestors: list[str] = []
    current = frame
    while current.get("parentId") is not None and len(ancestors) < limit:
        parent = by_id.get(str(current.get("parentId")))
        if not parent:
            break
        ancestors.append(str(parent["id"]))
        current = parent
    ancestors.reverse()
    return ancestors


def format_frame(frame: dict[str, Any], selector_map: dict[str, str], collapse: dict[str, Any] | None = None) -> str:
    frame_id = f"[{frame['id']}..{collapse['lastId']}]" if collapse else f"[{frame['id']}]"
    depth = f"d={frame['depth']}".ljust(5)
    call_type = frame.get("type", "")[:10].ljust(10)
    route = f"{short_addr(frame.get('from'))}->{short_addr(frame.get('to'))}"
    selector = selector_name(selector_map, frame.get("selector"))[:18].ljust(18)
    gas = f"gas={hex_to_int(frame.get('gasUsed'))}".ljust(12)
    value_tag = format_native_value(frame.get("value"))
    loop_tag = ""
    if collapse:
        pattern = f" pattern({collapse['windowSize']})" if collapse.get("windowSize", 1) > 1 else ""
        frame_count = f" frames={collapse['totalFrames']}" if collapse.get("totalFrames") else ""
        first_count = f" first={collapse['firstIterationFrames']}" if collapse.get("firstIterationFrames") else ""
        loop_tag = f"  x{collapse['count']}{pattern} [LOOP]{frame_count}{first_count}"
    error_tag = f"  ERR={frame['error']}" if frame.get("error") else ""
    return f"{frame_id.ljust(18)} {depth} {call_type} {route}  {selector}  {gas}{value_tag}{loop_tag}{error_tag}"


def compact_calls(calls: list[dict[str, Any]], limit: int = READ_SUBTREE_HOT_CALL_LIMIT) -> str:
    if not calls:
        return ""
    values = [f"{item['call']} x{item['count']}" for item in calls[:limit]]
    if len(calls) > limit:
        values.append(f"+{len(calls) - limit} more")
    return ", ".join(values)


def format_subtree_summary(
    frame: dict[str, Any],
    selector_map: dict[str, str],
    frame_count: int,
    hot_calls: list[dict[str, Any]],
) -> str:
    hot = compact_calls(hot_calls)
    summary = f"  [READ-SUBTREE frames={frame_count}"
    if hot:
        summary += f" hot={hot}"
    summary += "]"
    return format_frame(frame, selector_map) + summary


def is_zero_selector(frame: dict[str, Any]) -> bool:
    return frame.get("selector") == "0x00000000"


def is_unknown_function(function_name: str) -> bool:
    return function_name.startswith("0x")


def should_omit_frame(frame: dict[str, Any], selector_map: dict[str, str]) -> bool:
    if frame.get("error"):
        return False
    function_name = frame_function(frame, selector_map)
    call_type = frame.get("type")
    if is_zero_selector(frame) or function_name.startswith("fulfillBasicOrder"):
        return True
    if function_name in LOW_SIGNAL_SUMMARY_FUNCTIONS:
        return True
    depth = int(frame.get("depth", 0))
    if is_unknown_function(function_name) and depth >= COMPACT_INTERNAL_DEPTH:
        if call_type in {"STATICCALL", "DELEGATECALL"}:
            return True
        if call_type == "CALL" and hex_to_int(frame.get("value")) == 0:
            return True
    return call_type == "STATICCALL" and function_name in LOW_SIGNAL_LOOP_FUNCTIONS


def should_summarize_read_subtree(frame: dict[str, Any], selector_map: dict[str, str], child_count: int) -> bool:
    if frame.get("error") or child_count == 0:
        return False
    function_name = frame_function(frame, selector_map)
    if function_name in READ_SUBTREE_FUNCTIONS and child_count >= READ_SUBTREE_MIN_FRAMES:
        return True
    return frame.get("type") == "STATICCALL" and child_count >= 4


def should_omit_small_read_frame(frame: dict[str, Any], selector_map: dict[str, str], child_count: int) -> bool:
    if frame.get("error"):
        return False
    function_name = frame_function(frame, selector_map)
    return frame.get("type") == "STATICCALL" and function_name in READ_SUBTREE_FUNCTIONS and child_count < READ_SUBTREE_MIN_FRAMES


def should_inline_delegate_shell(frame: dict[str, Any], by_id: dict[str, dict[str, Any]], selector_map: dict[str, str]) -> bool:
    if frame.get("type") != "DELEGATECALL" or frame.get("error"):
        return False
    parent = by_id.get(str(frame.get("parentId")))
    if not parent or parent.get("selector") != frame.get("selector"):
        return False
    function_name = frame_function(frame, selector_map)
    if function_name in LOW_SIGNAL_SUMMARY_FUNCTIONS:
        return True
    return function_name in SEMANTIC_LOOP_FUNCTIONS or function_name in VULNERABLE_HINT_FUNCTIONS


def count_window_reps(child_ids: list[str], by_id: dict[str, dict[str, Any]], start: int, window_size: int) -> int:
    if start + window_size > len(child_ids):
        return 1
    window = [frame_key(by_id[frame_id]) for frame_id in child_ids[start : start + window_size]]
    count = 1
    pos = start + window_size
    while pos + window_size <= len(child_ids):
        next_window = [frame_key(by_id[frame_id]) for frame_id in child_ids[pos : pos + window_size]]
        if window != next_window:
            break
        count += 1
        pos += window_size
    return count


def find_repetition(child_ids: list[str], by_id: dict[str, dict[str, Any]], start: int) -> dict[str, int] | None:
    remaining = len(child_ids) - start
    best: dict[str, int] | None = None
    for window_size in range(1, min(MAX_WINDOW, remaining // 2) + 1):
        count = count_window_reps(child_ids, by_id, start, window_size)
        if count >= COLLAPSE_THRESHOLD:
            total = window_size * count
            if best is None or total > best["total"]:
                best = {"windowSize": window_size, "count": count, "total": total}
    return None if best is None else {"windowSize": best["windowSize"], "count": best["count"]}


def subtree_ids(frame_id: str, children_map: dict[str, list[str]], cache: dict[str, list[str]]) -> list[str]:
    cached = cache.get(frame_id)
    if cached is not None:
        return cached
    collected = [frame_id]
    for child_id in children_map.get(frame_id, []):
        collected.extend(subtree_ids(child_id, children_map, cache))
    cache[frame_id] = collected
    return collected


def child_window_subtree_ids(
    child_ids: list[str],
    children_map: dict[str, list[str]],
    cache: dict[str, list[str]],
    start: int,
    window_size: int,
    count: int = 1,
) -> list[str]:
    collected: list[str] = []
    for child_id in child_ids[start : start + window_size * count]:
        collected.extend(subtree_ids(child_id, children_map, cache))
    return collected


def child_window_subtree_frame_count(
    child_ids: list[str],
    children_map: dict[str, list[str]],
    cache: dict[str, list[str]],
    start: int,
    window_size: int,
    count: int = 1,
) -> int:
    return sum(
        len(subtree_ids(child_id, children_map, cache))
        for child_id in child_ids[start : start + window_size * count]
    )


def semantic_label(frame: dict[str, Any], selector_map: dict[str, str]) -> str | None:
    selector = frame.get("selector")
    if not selector:
        return None
    function_name = frame_function(frame, selector_map)
    if selector == "0x00000000" or function_name.startswith("fulfillBasicOrder"):
        return None
    if function_name in LOW_SIGNAL_LOOP_FUNCTIONS:
        return None
    call_type = frame.get("type")
    if call_type == "STATICCALL" and function_name not in SEMANTIC_LOOP_FUNCTIONS:
        return None
    return call_label(frame, selector_map, function_name)


def ordered_counts(labels: list[str], limit: int) -> list[str]:
    counts = Counter(labels)
    seen: set[str] = set()
    ordered: list[str] = []
    for label in labels:
        if label in seen:
            continue
        seen.add(label)
        count = counts[label]
        ordered.append(f"{label} x{count}" if count > 1 else label)
        if len(ordered) >= limit:
            remaining = len(counts) - len(ordered)
            if remaining > 0:
                ordered.append(f"... +{remaining} more")
            break
    return ordered


def hot_call_counts(frames: list[dict[str, Any]], selector_map: dict[str, str]) -> list[dict[str, Any]]:
    counts: Counter[str] = Counter()
    for frame in frames:
        selector = frame.get("selector")
        if not selector:
            continue
        function_name = frame_function(frame, selector_map)
        if selector == "0x00000000" or function_name.startswith("fulfillBasicOrder") or function_name == "none":
            continue
        if function_name in LOW_SIGNAL_LOOP_FUNCTIONS:
            continue
        counts[call_label(frame, selector_map, function_name)] += 1
    return [{"call": call, "count": count} for call, count in counts.most_common(LOOP_HOT_CALL_LIMIT)]


def loop_detail(
    child_ids: list[str],
    by_id: dict[str, dict[str, Any]],
    children_map: dict[str, list[str]],
    selector_map: dict[str, str],
    subtree_cache: dict[str, list[str]],
    start: int,
    window_size: int,
    count: int,
    last_id: str,
) -> dict[str, Any] | None:
    first_ids = child_window_subtree_ids(child_ids, children_map, subtree_cache, start, window_size)
    total_frame_count = child_window_subtree_frame_count(child_ids, children_map, subtree_cache, start, window_size, count)
    first_child_ids = set(child_ids[start : start + window_size])
    first_child_frames = [by_id[frame_id] for frame_id in child_ids[start : start + window_size]]
    first_frames = [by_id[frame_id] for frame_id in first_ids]
    primary_action_frames: list[dict[str, Any]] = []
    primary_action_labels: list[str] = []
    for frame in first_child_frames:
        label = semantic_label(frame, selector_map)
        if label:
            primary_action_frames.append(frame)
            primary_action_labels.append(label)

    nested_action_frames: list[dict[str, Any]] = []
    nested_action_labels: list[str] = []
    for frame in first_frames:
        if frame.get("id") in first_child_ids:
            continue
        label = semantic_label(frame, selector_map)
        if label:
            nested_action_frames.append(frame)
            nested_action_labels.append(label)

    action_frames = primary_action_frames + nested_action_frames
    action_labels = primary_action_labels + nested_action_labels
    actions = ordered_counts(action_labels, LOOP_ACTION_LIMIT)
    hot_calls = hot_call_counts(first_frames, selector_map)

    has_semantic_action = any(frame_function(frame, selector_map) in SEMANTIC_LOOP_FUNCTIONS for frame in action_frames)
    if total_frame_count < LOOP_DETAIL_MIN_FRAMES and not has_semantic_action:
        return None

    first_id = child_ids[start]
    first_last_id = first_ids[-1] if first_ids else first_id
    summary = {
        "range": f"{first_id}..{last_id}",
        "parent_id": by_id[first_id].get("parentId"),
        "depth": by_id[first_id].get("depth"),
        "count": count,
        "window_size": window_size,
        "sibling_frames": window_size * count,
        "total_frames": total_frame_count,
        "first_iteration_frames": len(first_frames),
        "first_iteration_range": f"{first_id}..{first_last_id}",
        "actions": actions,
        "hot_calls": hot_calls,
    }

    indent = "  " * int(by_id[first_id].get("depth", 0))
    detail_lines = [
        f"  {indent}| loop detail: total_frames={total_frame_count} first_iter_frames={len(first_frames)} first_iter={first_id}..{first_last_id}",
    ]
    if actions:
        detail_lines.append(clip_text(f"  {indent}| loop actions: {' -> '.join(actions)}"))
    if hot_calls:
        hot = ", ".join(f"{item['call']} x{item['count']}" for item in hot_calls)
        detail_lines.append(clip_text(f"  {indent}| loop hot calls: {hot}"))
    return {"lines": detail_lines, "summary": summary}


def clip_text(value: str, limit: int = 220) -> str:
    if len(value) <= limit:
        return value
    return value[: limit - 3] + "..."


def format_loop_hotspots(loop_summaries: list[dict[str, Any]]) -> list[str]:
    if not loop_summaries:
        return []
    ordered = sorted(loop_summaries, key=lambda item: int(item.get("total_frames", 0)), reverse=True)
    lines = [
        "# Loop Hotspots",
        "# Major repeated subtrees, sorted by collapsed frame count.",
        "# Format: range repeat window frames first_iter actions",
    ]
    for item in ordered[:LOOP_HOTSPOT_LIMIT]:
        actions = " -> ".join(str(action) for action in item.get("actions", [])[:6]) or "none"
        line = (
            f"# - {item.get('range')} x{item.get('count')} window={item.get('window_size')} "
            f"frames={item.get('total_frames')} first={item.get('first_iteration_range')} actions={actions}"
        )
        lines.append(clip_text(line))
    lines.append("")
    return lines


def process_children(
    child_ids: list[str],
    by_id: dict[str, dict[str, Any]],
    children_map: dict[str, list[str]],
    selector_map: dict[str, str],
    lines: list[str],
    loop_summaries: list[dict[str, Any]],
    subtree_cache: dict[str, list[str]],
) -> None:
    index = 0
    while index < len(child_ids):
        repetition = find_repetition(child_ids, by_id, index)
        if repetition:
            window_size = repetition["windowSize"]
            count = repetition["count"]
            first_id = child_ids[index]
            last_id = child_ids[index + window_size * count - 1]
            detail = loop_detail(
                child_ids,
                by_id,
                children_map,
                selector_map,
                subtree_cache,
                index,
                window_size,
                count,
                last_id,
            )
            collapse = {"count": count, "lastId": last_id, "windowSize": window_size}
            if detail:
                summary = detail["summary"]
                collapse["totalFrames"] = summary["total_frames"]
                collapse["firstIterationFrames"] = summary["first_iteration_frames"]
            if not detail and should_omit_frame(by_id[first_id], selector_map):
                index += window_size * count
                continue
            lines.append(format_frame(by_id[first_id], selector_map, collapse))
            if detail:
                lines.extend(detail["lines"])
                if len(loop_summaries) < MAX_LOOP_SUMMARIES:
                    loop_summaries.append(detail["summary"])
            if window_size > 1:
                for offset in range(1, window_size):
                    frame = by_id[child_ids[index + offset]]
                    if should_omit_frame(frame, selector_map):
                        continue
                    indent = "  " * frame["depth"]
                    lines.append(f"  {indent}| {format_frame(frame, selector_map)}")
            index += window_size * count
        else:
            walk(child_ids[index], by_id, children_map, selector_map, lines, loop_summaries, subtree_cache)
            index += 1


def walk(
    frame_id: str,
    by_id: dict[str, dict[str, Any]],
    children_map: dict[str, list[str]],
    selector_map: dict[str, str],
    lines: list[str],
    loop_summaries: list[dict[str, Any]],
    subtree_cache: dict[str, list[str]],
) -> None:
    frame = by_id[frame_id]
    descendant_ids = subtree_ids(frame_id, children_map, subtree_cache)
    child_count = len(descendant_ids) - 1
    if should_inline_delegate_shell(frame, by_id, selector_map):
        process_children(children_map.get(frame_id, []), by_id, children_map, selector_map, lines, loop_summaries, subtree_cache)
        return
    if should_summarize_read_subtree(frame, selector_map, child_count):
        descendant_frames = [by_id[item] for item in descendant_ids[1:]]
        lines.append(format_subtree_summary(frame, selector_map, child_count, hot_call_counts(descendant_frames, selector_map)))
        return
    if should_omit_frame(frame, selector_map) or should_omit_small_read_frame(frame, selector_map, child_count):
        return
    lines.append(format_frame(frame, selector_map))
    process_children(children_map.get(frame_id, []), by_id, children_map, selector_map, lines, loop_summaries, subtree_cache)


def write_summary_and_index(artifact_dir: Path, chain: str, tx_hash: str, frames: list[dict[str, Any]], selector_map: dict[str, str]) -> dict[str, Any]:
    by_id = {frame["id"]: frame for frame in frames}
    children_map: dict[str, list[str]] = defaultdict(list)
    by_address: dict[str, list[str]] = defaultdict(list)
    by_selector: dict[str, list[str]] = defaultdict(list)
    loop_summaries: list[dict[str, Any]] = []
    subtree_cache: dict[str, list[str]] = {}
    for frame in frames:
        parent_id = frame.get("parentId")
        if parent_id is not None:
            children_map[parent_id].append(frame["id"])
        target = normalized_addr(frame.get("to"))
        if target:
            by_address[target].append(frame["id"])
        if frame.get("selector"):
            by_selector[frame["selector"]].append(frame["id"])

    max_depth = max((frame["depth"] for frame in frames), default=0)
    index_doc = {
        "totalFrames": len(frames),
        "maxDepth": max_depth,
        "uniqueAddresses": len(by_address),
        "uniqueSelectors": len(by_selector),
        "byAddress": dict(by_address),
        "bySelector": dict(by_selector),
    }

    root = next((frame for frame in frames if frame.get("parentId") is None), None)
    if not root:
        raise RuntimeError("No root frame found in normalized trace.")

    header_lines = [
        "# Trace Summary",
        f"# Tx:     {tx_hash}",
        f"# Chain:  {chain}",
        f"# Frames: {len(frames)}  MaxDepth: {max_depth}  Addresses: {index_doc['uniqueAddresses']}",
        "# Format: [id] depth type from->to selector gasUsed [value] [xN LOOP]",
        f"# Collapse threshold: {COLLAPSE_THRESHOLD} consecutive identical (type,to,selector)",
        "",
    ]
    body_lines: list[str] = []
    walk(root["id"], by_id, children_map, selector_map, body_lines, loop_summaries, subtree_cache)
    lines = header_lines + format_loop_hotspots(loop_summaries) + body_lines
    (artifact_dir / "trace.summary.txt").write_text("\n".join(lines), encoding="utf-8")
    print(f"trace.summary.txt ({len(lines)} lines from {len(frames)} frames)")
    index_doc["loopSummaries"] = loop_summaries
    return index_doc


def build_call_evidence(frames: list[dict[str, Any]], selector_map: dict[str, str]) -> list[dict[str, Any]]:
    by_id = {frame["id"]: frame for frame in frames}
    evidence: list[dict[str, Any]] = []
    for frame in frames:
        output = frame.get("output")
        if not output or output in {"0x", "0x0"}:
            continue

        selector = frame.get("selector")
        function_name = evidence_function_name(selector_map, selector)
        output_decoded = decode_output(frame, selector_map)
        if function_name in {"approve", "transfer", "transferFrom"} and set(output_decoded) == {"success"}:
            continue

        raw = clipped_raw(output)
        item = {
            "frame": frame.get("id"),
            "parent": frame.get("parentId"),
            "ancestors": ancestor_path(frame, by_id),
            "seq_index": frame.get("seqIndex"),
            "depth": frame.get("depth"),
            "type": frame.get("type"),
            "from": normalized_addr(frame.get("from")),
            "to": normalized_addr(frame.get("to")),
            "selector": selector,
            "signature": evidence_signature(selector_map, selector),
            "function": function_name,
            "input_decoded": decode_static_args(frame, function_name),
            "output_raw": raw["value"],
            "output_truncated": raw["truncated"],
        }
        if output_decoded:
            item["output_decoded"] = output_decoded
        evidence.append(item)
        if len(evidence) >= CALL_EVIDENCE_LIMIT:
            break
    return evidence


def ledger_action(frame: dict[str, Any], selector_map: dict[str, str]) -> dict[str, Any] | None:
    selector = frame.get("selector")
    if not selector:
        return None
    function_name = frame_function(frame, selector_map)
    if function_name not in ACTION_FUNCTIONS:
        return None
    return {
        "frame": frame.get("id"),
        "parent": frame.get("parentId"),
        "seq_index": frame.get("seqIndex"),
        "depth": frame.get("depth"),
        "type": frame.get("type"),
        "from": normalized_addr(frame.get("from")),
        "to": normalized_addr(frame.get("to")),
        "selector": selector,
        "signature": selector_map.get(selector),
        "function": function_name,
        "value_wei": hex_to_int(frame.get("value")),
        "args": decode_static_args(frame, function_name),
    }


def build_action_ledger(frames: list[dict[str, Any]], selector_map: dict[str, str]) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = []
    for frame in frames:
        action = ledger_action(frame, selector_map)
        if action:
            actions.append(action)
            if len(actions) >= ACTION_LIMIT:
                break
    return actions


def summarize_actions(actions: list[dict[str, Any]]) -> dict[str, Any]:
    by_function: Counter[str] = Counter()
    by_target: Counter[str] = Counter()
    by_caller: Counter[str] = Counter()
    first_actions: list[dict[str, Any]] = []
    for action in actions:
        function_name = str(action.get("function") or "")
        by_function[function_name] += 1
        if action.get("to"):
            by_target[str(action["to"])] += 1
        if action.get("from"):
            by_caller[str(action["from"])] += 1
        if len(first_actions) < 40:
            first_actions.append(action)
    return {
        "by_function": dict(by_function.most_common()),
        "by_target": dict(by_target.most_common(40)),
        "by_caller": dict(by_caller.most_common(40)),
        "first_actions": first_actions,
    }


def build_callback_edges(
    frames: list[dict[str, Any]],
    selector_map: dict[str, str],
    children_map: dict[str, list[str]],
    by_id: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    callback_names = {
        "executeOperation",
        "onFlashLoan",
        "onMorphoFlashLoan",
        "receiveFlashLoan",
        "uniswapV3FlashCallback",
        "uniswapV3SwapCallback",
    }
    edges: list[dict[str, Any]] = []
    for frame in frames:
        parent = by_id.get(str(frame.get("parentId")))
        function_name = frame_function(frame, selector_map)
        if not parent or function_name not in callback_names:
            continue
        parent_function = frame_function(parent, selector_map)
        edges.append(
            {
                "from_frame": parent.get("id"),
                "from_function": parent_function,
                "from_address": normalized_addr(parent.get("to")),
                "to_frame": frame.get("id"),
                "to_function": function_name,
                "to_address": normalized_addr(frame.get("to")),
                "child_count": len(children_map.get(str(frame.get("id")), [])),
            }
        )
        if len(edges) >= CALLBACK_EDGE_LIMIT:
            break
    return edges


def build_delegatecall_pairs(frames: list[dict[str, Any]], selector_map: dict[str, str]) -> list[dict[str, Any]]:
    by_id = {frame["id"]: frame for frame in frames}
    pairs: dict[tuple[str, str, str, str | None, str | None, str], dict[str, Any]] = {}
    for frame in frames:
        if frame.get("type") != "DELEGATECALL":
            continue
        parent = by_id.get(str(frame.get("parentId")))
        if not parent:
            continue

        entry_address = normalized_addr(frame.get("from"))
        parent_target = normalized_addr(parent.get("to"))
        code_target = normalized_addr(frame.get("to"))
        parent_selector = parent.get("selector")
        code_selector = frame.get("selector")
        key = (entry_address, parent_target, code_target, parent_selector, code_selector, parent.get("type") or "")
        item = pairs.setdefault(
            key,
            {
                "entry_state_address": entry_address,
                "parent_frame": parent.get("id"),
                "parent_target": parent_target,
                "parent_call_type": parent.get("type"),
                "parent_selector": parent_selector,
                "parent_signature": evidence_signature(selector_map, parent_selector),
                "parent_function": evidence_function_name(selector_map, parent_selector),
                "code_target": code_target,
                "code_call_type": frame.get("type"),
                "code_selector": code_selector,
                "same_selector": parent_selector == code_selector,
                "code_signature": evidence_signature(selector_map, code_selector),
                "code_function": evidence_function_name(selector_map, code_selector),
                "count": 0,
                "entry_frames": [],
                "code_frames": [],
                "parent_callers": [],
            },
        )
        item["count"] += 1
        append_unique(item["entry_frames"], str(parent.get("id")), DELEGATECALL_PAIR_FRAME_LIMIT)
        append_unique(item["code_frames"], str(frame.get("id")), DELEGATECALL_PAIR_FRAME_LIMIT)
        append_unique(item["parent_callers"], normalized_addr(parent.get("from")), DELEGATECALL_PAIR_FRAME_LIMIT)

    ordered = sorted(pairs.values(), key=lambda item: int(item["count"]), reverse=True)
    return ordered[:DELEGATECALL_PAIR_LIMIT]


def known_addresses(chain: str) -> dict[str, dict[str, Any]]:
    if not KNOWN_ADDRESSES_PATH.exists():
        return {}
    data = read_json(KNOWN_ADDRESSES_PATH)
    return {address.lower(): meta for address, meta in data.get(canonical_chain(chain), {}).items()}


def block_month(block_data: dict[str, Any] | None) -> str:
    if not block_data or not block_data.get("timestamp"):
        return "unknown-date"
    timestamp = block_data["timestamp"]
    try:
        value = int(timestamp, 16) if isinstance(timestamp, str) and timestamp.startswith("0x") else int(timestamp)
    except (TypeError, ValueError):
        return "unknown-date"
    return datetime.datetime.utcfromtimestamp(value).strftime("%Y-%m")


def repo_relative(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(REPO_ROOT.resolve()))
    except ValueError:
        return str(path)


def build_role_candidates(chain: str, frames: list[dict[str, Any]], tx_data: dict[str, Any], selector_map: dict[str, str]) -> dict[str, Any]:
    root = frames[0] if frames else {}
    tx_sender = normalized_addr(root.get("from") or tx_data.get("from"))
    root_target = normalized_addr(root.get("to") or tx_data.get("to"))
    root_target_candidate = root_target if root_target and root_target != tx_sender else ""
    known = known_addresses(chain)

    def known_kind(address: str) -> str | None:
        item = known.get(address)
        if not item:
            return None
        kind = item.get("kind")
        return str(kind) if kind else None

    direct_targets: dict[str, dict[str, Any]] = {}
    token_candidates: dict[str, dict[str, Any]] = {}
    flash_loan_candidates: dict[str, dict[str, Any]] = {}

    for frame in frames:
        target = normalized_addr(frame.get("to"))
        if not target:
            continue
        selector = frame.get("selector")
        fn_name = selector_name(selector_map, selector)
        frame_id = str(frame.get("id", ""))
        kind = known_kind(target)

        if kind == "token" or fn_name in TOKEN_FUNCTIONS:
            item = token_candidates.setdefault(target, {"address": target, "selectors": [], "evidence_frames": [], "known_kind": kind})
            append_unique(item["selectors"], fn_name)
            append_unique(item["evidence_frames"], frame_id)

        if fn_name == "flashLoan":
            item = flash_loan_candidates.setdefault(target, {"address": target, "selectors": [], "evidence_frames": []})
            append_unique(item["selectors"], fn_name)
            append_unique(item["evidence_frames"], frame_id)

        if not root_target_candidate or normalized_addr(frame.get("from")) != root_target_candidate or target == root_target_candidate:
            continue

        item = direct_targets.setdefault(
            target,
            {"address": target, "score": 0, "direct_call_count": 0, "selectors": [], "evidence_frames": [], "known_kind": kind, "reasons": []},
        )
        item["direct_call_count"] += 1
        append_unique(item["selectors"], fn_name)
        append_unique(item["evidence_frames"], frame_id)

        if kind == "token":
            item["score"] -= 4
            append_unique(item["reasons"], "known token address")
        if fn_name in TOKEN_FUNCTIONS:
            item["score"] -= 2
            append_unique(item["reasons"], "token helper call")
        elif fn_name in INFRA_FUNCTIONS:
            item["score"] -= 1
            append_unique(item["reasons"], "common infrastructure call")
        elif fn_name in VULNERABLE_HINT_FUNCTIONS:
            item["score"] += 4
            append_unique(item["reasons"], "protocol state/action selector")
        elif selector and selector.startswith("0x"):
            item["score"] += 2
            append_unique(item["reasons"], "non-token direct call from attack contract")
        item["score"] += 1

    direct_attack_targets = sorted(direct_targets.values(), key=lambda item: (int(item["score"]), int(item["direct_call_count"])), reverse=True)
    return {
        "attacker": {"address": tx_sender, "reason": "root transaction sender"},
        "attack_contract": {
            "address": root_target_candidate or None,
            "reason": "root transaction target when it fans out to child calls; verify attacker control before final role assignment",
        },
        "candidate_scope": "direct_attack_targets are shallow hints from outbound calls made by the root target; inspect delegatecall_pairs, call_evidence, and trace.summary.txt before assigning vulnerable_contract",
        "direct_attack_targets": direct_attack_targets[:10],
        "flash_loan_providers": list(flash_loan_candidates.values()),
        "token_contracts": list(token_candidates.values())[:20],
    }


def write_context(case_dir: Path, artifact_dir: Path, chain: str, tx_hash: str, frames: list[dict[str, Any]], selector_map: dict[str, str], trace_index: dict[str, Any]) -> None:
    tx_path = artifact_dir / "tx.json"
    block_path = artifact_dir / "block.json"
    require_files([tx_path])
    tx_data = read_json(tx_path)
    block_data = read_json(block_path) if block_path.exists() else {}
    block_number = hex_to_int(tx_data.get("blockNumber"))
    root = frames[0] if frames else {}
    by_id = {frame["id"]: frame for frame in frames}
    children_map: dict[str, list[str]] = defaultdict(list)
    for frame in frames:
        parent_id = frame.get("parentId")
        if parent_id is not None:
            children_map[str(parent_id)].append(str(frame["id"]))
    action_ledger = build_action_ledger(frames, selector_map)
    loop_summaries = trace_index.get("loopSummaries", [])
    context = {
        "source": "tx2poc-build-context",
        "chain": chain,
        "tx_hash": tx_hash,
        "block_number": block_number,
        "fork_block_number": max(block_number - 1, 0),
        "block_month": block_month(block_data),
        "case_folder": case_dir.name,
        "tx_prefix": tx_hash[:14],
        "tx_sender": normalized_addr(root.get("from") or tx_data.get("from")),
        "root_target": normalized_addr(root.get("to") or tx_data.get("to")),
        "selector_map": selector_map,
        "address_index": trace_index.get("byAddress", {}),
        "selector_index": trace_index.get("bySelector", {}),
        "loop_summaries": loop_summaries,
        "call_evidence": build_call_evidence(frames, selector_map),
        "action_ledger": action_ledger,
        "action_summary": summarize_actions(action_ledger),
        "callback_edges": build_callback_edges(frames, selector_map, children_map, by_id),
        "delegatecall_pairs_note": "entry_state_address is the execution/storage context address from the DELEGATECALL frame; code_target supplies executed code. Confirm proxy identity with source or storage evidence before final role assignment.",
        "delegatecall_pairs": build_delegatecall_pairs(frames, selector_map),
        "role_candidates": build_role_candidates(chain, frames, tx_data, selector_map),
        "artifacts": {
            "trace_summary_file": repo_relative(artifact_dir / "trace.summary.txt"),
        },
    }
    write_json(artifact_dir / "tx_context.json", context)
    print(artifact_dir / "tx_context.json")


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch and summarize an EVM transaction trace.")
    parser.add_argument("--chain", required=True, help="Chain name")
    parser.add_argument("--tx", required=True, help="Transaction hash")
    parser.add_argument("--output-dir", required=True, help="Case folder directly under cases/; artifacts are written under evidence/")
    parser.add_argument("--workspace-root", help="Workspace/repo root; defaults to the current directory")
    parser.add_argument(
        "--source",
        choices=TRACE_SOURCES,
        default="auto",
        help="Trace data source. 'auto' (default) uses Alchemy when ALCHEMY_API_KEY is set, otherwise keyless Blockscout.",
    )
    parser.add_argument("--force", action="store_true", help="Refetch even if trace.raw.json exists")
    args = parser.parse_args()

    set_workspace_root(args.workspace_root)
    chain = canonical_chain(args.chain)
    source = resolve_source(args.source, chain)
    case_dir = resolve_case_dir(args.output_dir)
    case_dir.mkdir(parents=True, exist_ok=True)
    artifact_dir = evidence_dir(case_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    fetch_trace(chain, args.tx, artifact_dir, args.force, source)
    frames = normalize_trace(artifact_dir)
    selector_map = resolve_selectors(case_dir, frames)
    trace_index = write_summary_and_index(artifact_dir, chain, args.tx, frames, selector_map)
    write_context(case_dir, artifact_dir, chain, args.tx, frames, selector_map, trace_index)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
