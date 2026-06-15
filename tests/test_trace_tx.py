from __future__ import annotations

import pytest

from _load_skill_module import load_tx2poc_script


trace_tx = load_tx2poc_script("trace_tx")


def test_canonical_chain_aliases() -> None:
    assert trace_tx.canonical_chain("eth") == "ethereum"
    assert trace_tx.canonical_chain("mainnet") == "ethereum"
    assert trace_tx.canonical_chain("bnb") == "bsc"
    assert trace_tx.canonical_chain("base") == "base"


def test_resolve_case_dir_must_be_direct_child_of_cases() -> None:
    case_dir = trace_tx.resolve_case_dir("cases/example-case")
    assert case_dir.parent == trace_tx.CASE_ROOT.resolve()
    assert case_dir.name == "example-case"

    with pytest.raises(RuntimeError, match="direct child of cases"):
        trace_tx.resolve_case_dir("cases/example-case/nested")


def test_selector_from_input() -> None:
    assert trace_tx.selector_from_input("0x12345678abcd") == "0x12345678"
    assert trace_tx.selector_from_input("0x1234") is None
    assert trace_tx.selector_from_input(None) is None


def test_format_native_value_keeps_small_wei_exact() -> None:
    assert trace_tx.format_native_value(None) == ""
    assert trace_tx.format_native_value("0x0") == ""
    assert trace_tx.format_native_value(hex(1)) == " 1wei"
    assert trace_tx.format_native_value(hex(10**14 - 1)) == f" {10**14 - 1}wei"
    assert trace_tx.format_native_value(hex(10**14)) == " 0.0001ETH"
    assert trace_tx.format_native_value(hex(10**18)) == " 1.0000ETH"


def test_decode_static_transfer_args() -> None:
    to = "0x0000000000000000000000001111111111111111111111111111111111111111"
    amount = 123
    calldata = "0xa9059cbb" + to[2:].rjust(64, "0") + hex(amount)[2:].rjust(64, "0")
    frame = {"input": calldata}

    assert trace_tx.decode_static_args(frame, "transfer") == {
        "to": "0x1111111111111111111111111111111111111111",
        "amount": amount,
    }


def word(value: int) -> str:
    return hex(value)[2:].rjust(64, "0")


def test_build_call_evidence_keeps_helper_local_return_data() -> None:
    output = "0x" + word(233) + word(64) + word(2) + word(50_000) + word(57_000)
    frames = [
        {
            "id": "c0000",
            "parentId": None,
            "seqIndex": 0,
            "depth": 0,
            "type": "CALL",
            "from": "0xaaa",
            "to": "0xbbb",
            "input": "0x",
            "output": None,
            "selector": None,
        },
        {
            "id": "c0001",
            "parentId": "c0000",
            "seqIndex": 1,
            "depth": 1,
            "type": "CALL",
            "from": "0xbbb",
            "to": "0xhelper",
            "input": "0x9846cd9e",
            "output": None,
            "selector": "0x9846cd9e",
        },
        {
            "id": "c0002",
            "parentId": "c0001",
            "seqIndex": 2,
            "depth": 2,
            "type": "CALL",
            "from": "0xhelper",
            "to": "0xquery",
            "input": "0x9ebbf05d",
            "output": output,
            "selector": "0x9ebbf05d",
        },
    ]

    evidence = trace_tx.build_call_evidence(frames, {})

    assert evidence == [
        {
            "frame": "c0002",
            "parent": "c0001",
            "ancestors": ["c0000", "c0001"],
            "seq_index": 2,
            "depth": 2,
            "type": "CALL",
            "from": "0xhelper",
            "to": "0xquery",
            "selector": "0x9ebbf05d",
            "signature": None,
            "function": "0x9ebbf05d",
            "input_decoded": {},
            "output_raw": output,
            "output_truncated": False,
        }
    ]


def test_build_call_evidence_decodes_known_balance_output() -> None:
    account = "0x1111111111111111111111111111111111111111"
    balance = 233
    calldata = "0x70a08231" + account[2:].rjust(64, "0")
    output = "0x" + word(balance)
    frames = [
        {
            "id": "c0000",
            "parentId": None,
            "seqIndex": 0,
            "depth": 0,
            "type": "STATICCALL",
            "from": "0xhelper",
            "to": "0xtoken",
            "input": calldata,
            "output": output,
            "selector": "0x70a08231",
        }
    ]

    evidence = trace_tx.build_call_evidence(frames, {"0x70a08231": "balanceOf(address)"})

    assert evidence == [
        {
            "frame": "c0000",
            "parent": None,
            "ancestors": [],
            "seq_index": 0,
            "depth": 0,
            "type": "STATICCALL",
            "from": "0xhelper",
            "to": "0xtoken",
            "selector": "0x70a08231",
            "signature": "balanceOf(address)",
            "function": "balanceOf",
            "input_decoded": {"account": account},
            "output_raw": output,
            "output_truncated": False,
            "output_decoded": {"balance": balance},
        }
    ]
