from __future__ import annotations

import pytest

from _load_skill_module import load_tx2poc_script


check_env = load_tx2poc_script("check_env")


def test_missing_env_vars_reports_only_required_keys() -> None:
    assert check_env.missing_env_vars({}) == ["ETHERSCAN_API_KEY"]
    assert check_env.missing_env_vars({"ETHERSCAN_API_KEY": "key"}) == []
    # ALCHEMY_API_KEY is optional; its absence is not a missing requirement.
    assert check_env.missing_env_vars({"ETHERSCAN_API_KEY": "key", "ALCHEMY_API_KEY": ""}) == []


def test_check_env_raises_for_missing_required_key() -> None:
    with pytest.raises(RuntimeError, match="ETHERSCAN_API_KEY"):
        check_env.check_env({})


def test_check_env_passes_without_alchemy_key() -> None:
    check_env.check_env({"ETHERSCAN_API_KEY": "etherscan"})


def test_trace_source_prefers_alchemy_when_present() -> None:
    assert check_env.trace_source({"ALCHEMY_API_KEY": "key"}) == "alchemy"
    assert check_env.trace_source({}) == "blockscout (keyless)"


def test_main_reports_trace_source(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.delenv("ALCHEMY_API_KEY", raising=False)
    monkeypatch.setenv("ETHERSCAN_API_KEY", "etherscan")

    assert check_env.main() == 0
    assert capsys.readouterr().out == "Environment preflight ok. Trace source: blockscout (keyless).\n"
