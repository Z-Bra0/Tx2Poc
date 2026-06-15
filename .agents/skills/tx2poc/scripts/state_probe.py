from __future__ import annotations

import argparse
import json
from typing import Any

from trace_tx import canonical_chain, hex_to_int, rpc_call, rpc_url


BALANCE_OF_SELECTOR = "0x70a08231"
ALLOWANCE_SELECTOR = "0xdd62ed3e"

CUSTOM_VIEW_SELECTORS = {
    "creditOf": "0x75807250",
    "creditlessOf": "0x232d88ba",
    "lockedOf": "0xa5f1e282",
    "debtOf": "0xd283e75f",
}

def normalize_address(address: str) -> str:
    value = address.strip().lower()
    if not value.startswith("0x") or len(value) != 42:
        raise ValueError(f"invalid address: {address}")
    int(value[2:], 16)
    return value


def normalize_block(block: str) -> str:
    value = block.strip().lower()
    if value.startswith("0x"):
        int(value, 16)
        return value
    return hex(int(value))


def encode_address_arg(address: str) -> str:
    return normalize_address(address)[2:].rjust(64, "0")


def encode_call(selector: str, *addresses: str) -> str:
    if not selector.startswith("0x") or len(selector) != 10:
        raise ValueError(f"invalid selector: {selector}")
    return selector + "".join(encode_address_arg(address) for address in addresses)


def decode_uint_result(result: str | None) -> int | None:
    if not result or result == "0x":
        return None
    return int(result, 16)


def eth_call_uint(url: str, token: str, data: str, block: str) -> dict[str, Any]:
    try:
        result = rpc_call(url, "eth_call", [{"to": token, "data": data}, block])
        value = decode_uint_result(result)
        if value is None:
            return {"ok": False, "error": "empty response"}
        return {"ok": True, "value": value}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def probe_token(
    url: str,
    token: str,
    address: str,
    spenders: list[str],
    custom_views: list[str],
    block: str,
) -> dict[str, Any]:
    token = normalize_address(token)
    entry: dict[str, Any] = {
        "token": token,
        "balanceOf": eth_call_uint(url, token, encode_call(BALANCE_OF_SELECTOR, address), block),
    }

    custom: dict[str, Any] = {}
    for view_name in custom_views:
        selector = CUSTOM_VIEW_SELECTORS[view_name]
        view_result = eth_call_uint(url, token, encode_call(selector, address), block)
        if view_result.get("ok") or view_result.get("error") != "empty response":
            custom[view_name] = view_result
    if custom:
        entry["customViews"] = custom

    if spenders:
        entry["allowances"] = {
            spender: eth_call_uint(url, token, encode_call(ALLOWANCE_SELECTOR, address, spender), block)
            for spender in spenders
        }

    return entry


def probe_address(
    url: str,
    address: str,
    tokens: list[str],
    spenders: list[str],
    custom_views: list[str],
    block: str,
) -> dict[str, Any]:
    address = normalize_address(address)
    code = rpc_call(url, "eth_getCode", [address, block])
    native_balance = rpc_call(url, "eth_getBalance", [address, block])
    return {
        "address": address,
        "codeLength": max((len(code) - 2) // 2, 0),
        "nativeBalanceWei": hex_to_int(native_balance),
        "tokens": [probe_token(url, token, address, spenders, custom_views, block) for token in tokens],
    }


def probe_state(
    chain: str,
    block: str,
    addresses: list[str],
    tokens: list[str],
    spenders: list[str],
    custom_views: list[str],
) -> dict[str, Any]:
    chain = canonical_chain(chain)
    block_tag = normalize_block(block)
    url = rpc_url(chain)
    normalized_spenders = [normalize_address(spender) for spender in spenders]
    return {
        "chain": chain,
        "block": block_tag,
        "addresses": [
            probe_address(url, address, tokens, normalized_spenders, custom_views, block_tag)
            for address in addresses
        ],
    }


def view_value_text(result: dict[str, Any]) -> str:
    if result.get("ok"):
        return str(result["value"])
    return f"ERR {result.get('error', 'unknown')}"


def render_markdown(report: dict[str, Any]) -> str:
    lines = [f"# State Probe", "", f"- Chain: {report['chain']}", f"- Block: {report['block']}", ""]
    for address_entry in report["addresses"]:
        lines.append(f"## {address_entry['address']}")
        lines.append(f"- codeLength: {address_entry['codeLength']}")
        lines.append(f"- nativeBalanceWei: {address_entry['nativeBalanceWei']}")
        for token_entry in address_entry["tokens"]:
            lines.append(f"- token {token_entry['token']}")
            lines.append(f"  - balanceOf: {view_value_text(token_entry['balanceOf'])}")
            for view_name, view_result in token_entry.get("customViews", {}).items():
                lines.append(f"  - {view_name}: {view_value_text(view_result)}")
            for spender, allowance in token_entry.get("allowances", {}).items():
                lines.append(f"  - allowance[{spender}]: {view_value_text(allowance)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe pre-attack state for attacker-controlled addresses.")
    parser.add_argument("--chain", required=True, help="Chain name or alias")
    parser.add_argument("--block", required=True, help="Fork block number/tag, usually tx_block - 1")
    parser.add_argument("--address", action="append", required=True, help="Address to probe; repeatable")
    parser.add_argument("--token", action="append", default=[], help="Token/accounting contract to probe; repeatable")
    parser.add_argument("--spender", action="append", default=[], help="Allowance spender to probe; repeatable")
    parser.add_argument(
        "--view",
        action="append",
        choices=sorted(CUSTOM_VIEW_SELECTORS),
        default=[],
        help="Custom uint view(address) to probe; repeatable.",
    )
    parser.add_argument("--markdown", action="store_true", help="Print markdown instead of JSON")
    args = parser.parse_args(argv)

    report = probe_state(args.chain, args.block, args.address, args.token, args.spender, args.view)
    if args.markdown:
        print(render_markdown(report), end="")
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
