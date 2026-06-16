---
name: tx2poc
description: Minimal workflow for turning an EVM transaction trace into a factual analysis and Foundry PoC.
---

Use this skill when the user provides an EVM chain and transaction hash and wants a Foundry PoC. Keep the workflow strict, but keep authoring rules minimal.

## Paths

Use the current workspace root as the target repo. `$SKILL_DIR` is the directory containing this `SKILL.md`.
When running shell examples, set `SKILL_DIR` to that absolute path or substitute the absolute path directly.

Skill-owned paths are under `$SKILL_DIR`: `scripts/`, `references/`, `assets/`, `data/`.
Workspace-owned paths are under the target repo root: `cases/`, `lib/`, generated artifacts, and Foundry config.

- `$CASE_DIR`: direct child of `cases/`.
- `$POC_FILE`: `$CASE_DIR/<poc_name>_exp.sol`.
- `$EVIDENCE_DIR`: `$CASE_DIR/evidence`.

If identity is unknown, start with a provisional folder. After role decision, rename to `yyyy-mm-<poc_name>-<txprefix>`. Keep user-facing files in `$CASE_DIR`; keep script-owned factual artifacts and logs in `$EVIDENCE_DIR`.

## Workspace Setup

Requires Foundry/Forge, git/network access when `forge-std` is missing, `ALCHEMY_API_KEY` for trace fetching, and `ETHERSCAN_API_KEY` for source/ABI lookup.

Before fetching traces:

- Run `python "$SKILL_DIR/scripts/setup_workspace.py"` from the workspace root.
- This creates `cases/`, copies missing helper files, writes missing `foundry.toml`/`remappings.txt` from bundled assets, and installs missing `forge-std`.
- `setup_workspace.py` installs the current `forge-std` when missing. Use `--forge-std-ref <tag-or-commit>` only when the user explicitly asks for a pinned dependency.
- Do not reinstall or overwrite existing helpers/config when they already exist.

## Workflow

Scripts write factual artifacts only. Codex writes roles, analysis, and Solidity.

1. Check fetch environment.

   Confirm required RPC and explorer API keys are available.

   ```bash
   python "$SKILL_DIR/scripts/check_env.py"
   ```

   Stop if required access is missing.

2. Build factual trace artifacts.

   Fetch or reuse the transaction trace. `trace_tx.py` takes the case folder as `--output-dir` and writes script-owned factual files under `$EVIDENCE_DIR`.

   ```bash
   python "$SKILL_DIR/scripts/trace_tx.py" --chain <chain> --tx <txhash> --output-dir $CASE_DIR
   ```

   Expected output: `$EVIDENCE_DIR/tx.json`, `$EVIDENCE_DIR/receipt.json`, `$EVIDENCE_DIR/block.json`, `$EVIDENCE_DIR/trace.raw.json`, `$EVIDENCE_DIR/trace.summary.txt`, and `$EVIDENCE_DIR/tx_context.json`.

3. Fill evidence gaps only when needed.

   Decode important unknown calldata, or check metadata access before selective source/ABI/token queries.

   ```bash
   python "$SKILL_DIR/scripts/decode_calldata.py" <0x_calldata>
   python "$SKILL_DIR/scripts/check_env.py"
   ```

   Use Etherscan/source/ABI/token metadata selectively for important undecoded contracts, proxy checks, tokens, or protocol behavior. Do not query just to add names.

   Useful selective evidence examples:

   - Unknown selector on a key exploit call: check 4byte, decode calldata, or query ABI/source.
   - Token role is unclear: query `symbol()`, `name()`, or `decimals()`.
   - Trace shows `DELEGATECALL A -> B` and header/source link depends on it: check explorer proxy metadata or common proxy slots/functions.
   - Helper behavior affects control flow: inspect verified source/ABI.

   See `$SKILL_DIR/references/evidence_commands.md` for command examples.

