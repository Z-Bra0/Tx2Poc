from __future__ import annotations

import pytest

from _load_skill_module import load_tx2poc_script


state_probe = load_tx2poc_script("state_probe")


def test_normalize_address() -> None:
    assert (
        state_probe.normalize_address("0x1111111111111111111111111111111111111111")
        == "0x1111111111111111111111111111111111111111"
    )

    with pytest.raises(ValueError, match="invalid address"):
        state_probe.normalize_address("0x1234")


def test_normalize_block() -> None:
    assert state_probe.normalize_block("25170425") == "0x18011f9"
    assert state_probe.normalize_block("0x18011f9") == "0x18011f9"

    with pytest.raises(ValueError):
        state_probe.normalize_block("latest")


def test_encode_call_with_address_args() -> None:
    owner = "0x1111111111111111111111111111111111111111"
    spender = "0x2222222222222222222222222222222222222222"

    assert state_probe.encode_call(state_probe.BALANCE_OF_SELECTOR, owner) == (
        "0x70a08231"
        "0000000000000000000000001111111111111111111111111111111111111111"
    )
    assert state_probe.encode_call(state_probe.ALLOWANCE_SELECTOR, owner, spender) == (
        "0xdd62ed3e"
        "0000000000000000000000001111111111111111111111111111111111111111"
        "0000000000000000000000002222222222222222222222222222222222222222"
    )


def test_decode_uint_result() -> None:
    assert state_probe.decode_uint_result(None) is None
    assert state_probe.decode_uint_result("0x") is None
    assert state_probe.decode_uint_result("0x0") == 0
    assert state_probe.decode_uint_result("0x7b") == 123


def test_render_markdown() -> None:
    report = {
        "chain": "ethereum",
        "block": "0x1",
        "addresses": [
            {
                "address": "0x1111111111111111111111111111111111111111",
                "codeLength": 42,
                "nativeBalanceWei": 1,
                "tokens": [
                    {
                        "token": "0x2222222222222222222222222222222222222222",
                        "balanceOf": {"ok": True, "value": 100},
                        "customViews": {"creditOf": {"ok": False, "error": "empty response"}},
                    }
                ],
            }
        ],
    }

    rendered = state_probe.render_markdown(report)

    assert "# State Probe" in rendered
    assert "codeLength: 42" in rendered
    assert "balanceOf: 100" in rendered
    assert "creditOf: ERR empty response" in rendered


def test_probe_state_uses_rpc_calls_without_network(monkeypatch: pytest.MonkeyPatch) -> None:
    address = "0x1111111111111111111111111111111111111111"
    token = "0x2222222222222222222222222222222222222222"
    spender = "0x3333333333333333333333333333333333333333"

    calls: list[tuple[str, list[object]]] = []

    def fake_rpc_url(chain: str) -> str:
        assert chain == "ethereum"
        return "mock://rpc"

    def fake_rpc_call(url: str, method: str, params: list[object]) -> str:
        assert url == "mock://rpc"
        calls.append((method, params))
        if method == "eth_getCode":
            return "0x6000"
        if method == "eth_getBalance":
            return "0x7b"
        if method == "eth_call":
            data = params[0]["data"]  # type: ignore[index]
            if data.startswith(state_probe.BALANCE_OF_SELECTOR):
                return "0x64"
            if data.startswith(state_probe.ALLOWANCE_SELECTOR):
                return "0x05"
            if data.startswith(state_probe.CUSTOM_VIEW_SELECTORS["creditOf"]):
                return "0x03"
        raise AssertionError(f"unexpected call {method} {params}")

    monkeypatch.setattr(state_probe, "rpc_url", fake_rpc_url)
    monkeypatch.setattr(state_probe, "rpc_call", fake_rpc_call)

    report = state_probe.probe_state("eth", "1", [address], [token], [spender], ["creditOf"])

    address_report = report["addresses"][0]
    token_report = address_report["tokens"][0]
    assert report["block"] == "0x1"
    assert address_report["codeLength"] == 2
    assert address_report["nativeBalanceWei"] == 123
    assert token_report["balanceOf"]["value"] == 100
    assert token_report["allowances"][spender]["value"] == 5
    assert token_report["customViews"]["creditOf"]["value"] == 3
    assert [method for method, _ in calls] == ["eth_getCode", "eth_getBalance", "eth_call", "eth_call", "eth_call"]
