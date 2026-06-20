# tx2poc

`tx2poc` is an agent skill for turning an EVM transaction ID into a Foundry fork PoC.

This project is sponsored by the [DeFiHackLabs AI Credits Initiative](https://x.com/1nf0s3cpt/status/2060346469580992727).


## Requirements

- Etherscan API key for source/ABI lookup, set as `ETHERSCAN_API_KEY`.
- Foundry, for running generated PoCs with `forge test`.
- Trace fetching, via either:
  - Keyless public Blockscout (default when no Alchemy key is set), or
  - Alchemy API key for richer trace access (paid), set as `ALCHEMY_API_KEY`.

  Pick a source explicitly with `trace_tx.py --source {auto,alchemy,blockscout}` (`auto` is the default). Blockscout supports ethereum, optimism, base, arbitrum, polygon, and gnosis.


## Basic Use

Open this repo as the agent root folder, then ask for `$tx2poc` with a chain name and tx hash:

```txt
$tx2poc eth 0x1234...<txid>
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
- `skills/tx2poc/`: portable tx2poc skill, scripts, data, and references.
- `.agents/skills/`: repo-local Codex automation skills.
- `DeFiHackLabs/`: gitignored local clone of the user's DeFiHackLabs fork, used by `defihacklabs-pr`.
- `lib/forge-std/`: Foundry test dependency submodule.

## Submodules

This repo uses a git submodule for the Foundry dependency. After cloning:

```bash
git submodule update --init --recursive
```

For DeFiHackLabs PR work, clone your fork into `DeFiHackLabs/` and add the official repo as `upstream`.

## Limitations

- Portable with setup, but not zero-install. It needs Foundry, forge-std, the shared helper files, and an Etherscan key.
- Keyless trace fetching relies on public Blockscout availability and is limited to its supported chains; Alchemy is the fallback for other chains or when Blockscout is rate-limited.
- Large or complex tx traces may be incomplete or inaccurate. Generated analysis and PoCs still need human review.
