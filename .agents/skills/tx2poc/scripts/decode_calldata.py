from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


SCRIPT_DIR = Path(__file__).resolve().parent
SIGNATURES_PATH = SCRIPT_DIR.parent / "data" / "common_signatures_2k.json"

CUSTOM_DECODER_SIGNATURES = {
    "0x945bcec9": "batchSwap(uint8,(bytes32,uint256,uint256,uint256,bytes)[],address[],(address,bool,address,bool),int256[],uint256)",
    "0x2df2c7c0": "updateTokenRateCache(address)",
}


def load_signatures() -> dict[str, str]:
    signatures: dict[str, str] = {}
    if SIGNATURES_PATH.exists():
        with SIGNATURES_PATH.open("r", encoding="utf-8") as handle:
            signatures.update(json.load(handle))
    signatures.update(CUSTOM_DECODER_SIGNATURES)
    return signatures


def clean_hex(value: str) -> str:
    value = value.strip()
    if not value.startswith("0x"):
        raise ValueError("calldata must start with 0x")
    if len(value) < 10:
        raise ValueError("calldata is too short")
    if len(value[2:]) % 2:
        raise ValueError("calldata hex has odd length")
    return value.lower()


def word(data: str, offset: int) -> str:
    start = offset * 2
    end = start + 64
    if end > len(data):
        raise ValueError(f"ABI word at byte offset {offset} is out of bounds")
    return data[start:end]


def uint_word(data: str, offset: int) -> int:
    return int(word(data, offset), 16)


def int_word(data: str, offset: int) -> int:
    value = uint_word(data, offset)
    if value >= 1 << 255:
        value -= 1 << 256
    return value


def address_word(data: str, offset: int) -> str:
    return "0x" + word(data, offset)[24:]


def bool_word(data: str, offset: int) -> bool:
    value = uint_word(data, offset)
    if value not in {0, 1}:
        raise ValueError(f"invalid ABI bool value {value}")
    return bool(value)


def bytes_at(data: str, offset: int) -> str:
    length = uint_word(data, offset)
    start = (offset + 32) * 2
    end = start + (length * 2)
    if end > len(data):
        raise ValueError(f"ABI bytes at byte offset {offset} is out of bounds")
    return "0x" + data[start:end]


def address_array(data: str, offset: int) -> list[str]:
    length = uint_word(data, offset)
    return [address_word(data, offset + 32 + i * 32) for i in range(length)]


def int_array(data: str, offset: int) -> list[int]:
    length = uint_word(data, offset)
    return [int_word(data, offset + 32 + i * 32) for i in range(length)]


def decode_batch_swap(args: str) -> dict[str, Any]:
    swaps_offset = uint_word(args, 32)
    assets_offset = uint_word(args, 64)
    limits_offset = uint_word(args, 224)
    swaps = decode_batch_swap_steps(args, swaps_offset)

    return {
        "kind": decode_swap_kind(uint_word(args, 0)),
        "swaps": swaps,
        "poolIds": decode_unique_pool_ids(swaps),
        "loopHints": find_step_loop_hints(swaps),
        "assets": address_array(args, assets_offset),
        "funds": {
            "sender": address_word(args, 96),
            "fromInternalBalance": bool_word(args, 128),
            "recipient": address_word(args, 160),
            "toInternalBalance": bool_word(args, 192),
        },
        "limits": int_array(args, limits_offset),
        "deadline": uint_word(args, 256),
    }


def decode_swap_kind(value: int) -> str:
    if value == 0:
        return "GIVEN_IN"
    if value == 1:
        return "GIVEN_OUT"
    return f"UNKNOWN({value})"


def decode_batch_swap_steps(args: str, offset: int) -> list[dict[str, Any]]:
    length = uint_word(args, offset)
    steps: list[dict[str, Any]] = []
    offsets_base = offset + 32

    for index in range(length):
        element_offset = uint_word(args, offsets_base + index * 32)
        # Dynamic tuple array element offsets are relative to the start of the
        # element-offset table, not the length word.
        tuple_start = offsets_base + element_offset
        user_data_offset = uint_word(args, tuple_start + 128)
        steps.append(
            {
                "poolId": "0x" + word(args, tuple_start),
                "poolIdDecoded": decode_balancer_pool_id("0x" + word(args, tuple_start)),
                "assetInIndex": uint_word(args, tuple_start + 32),
                "assetOutIndex": uint_word(args, tuple_start + 64),
                "amount": uint_word(args, tuple_start + 96),
                "userData": bytes_at(args, tuple_start + user_data_offset),
            }
        )
    return steps


