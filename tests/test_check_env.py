from __future__ import annotations

import pytest

from _load_skill_module import load_tx2poc_script


check_env = load_tx2poc_script("check_env")


def test_missing_env_vars_reports_all_required_keys() -> None:
    assert check_env.missing_env_vars({}) == ["ALCHEMY_API_KEY", "ETHERSCAN_API_KEY"]
    assert check_env.missing_env_vars({"ALCHEMY_API_KEY": "key", "ETHERSCAN_API_KEY": ""}) == ["ETHERSCAN_API_KEY"]


def test_check_env_raises_for_missing_keys() -> None:
    with pytest.raises(RuntimeError, match="ALCHEMY_API_KEY, ETHERSCAN_API_KEY"):
        check_env.check_env({})


def test_main_checks_all_required_env(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("ALCHEMY_API_KEY", "alchemy")
    monkeypatch.setenv("ETHERSCAN_API_KEY", "etherscan")

    assert check_env.main() == 0
    assert capsys.readouterr().out == "Environment preflight ok.\n"
