from __future__ import annotations

import pytest

from _load_skill_module import load_tx2poc_script


trace_tx = load_tx2poc_script("trace_tx")


def test_resolve_source_auto_prefers_alchemy_when_key_present(monkeypatch) -> None:
    monkeypatch.setenv("ALCHEMY_API_KEY", "key")
    assert trace_tx.resolve_source("auto") == "alchemy"
    assert trace_tx.resolve_source(None) == "alchemy"
    monkeypatch.delenv("ALCHEMY_API_KEY", raising=False)
    assert trace_tx.resolve_source("auto") == "blockscout"


def test_resolve_source_explicit_overrides_auto(monkeypatch) -> None:
    monkeypatch.delenv("ALCHEMY_API_KEY", raising=False)
    assert trace_tx.resolve_source("alchemy") == "alchemy"
    monkeypatch.setenv("ALCHEMY_API_KEY", "key")
    assert trace_tx.resolve_source("blockscout") == "blockscout"


def test_resolve_source_rejects_unknown() -> None:
    with pytest.raises(RuntimeError, match="Unsupported source"):
        trace_tx.resolve_source("infura")


def test_blockscout_base_rejects_unsupported_chain() -> None:
    assert trace_tx.blockscout_base("eth") == "https://eth.blockscout.com"
    with pytest.raises(RuntimeError, match="Blockscout source unsupported"):
        trace_tx.blockscout_base("bsc")


def test_rpc_endpoint_routes_by_source() -> None:
    assert trace_tx.rpc_endpoint("eth", "blockscout") == "https://eth.blockscout.com/api/eth-rpc"


def test_parity_trace_to_calltracer_rebuilds_nested_tree() -> None:
    flat = [
        {
            "action": {"callType": "call", "from": "0xaaa", "to": "0xbbb", "value": "0x1", "gas": "0x10", "input": "0xdeadbeef"},
            "result": {"gasUsed": "0x5", "output": "0x01"},
            "subtraces": 2,
            "traceAddress": [],
            "type": "call",
        },
        {
            "action": {"callType": "staticcall", "from": "0xbbb", "to": "0xccc", "gas": "0x8", "input": "0x70a08231"},
            "result": {"gasUsed": "0x2", "output": "0x02"},
            "subtraces": 0,
            "traceAddress": [0],
            "type": "call",
        },
        {
            "action": {"callType": "delegatecall", "from": "0xbbb", "to": "0xddd", "gas": "0x4", "input": "0xabcd"},
            "result": {"gasUsed": "0x1"},
            "subtraces": 0,
            "traceAddress": [1],
            "type": "call",
        },
    ]

    root = trace_tx.parity_trace_to_calltracer(flat)

    assert root["type"] == "CALL"
    assert root["from"] == "0xaaa"
    assert root["to"] == "0xbbb"
    assert root["value"] == "0x1"
    assert root["input"] == "0xdeadbeef"
    assert root["output"] == "0x01"
    assert len(root["calls"]) == 2
    assert root["calls"][0]["type"] == "STATICCALL"
    assert root["calls"][0]["to"] == "0xccc"
    assert root["calls"][1]["type"] == "DELEGATECALL"
    assert root["calls"][1]["output"] is None


def test_parity_trace_to_calltracer_orders_siblings_by_trace_address() -> None:
    flat = [
        {"action": {"callType": "call", "from": "0xroot"}, "traceAddress": [], "type": "call"},
        {"action": {"callType": "call", "from": "0xroot", "to": "0x02"}, "traceAddress": [2], "type": "call"},
        {"action": {"callType": "call", "from": "0xroot", "to": "0x00"}, "traceAddress": [0], "type": "call"},
        {"action": {"callType": "call", "from": "0xroot", "to": "0x01"}, "traceAddress": [1], "type": "call"},
    ]

    root = trace_tx.parity_trace_to_calltracer(flat)

    assert [child["to"] for child in root["calls"]] == ["0x00", "0x01", "0x02"]


def test_parity_trace_to_calltracer_surfaces_error_payload() -> None:
    with pytest.raises(RuntimeError, match="Not found"):
        trace_tx.parity_trace_to_calltracer({"message": "Not found"})
    with pytest.raises(RuntimeError, match="empty"):
        trace_tx.parity_trace_to_calltracer([])


def test_parity_create_and_suicide_frames() -> None:
    flat = [
        {"action": {"callType": "call", "from": "0xroot", "to": "0xfactory"}, "traceAddress": [], "type": "call"},
        {
            "action": {"from": "0xfactory", "gas": "0x9", "init": "0x6080", "value": "0x0"},
            "result": {"gasUsed": "0x7", "address": "0xnew", "code": "0x60"},
            "traceAddress": [0],
            "type": "create",
        },
        {
            "action": {"address": "0xnew", "refundAddress": "0xbeef", "balance": "0x3"},
            "traceAddress": [1],
            "type": "suicide",
        },
    ]

    root = trace_tx.parity_trace_to_calltracer(flat)

    created = root["calls"][0]
    assert created["type"] == "CREATE"
    assert created["from"] == "0xfactory"
    assert created["to"] == "0xnew"
    assert created["input"] == "0x6080"
    assert created["output"] == "0x60"

    destroyed = root["calls"][1]
    assert destroyed["type"] == "SELFDESTRUCT"
    assert destroyed["from"] == "0xnew"
    assert destroyed["to"] == "0xbeef"
    assert destroyed["value"] == "0x3"


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


def test_set_workspace_root_controls_case_dir(tmp_path) -> None:
    original_root = trace_tx.REPO_ROOT
    try:
        trace_tx.set_workspace_root(str(tmp_path))
        case_dir = trace_tx.resolve_case_dir("cases/example-case")
        assert case_dir == (tmp_path / "cases" / "example-case").resolve()
    finally:
        trace_tx.set_workspace_root(str(original_root))


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