4. Decide exploit roles.

   Use `$EVIDENCE_DIR/tx_context.json`, `$EVIDENCE_DIR/trace.summary.txt`, calldata, and selective evidence to identify attacker, root/coordinator contract, attack receiver/helper contracts, vulnerable contract, victim, fork block, final profit asset/receiver, and PoC name. Inspect `delegatecall_pairs` for entry/state versus code-target roles, inspect `call_evidence` for important helper scopes, and trace the final profit transfer path before writing the PoC.

   Expected output: `metadata.json`.

5. Check state-sensitive attacker addresses when needed.

   Before writing the PoC, probe pre-attack state only when trace/source suggests attacker address state affects behavior: self-call, attacker `DELEGATECALL`, EIP-7702-like execution, or `msg.sender`-keyed balances, credits, locks, debts, or allowances.

   ```bash
   python "$SKILL_DIR/scripts/state_probe.py" --chain <chain> --block <fork_block> --address <address> --token <token>
   ```

   Candidate addresses include tx sender, tx target/root attack contract, profit receiver, delegatecall caller/code target, and helper contracts that already existed before the tx. Choose relevant tokens and simple address-keyed `uint view(address)` probes from the trace/source. Use protocol-specific `cast call` for other state. Use results to decide normal local helpers vs historical-address execution such as `vm.etch`.

6. Author the analysis and PoC.

   Explain the exploit path in `attack_analysis.md`, then create `$POC_FILE` from `$SKILL_DIR/references/poc_template.sol`.

   Write the Solidity in three passes:

   - Structure pass: set imports, main test contract, helper contracts, function names, callbacks, fork, labels, ordered key calls, and final profit forwarding. Preserve trace call order and observed read sources here.
   - Detail pass: fill typed calls, parameters, derived amounts, callback data, funding, repayment, and assertions. Derive values from the same-scope args, call outputs, balances, reserves, or state reads seen in the trace when available.
   - Polish pass: add short `step N:` comments, remove temporary scaffolding, check naming/style, and ensure no placeholders remain.

   Expected output: `attack_analysis.md` and `$POC_FILE`.

7. Verify the generated PoC.

   Run Forge, inspect failures, and update the PoC until the intended exploit test passes or a blocker is clear.

   ```bash
   forge test --match-path $POC_FILE -vv
   ```

   After the final passing run, capture the user-facing run log with `-vv`, not `-vvvv`.

   ```bash
   forge test --match-path $POC_FILE -vv > $EVIDENCE_DIR/poc_run.log 2>&1
   ```

8. Review and iterate quality.

   Read `$SKILL_DIR/references/good_poc_rules.md`. When subagents are available, ask one subagent to review `metadata.json`, `attack_analysis.md`, `$POC_FILE`, and factual trace artifacts against those rules. The review must explicitly flag magic numbers, especially hardcoded trace-exact irregular amounts. A fixable magic number is `needs work`, not `pass`; derive it or document why derivation is unreliable. Apply concrete fixes and rerun Forge. Repeat for at most 3 review/fix rounds.

   If the PoC is still weak after 3 rounds, stop and tell the user which evidence, behavior, or quality rule still does not work.

   Write `$EVIDENCE_DIR/generation_notes.md` with environment failures, evidence gaps, review rounds, fixes tried, remaining PoC flaws, and what to mention when returning the PoC.

   Write user-facing `final_review.md` with a concise attack summary, the final Forge command/result from `$EVIDENCE_DIR/poc_run.log`, the final good-poc-rules verdict, remaining weaknesses, and reviewer feedback. When the review points out a PoC problem, include the file path, line number, and a small code snippet.

No `attack_plan.md` or other intermediate planning artifact.

## Outputs

Script-owned factual files:

- `evidence/tx.json`, `evidence/receipt.json`, `evidence/block.json`, `evidence/trace.raw.json`
- `evidence/trace.summary.txt`
- `evidence/tx_context.json`

User-facing AI-owned files:

- `metadata.json`
- `attack_analysis.md`
- `<poc_name>_exp.sol`
- `final_review.md`

Non-user-facing AI-owned files:

- `evidence/generation_notes.md`
- `evidence/poc_run.log`

`evidence/tx_context.json` is evidence, not final truth.

## Role Decision

Write `metadata.json` after deciding:

- `attacker`: tx sender or final profit receiver.
- `attack_contract`: attacker-controlled contract driving the call track.
- `vulnerable_contract`: real vulnerable implementation/source address when a proxy is confirmed; otherwise the protocol address whose behavior is exploited.
- `victim`: fund-losing account/entity only when distinct and trace-supported.
- `block_miner`: `block.json.miner` / block beneficiary when present.

Do not mark routers, pairs, proxies, or public executors as vulnerable only because calls pass through them. If no distinct victim exists, set victim to the vulnerable contract. In proxy/state-escrow cases, the victim or asset-holder can be the entry/state proxy even when `vulnerable_contract` is the confirmed implementation/source address.

Choose `vulnerable_contract` as the trace-supported protocol address whose own behavior is the exploited failure point. If the exploited on-chain address is a proxy, use the real implementation/source address for `vulnerable_contract` and record the proxy/entry address separately in metadata or analysis.

Do not pick a contract only because it is noisy, central, or repeatedly used for checks.

If the trace shows an exploited protocol address delegatecalling another address, inspect `tx_context.json.delegatecall_pairs` and record both when useful:

- entry/state address: the address called by the attacker or protocol flow.
- code target: the delegatecall target that supplies executed code.

For multi-contract protocols, record separate roles when useful: exploited entry/state contract, code target/implementation, risk-check dependency, and asset holder/loss source.

Do not call an address a proxy from delegatecall alone. If proxy identity matters for the PoC header, source link, or interface choice, confirm it with source/explorer metadata, EIP-1967/beacon/admin slots, `implementation()`/`admin()` style functions, or a strong repeated fallback-delegate pattern.

## PoC Authoring Guardrails

Detailed format and quality rules live in `$SKILL_DIR/references/good_poc_rules.md`. Keep this section to early decisions that shape the PoC.

- Start from `$SKILL_DIR/references/poc_template.sol`; import shared helpers only when used, and check `../interface.sol` before writing common local interfaces.
- Name the main test contract `ContractTest` and put the `BaseTestWithBalanceLog` contract before helper contracts.
- Fork at `tx_block - 1` with `vm.createSelectFork("<chain-alias>", forkBlock);`. Do not build provider URLs in Solidity.
- Treat unresolved core identity, ABI/source, helper behavior, or address-sensitive behavior as a blocker.
- Prefer typed, readable reconstruction over raw transaction input, large calldata blobs, or opaque replay.
- Derive irregular trace amounts from nearby balances, reserves, allowances, call outputs, parameters, or state reads when reliable.
- Rebuild attacker-controlled execution with local helpers. Use historical addresses only when evidence shows exact address behavior matters.
- Call the trace entry/state address. Use implementation/code-target evidence for interfaces, labels, and source links.
- Preserve core economics: asset provenance, callbacks, phase order, state-dependent repetition, final forwarding, and profit/state assertion.
- Keep declarations and numeric values scoped near the logic that uses them.

## Script Map

- `setup_workspace.py`: prepare a workspace by adding missing Foundry config, shared helpers, and `forge-std`.
- `check_env.py`: environment preflight.
- `trace_tx.py`: fetch trace, normalize it, and write summary/context artifacts.
- `decode_calldata.py`: decode one calldata payload.
- `state_probe.py`: probe pre-attack address/token/accounting state.

## References

- `references/poc_template.sol`: starting Solidity template.
- `references/good_poc_rules.md`: detailed PoC quality checklist.
- `references/evidence_commands.md`: command examples for selective evidence checks.

## Assets

- `assets/foundry-helpers/`: shared Solidity helpers plus Foundry config/remapping templates for workspace setup.
