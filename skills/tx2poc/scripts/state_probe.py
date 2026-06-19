from __future__ import annotations

import argparse
import json
from collections.abc import Callable
from typing import Any, Literal, NamedTuple

from trace_tx import canonical_chain, hex_to_int, hex_words, rpc_call, rpc_url


BALANCE_OF_SELECTOR = "0x70a08231"
ALLOWANCE_SELECTOR = "0xdd62ed3e"

CustomView = tuple[str, str]


class AddressView(NamedTuple):
    name: str
    selector: str
    arg_kind: Literal["address", "none"]

ADDRESS_VIEW_ARG_KINDS = {"address", "none"}


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
    return normalize_selector(selector) + "".join(encode_address_arg(address) for address in addresses)


def normalize_selector(selector: str) -> str:
    value = selector.strip().lower()
    if not value.startswith("0x") or len(value) != 10:
        raise ValueError(f"invalid selector: {selector}")
    int(value[2:], 16)
    return value


def parse_named_spec(value: str, item_name: str, expected: str) -> tuple[str, str]:
    if "=" not in value:
        raise ValueError(f"invalid {item_name} {value!r}: expected {expected}")
    name, spec = value.split("=", 1)
    name = name.strip()
    if not name:
        raise ValueError(f"invalid {item_name} {value!r}: missing name")
    return name, spec.strip()


def parse_named_selector(value: str, item_name: str, expected: str) -> tuple[str, str]:
    name, selector = parse_named_spec(value, item_name, expected)
    return name, normalize_selector(selector)


