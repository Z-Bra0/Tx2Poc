# Agent Guide - tx2poc

`tx2poc` turns an EVM chain + tx hash into factual trace artifacts, analysis, and a Foundry fork PoC.

Use the live skills for workflow details. Do not use ad hoc workflow rules from old docs.

## Skills

- `tx2poc`: generate trace artifacts, analysis, and a Foundry PoC from a chain + tx hash.
- `tx2poc-benchmark`: compare generated output against delayed DeFiHackLabs references.

## Basics

- Case output lives under `cases/<case>/`.
- Shared Solidity helpers live at `cases/basetest.sol`, `cases/interface.sol`, `cases/StableMath.sol`, and `cases/tokenhelper.sol`.
- Python scripts fetch and normalize evidence only.
- Codex writes `metadata.json`, `attack_analysis.md`, `generation_notes.md`, and `<poc_name>_exp.sol`.

## Environment

- `ALCHEMY_API_KEY`: required for trace fetching.
- `ETHERSCAN_API_KEY`: required for source/ABI lookups.

## Commands

```bash
python .agents/skills/tx2poc/scripts/check_env.py --chain <chain> --fetch
python .agents/skills/tx2poc/scripts/trace_tx.py --chain <chain> --tx <txhash> --output-dir cases/<case>
forge test --match-path cases/<case>/<poc_name>_exp.sol -vv
python -m pytest tests -q
```

## Guardrails

- Do not write generated files into `DeFiHackLabs/`.
- Do not inspect a same-transaction DeFiHackLabs sample before the generated PoC exists.
- Do not infer token/protocol names from folder names or old generated files.
- Do not leave TODO/FIXME placeholders, compile-only tests, raw replay, or trace-frame comments in generated PoCs.
