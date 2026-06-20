# Agent Guide - tx2poc

`tx2poc` turns an EVM chain + tx hash into factual trace artifacts, analysis, and a Foundry fork PoC.

Use the live skills for workflow details. Do not use ad hoc workflow rules from old docs.

## Skills

Portable skills:

- `tx2poc` (`skills/tx2poc`): generate trace artifacts, analysis, and a Foundry PoC from a chain + tx hash.

Repo agent skills:

- `tx2poc-benchmark` (`.agents/skills/tx2poc-benchmark`): compare generated output against delayed DeFiHackLabs references.
- `defihacklabs-pr` (`.agents/skills/defihacklabs-pr`): export a finished tx2poc case into a local DeFiHackLabs fork, push a branch, and open a draft PR.
- `twitter-browser-mcp` (`.agents/skills/twitter-browser-mcp`): monitor configured X/Twitter accounts for on-chain attack alerts and extract tx/event details.

## Basics

- This repo already provides the expected layout, shared helpers, and `forge-std` submodule.
- Case output lives under `cases/<case>/`.
- Shared Solidity helpers live at `cases/basetest.sol`, `cases/interface.sol`, `cases/StableMath.sol`, and `cases/tokenhelper.sol`.
- The four shared helpers and matching `.sol` files under `skills/tx2poc/assets/foundry-helpers/` are DeFiHackLabs `src/test` copies; do not edit them during case work.
- After helper resync, check the four helper `.sol` files in both `cases/` and `skills/tx2poc/assets/foundry-helpers/` are up to date with DeFiHackLabs `src/test`.
- Python scripts fetch and normalize evidence only.
- Codex writes `metadata.json`, `attack_analysis.md`, `generation_notes.md`, and `<poc_name>_exp.sol`.

## Environment

- `ALCHEMY_API_KEY`: required for trace fetching.
- `ETHERSCAN_API_KEY`: required for source/ABI lookups.

## Commands

```bash
python skills/tx2poc/scripts/check_env.py
python skills/tx2poc/scripts/trace_tx.py --chain <chain> --tx <txhash> --output-dir cases/<case>
forge test --match-path cases/<case>/<poc_name>_exp.sol -vv
python -m pytest tests -q
```

## Submodules

```bash
git submodule update --init --recursive
git submodule update --remote --merge lib/forge-std
git add lib/forge-std
git commit -m "chore: update submodules"
```

## DeFiHackLabs PR

- Local DeFiHackLabs fork clone: `DeFiHackLabs/`
- Upstream repo: `SunWeb3Sec/DeFiHackLabs`
- Base remote: `upstream`
- Push remote: `origin`
- Base branch: `main`
- Branch prefix: `tx2poc/`

`DeFiHackLabs/` is a gitignored local clone of the user's fork. It is not a submodule and should not be committed to this repo.

## Guardrails

- Do not write generated files into `DeFiHackLabs/` except through `defihacklabs-pr` after the generated PoC exists.
- Do not inspect a same-transaction DeFiHackLabs sample before the generated PoC exists.
- Do not infer token/protocol names from folder names or old generated files.
- Do not leave TODO/FIXME placeholders, compile-only tests, raw replay, or trace-frame comments in generated PoCs.
