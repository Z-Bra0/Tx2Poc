# tx2poc

`tx2poc` is an agent skill for turning an EVM transaction ID into a Foundry fork PoC.

This project is sponsored by the [DeFiHackLabs AI Credits Initiative](https://x.com/1nf0s3cpt/status/2060346469580992727).


## Requirements

- Alchemy API key, trace fetching (paid), set as `ALCHEMY_API_KEY`.
- Etherscan API key, source/ABI lookup, set as `ETHERSCAN_API_KEY`.
- Foundry, for running generated PoCs with `forge test`.


## Basic Use

Open this repo as the agent root folder, then ask for `$tx2poc` with a chain name and tx hash:

```txt
Use $tx2poc for chain ethereum and tx 0x...
```

The skill handles trace fetching, evidence, role decisions, analysis, PoC authoring, and verification. Output goes under `cases/<case>/`.


## tx2poc Skill Workflow

1. Fetch transaction, receipt, block, and call trace.
2. Normalize the trace into readable summaries and factual context.
3. Decode calldata and query source/token evidence only when needed.
4. Decide attacker, attack contract, vulnerable contract, victim, and fork block.
5. Write `metadata.json`, `attack_analysis.md`, and the Foundry PoC.
6. Run and iterate the PoC until it passes or a blocker is clear.


## Repo Layout

- `cases/`: generated tx cases, factual artifacts, analysis, and PoCs.
- `cases/basetest.sol`, `cases/interface.sol`, `cases/StableMath.sol`, `cases/tokenhelper.sol`: shared Solidity helpers.
- `tests/`: offline Python tests for tx2poc helper scripts.
- `.agents/skills/tx2poc/`: live Codex skill, scripts, data, and references.
- `DeFiHackLabs/`: external reference corpus. Do not write generated tx2poc output here.

## DeFiHackLabs Submodule

```bash
git submodule update --remote --merge DeFiHackLabs
```

## Limitations

- Not plug-and-play portable. It depends on Foundry, API keys, RPC behavior, and this repo layout.
- Trace fetching requires paid Alchemy access.
- Not 100% accurate. Generated analysis and PoCs still need human review.