def duplicate_names(names: list[str]) -> list[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in names:
        if name in seen:
            duplicates.add(name)
        seen.add(name)
    return sorted(duplicates)


def unique_addresses(addresses: list[str]) -> list[str]:
    seen: set[str] = set()
    unique: list[str] = []
    for address in addresses:
        normalized = normalize_address(address)
        if normalized not in seen:
            seen.add(normalized)
            unique.append(normalized)
    return unique


def parse_custom_view(value: str) -> CustomView:
    return parse_named_selector(value, "custom view", "NAME=0xSELECTOR")


def parse_custom_views(values: list[str]) -> list[CustomView]:
    views = [parse_custom_view(value) for value in values]
    names = [name for name, _ in views]
    duplicates = duplicate_names(names)
    if duplicates:
        raise ValueError(f"duplicate custom view name(s): {', '.join(duplicates)}")
    return views


def parse_address_view(value: str) -> AddressView:
    name, selector_spec = parse_named_spec(value, "address view", "NAME=0xSELECTOR[:address|none]")
    arg_kind = "address"
    if ":" in selector_spec:
        selector_spec, arg_kind = selector_spec.rsplit(":", 1)
        arg_kind = arg_kind.strip().lower()
    if arg_kind not in ADDRESS_VIEW_ARG_KINDS:
        raise ValueError(f"invalid address view {value!r}: expected arg kind address or none")
    normalized_selector = normalize_selector(selector_spec)
    if arg_kind == "none":
        return AddressView(name, normalized_selector, "none")
    return AddressView(name, normalized_selector, "address")


def parse_address_views(values: list[str]) -> list[AddressView]:
    views = [parse_address_view(value) for value in values]
    names = [view.name for view in views]
    duplicates = duplicate_names(names)
    if duplicates:
        raise ValueError(f"duplicate address view name(s): {', '.join(duplicates)}")
    return views


def decode_uint_result(result: str | None) -> int | None:
    if not result or result == "0x":
        return None
    return int(result, 16)


def decode_address_result(result: str | None) -> str | None:
    words = hex_words(result)
    if len(words) != 1:
        return None
    word = words[0]
    if int(word[:24], 16) != 0:
        return None
    return "0x" + word[-40:].lower()


def eth_call_decoded(
    url: str,
    target: str,
    data: str,
    block: str,
    decoder: Callable[[str | None], Any | None],
) -> dict[str, Any]:
    try:
        result = rpc_call(url, "eth_call", [{"to": target, "data": data}, block])
        value = decoder(result)
        if value is None:
            return {"ok": False, "error": "empty response"}
        return {"ok": True, "value": value}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def eth_call_uint(url: str, token: str, data: str, block: str) -> dict[str, Any]:
    return eth_call_decoded(url, token, data, block, decode_uint_result)


def eth_call_address(url: str, contract: str, data: str, block: str) -> dict[str, Any]:
    return eth_call_decoded(url, contract, data, block, decode_address_result)


def probe_token(
    url: str,
    token: str,
    address: str,
    spenders: list[str],
    custom_views: list[CustomView],
    block: str,
) -> dict[str, Any]:
    token = normalize_address(token)
    entry: dict[str, Any] = {
        "token": token,
        "balanceOf": eth_call_uint(url, token, encode_call(BALANCE_OF_SELECTOR, address), block),
    }

    custom: dict[str, Any] = {}
    for view_name, selector in custom_views:
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


def probe_contract(
    url: str,
    contract: str,
    addresses: list[str],
    address_views: list[AddressView],
    block: str,
) -> dict[str, Any]:
    contract = normalize_address(contract)
    entry: dict[str, Any] = {"contract": contract}

    no_arg_views: dict[str, Any] = {}
    per_address_views: dict[str, Any] = {}
    for view in address_views:
        if view.arg_kind == "none":
            no_arg_views[view.name] = eth_call_address(url, contract, encode_call(view.selector), block)
            continue

        for address in addresses:
            per_address_views.setdefault(address, {})[view.name] = eth_call_address(
                url,
                contract,
                encode_call(view.selector, address),
                block,
            )

    if no_arg_views:
        entry["views"] = no_arg_views
    if per_address_views:
        entry["addressViews"] = per_address_views
    return entry


def probe_address(
    url: str,
    address: str,
    tokens: list[str],
    spenders: list[str],
    custom_views: list[CustomView],
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
    custom_views: list[CustomView],
    contracts: list[str] | None = None,
    address_views: list[AddressView] | None = None,
) -> dict[str, Any]:
    chain = canonical_chain(chain)
    block_tag = normalize_block(block)
    url = rpc_url(chain)
    normalized_spenders = unique_addresses(spenders)
    normalized_addresses = unique_addresses(addresses)
    report = {
        "chain": chain,
        "block": block_tag,
        "addresses": [
            probe_address(url, address, tokens, normalized_spenders, custom_views, block_tag)
            for address in normalized_addresses
        ],
    }
    if contracts and address_views:
        report["contracts"] = [
            probe_contract(url, contract, normalized_addresses, address_views, block_tag)
            for contract in contracts
        ]
    return report


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
    for contract_entry in report.get("contracts", []):
        lines.append(f"## contract {contract_entry['contract']}")
        for view_name, view_result in contract_entry.get("views", {}).items():
            lines.append(f"- {view_name}: {view_value_text(view_result)}")
        for address, views in contract_entry.get("addressViews", {}).items():
            lines.append(f"- address {address}")
            for view_name, view_result in views.items():
                lines.append(f"  - {view_name}: {view_value_text(view_result)}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Probe pre-attack state for attacker-controlled addresses.")
    parser.add_argument("--chain", required=True, help="Chain name or alias")
    parser.add_argument("--block", required=True, help="Fork block number/tag, usually tx_block - 1")
    parser.add_argument("--address", action="append", required=True, help="Address to probe; repeatable")
    parser.add_argument("--token", action="append", default=[], help="Token/accounting contract to probe; repeatable")
    parser.add_argument("--spender", action="append", default=[], help="Allowance spender to probe; repeatable")
    parser.add_argument("--contract", action="append", default=[], help="Callee/helper contract to probe; repeatable")
    parser.add_argument(
        "--view",
        action="append",
        default=[],
        metavar="NAME=0xSELECTOR",
        help="Custom uint view(address) selector to probe; repeatable.",
    )
    parser.add_argument(
        "--address-view",
        action="append",
        default=[],
        metavar="NAME=0xSELECTOR[:address|none]",
        help="Custom address-returning helper view. Default arg kind is address; use :none for owner()/admin().",
    )
    parser.add_argument("--markdown", action="store_true", help="Print markdown instead of JSON")
    args = parser.parse_args(argv)

    try:
        custom_views = parse_custom_views(args.view)
        address_views = parse_address_views(args.address_view)
    except ValueError as exc:
        parser.error(str(exc))
    if address_views and not args.contract:
        parser.error("--address-view requires at least one --contract")

    report = probe_state(
        args.chain,
        args.block,
        args.address,
        args.token,
        args.spender,
        custom_views,
        args.contract,
        address_views,
    )
    if args.markdown:
        print(render_markdown(report), end="")
    else:
        print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