def decode_balancer_pool_id(pool_id: str) -> dict[str, Any]:
    value = clean_bytes32(pool_id)
    raw = value[2:]
    return {
        "poolAddress": "0x" + raw[:40],
        "specialization": int(raw[40:44], 16),
        "nonce": int(raw[44:], 16),
        "suffix": "0x" + raw[40:],
    }


def clean_bytes32(value: str) -> str:
    value = value.strip().lower()
    if not value.startswith("0x"):
        raise ValueError("bytes32 value must start with 0x")
    if len(value) != 66:
        raise ValueError("bytes32 value must be 32 bytes")
    return value


def decode_unique_pool_ids(swaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    decoded: list[dict[str, Any]] = []
    for swap in swaps:
        pool_id = swap["poolId"]
        if pool_id in seen:
            continue
        seen.add(pool_id)
        info = {"poolId": pool_id}
        info.update(decode_balancer_pool_id(pool_id))
        decoded.append(info)
    return decoded


def find_step_loop_hints(swaps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = [step_pattern_key(swap) for swap in swaps]
    hints: list[dict[str, Any]] = []
    index = 0
    while index < len(swaps):
        best: dict[str, Any] | None = None
        for width in range(1, 9):
            if index + width * 3 > len(swaps):
                continue
            pattern = keys[index : index + width]
            repeat_count = 1
            while keys[index + repeat_count * width : index + (repeat_count + 1) * width] == pattern:
                repeat_count += 1
            if repeat_count < 3:
                continue
            coverage = repeat_count * width
            candidate = {
                "start": index,
                "end": index + coverage - 1,
                "patternLength": width,
                "repeatCount": repeat_count,
                "coverage": coverage,
                "pattern": [step_pattern_dict(swaps[index + offset]) for offset in range(width)],
                "amounts": [swaps[index + offset]["amount"] for offset in range(coverage)],
            }
            if best is None or (candidate["coverage"], -candidate["patternLength"]) > (
                best["coverage"],
                -best["patternLength"],
            ):
                best = candidate
        if best is None:
            index += 1
            continue
        hints.append(best)
        index = best["end"] + 1
    return hints


def step_pattern_key(step: dict[str, Any]) -> tuple[str, int, int, str]:
    return (
        step["poolId"],
        step["assetInIndex"],
        step["assetOutIndex"],
        step["userData"],
    )


def step_pattern_dict(step: dict[str, Any]) -> dict[str, Any]:
    return {
        "poolId": step["poolId"],
        "assetInIndex": step["assetInIndex"],
        "assetOutIndex": step["assetOutIndex"],
        "userData": step["userData"],
    }


def decode_approve(args: str) -> dict[str, Any]:
    return {
        "spender": address_word(args, 0),
        "amount": uint_word(args, 32),
    }


def decode_address_arg(args: str, name: str) -> dict[str, Any]:
    return {name: address_word(args, 0)}


def decode_bytes32_arg(args: str, name: str) -> dict[str, Any]:
    return {name: "0x" + word(args, 0)}


def decode(calldata: str) -> dict[str, Any]:
    calldata = clean_hex(calldata)
    selector = calldata[:10]
    args = calldata[10:]
    signature = load_signatures().get(selector)
    result: dict[str, Any] = {
        "selector": selector,
        "signature": signature,
        "decoded": None,
    }

    if selector == "0x945bcec9":
        result["decoded"] = decode_batch_swap(args)
        result["solidity_hint"] = (
            "Build IBalancerVault.batchSwap(kind, swaps, assets, funds, limits, deadline). "
            "Use poolIds to name pool constants and loopHints to avoid flat repeated step setters."
        )
    elif selector == "0x095ea7b3":
        result["decoded"] = decode_approve(args)
    elif selector == "0x2df2c7c0":
        result["decoded"] = decode_address_arg(args, "token")
    elif selector == "0xf94d4668":
        result["decoded"] = decode_bytes32_arg(args, "poolId")
    else:
        result["raw_calldata"] = calldata
        result["reason"] = "selector is not supported by this helper"

    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Decode one EVM calldata payload and print JSON.")
    parser.add_argument("calldata", nargs="?", help="0x-prefixed calldata. Reads stdin when omitted.")
    parser.add_argument("--compact", action="store_true", help="Print compact JSON")
    args = parser.parse_args(argv)

    calldata = args.calldata if args.calldata is not None else sys.stdin.read()
    decoded = decode(calldata)
    if args.compact:
        print(json.dumps(decoded, separators=(",", ":")))
    else:
        print(json.dumps(decoded, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
