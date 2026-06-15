from __future__ import annotations

import pytest

from _load_skill_module import load_tx2poc_script


decode_calldata = load_tx2poc_script("decode_calldata")


def test_clean_hex_validation() -> None:
    assert decode_calldata.clean_hex(" 0xAABBccDD ") == "0xaabbccdd"

    with pytest.raises(ValueError, match="must start with 0x"):
        decode_calldata.clean_hex("aabbcc")
    with pytest.raises(ValueError, match="too short"):
        decode_calldata.clean_hex("0x1234")
    with pytest.raises(ValueError, match="odd length"):
        decode_calldata.clean_hex("0x095ea7b30")


def test_decode_approve() -> None:
    spender = "0x2222222222222222222222222222222222222222"
    amount = 456
    calldata = "0x095ea7b3" + spender[2:].rjust(64, "0") + hex(amount)[2:].rjust(64, "0")

    decoded = decode_calldata.decode(calldata)

    assert decoded["selector"] == "0x095ea7b3"
    assert decoded["decoded"] == {"spender": spender, "amount": amount}
    assert "raw_calldata" not in decoded


def test_unknown_selector_keeps_raw_calldata() -> None:
    calldata = "0x12345678" + "00" * 32

    decoded = decode_calldata.decode(calldata)

    assert decoded["selector"] == "0x12345678"
    assert decoded["decoded"] is None
    assert decoded["raw_calldata"] == calldata
    assert "not supported" in decoded["reason"]
