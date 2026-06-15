---
name: tx2poc
description: Minimal workflow for turning an EVM transaction trace into a factual analysis and Foundry PoC.
---

Use this skill when the user provides an EVM chain and transaction hash and wants a Foundry PoC. Keep the workflow strict, but keep authoring rules minimal.

## Paths

All paths are relative to the repo root.

- `$CASE_DIR`: direct child of `cases/`.
- `$POC_FILE`: `$CASE_DIR/<poc_name>_exp.sol`.

If identity is unknown, start with a provisional folder. After role decision, rename to `yyyy-mm-<poc_name>-<txprefix>` and keep all generated files together.

## Workflow

Scripts write factual artifacts only. Codex writes roles, analysis, and Solidity.

1. Check fetch environment.

   Confirm the chain alias, RPC/key availability, and whether trace fetching can run.

   ```bash
   python scripts/check_env.py --chain <chain> --fetch
   ```

   Stop if required fetch access is missing.

2. Build factual trace artifacts.

   Fetch or reuse the transaction trace and write the script-owned files under `$CASE_DIR`.

   ```bash
   python scripts/trace_tx.py --chain <chain> --tx <txhash> --output-dir $CASE_DIR
   ```

   Expected output: `tx.json`, `receipt.json`, `block.json`, `trace.raw.json`, `trace.summary.txt`, and `tx_context.json`.

3. Fill evidence gaps only when needed.

   Decode important unknown calldata, or check metadata access before selective source/ABI/token queries.

   ```bash
   python scripts/decode_calldata.py <0x_calldata>
   python scripts/check_env.py --chain <chain> --metadata
   ```

   Use Etherscan/source/ABI/token metadata selectively for important undecoded contracts, proxy checks, tokens, or protocol behavior. Do not query just to add names.

   Useful selective evidence examples:

   - Unknown selector on a key exploit call: check 4byte, decode calldata, or query ABI/source.
   - Token role is unclear: query `symbol()`, `name()`, or `decimals()`.
   - Trace shows `DELEGATECALL A -> B` and header/source link depends on it: check explorer proxy metadata or common proxy slots/functions.
   - Helper behavior affects control flow: inspect verified source/ABI.

   See `references/evidence_commands.md` for command examples.

4. Decide exploit roles.

   Use `tx_context.json`, `trace.summary.txt`, calldata, and selective evidence to identify attacker, attack contract, vulnerable contract, victim, fork block, and PoC name. Inspect `delegatecall_pairs` for entry/state versus code-target roles, and inspect `call_evidence` for important helper scopes before writing the PoC.

   Expected output: `metadata.json`.

5. Check state-sensitive attacker addresses when needed.

   Before writing the PoC, probe pre-attack state only when trace/source suggests attacker address state affects behavior: self-call, attacker `DELEGATECALL`, EIP-7702-like execution, or `msg.sender`-keyed balances, credits, locks, debts, or allowances.

   ```bash
   python scripts/state_probe.py --chain <chain> --block <fork_block> --address <address> --token <token>
   ```

   Candidate addresses include tx sender, tx target/root attack contract, profit receiver, delegatecall caller/code target, and helper contracts that already existed before the tx. Choose relevant tokens and simple address-keyed `uint view(address)` probes from the trace/source. Use protocol-specific `cast call` for other state. Use results to decide normal local helpers vs historical-address execution such as `vm.etch`.

6. Author the analysis and PoC.

   Explain the exploit path in `attack_analysis.md`, then create `$POC_FILE` from `references/poc_template.sol`.

   Write the Solidity in three passes:

  - Structure pass: set imports, main test contract, helper contracts, function names, callbacks, fork, labels, and ordered key calls. Preserve trace call order and observed read sources here.
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
   forge test --match-path $POC_FILE -vv > $CASE_DIR/poc_run.log 2>&1
   ```

8. Review and iterate quality.

   Read `references/good_poc_rules.md`. When subagents are available, ask one subagent to review `metadata.json`, `attack_analysis.md`, `$POC_FILE`, and factual trace artifacts against those rules. The review must explicitly flag magic numbers, especially hardcoded trace-exact irregular amounts. A fixable magic number is `needs work`, not `pass`; derive it or document why derivation is unreliable. Apply concrete fixes and rerun Forge. Repeat for at most 3 review/fix rounds.

   If the PoC is still weak after 3 rounds, stop and tell the user which evidence, behavior, or quality rule still does not work.

   Write `generation_notes.md` with environment failures, evidence gaps, review rounds, fixes tried, remaining PoC flaws, and what to mention when returning the PoC.

   Write user-facing `final_review.md` with a concise attack summary, the final Forge command/result, the final good-poc-rules verdict, remaining weaknesses, and reviewer feedback. When the review points out a PoC problem, include the file path, line number, and a small code snippet.

No `attack_plan.md` or other intermediate planning artifact.

## Outputs

Script-owned factual files:

- `tx.json`, `receipt.json`, `block.json`, `trace.raw.json`
- `trace.summary.txt`
- `tx_context.json`

AI-owned files:

- `metadata.json`
- `attack_analysis.md`
- `<poc_name>_exp.sol`
- `generation_notes.md`
- `poc_run.log`
- `final_review.md`

`tx_context.json` is evidence, not final truth.

## Role Decision

Write `metadata.json` after deciding:

- `attacker`: tx sender or final profit receiver.
- `attack_contract`: attacker-controlled contract driving the call track.
- `vulnerable_contract`: real vulnerable implementation/source address when a proxy is confirmed; otherwise the protocol address whose behavior is exploited.
- `victim`: fund-losing account/entity only when distinct and trace-supported.

Do not mark routers, pairs, proxies, or public executors as vulnerable only because calls pass through them. If no distinct victim exists, set victim to the vulnerable contract. In proxy/state-escrow cases, the victim or asset-holder can be the entry/state proxy even when `vulnerable_contract` is the confirmed implementation/source address.

Choose `vulnerable_contract` as the trace-supported protocol address whose own behavior is the exploited failure point. If the exploited on-chain address is a proxy, use the real implementation/source address for `vulnerable_contract` and record the proxy/entry address separately in metadata or analysis.

Do not pick a contract only because it is noisy, central, or repeatedly used for checks.

If the trace shows an exploited protocol address delegatecalling another address, inspect `tx_context.json.delegatecall_pairs` and record both when useful:

- entry/state address: the address called by the attacker or protocol flow.
- code target: the delegatecall target that supplies executed code.

For multi-contract protocols, record separate roles when useful: exploited entry/state contract, code target/implementation, risk-check dependency, and asset holder/loss source.

Do not call an address a proxy from delegatecall alone. If proxy identity matters for the PoC header, source link, or interface choice, confirm it with source/explorer metadata, EIP-1967/beacon/admin slots, `implementation()`/`admin()` style functions, or a strong repeated fallback-delegate pattern.

## Format Conventions

- Start from `references/poc_template.sol`. Always use `../basetest.sol`; import `../interface.sol`, `../StableMath.sol`, or `../tokenhelper.sol` only when used. For common interfaces such as ERC20, WETH, pairs, pools, routers, or Balancer, check `../interface.sol` before writing a local interface.
- Use this Solidity header shape: `@KeyInfo` with `Attacker`, `Attack Contract`, `Vulnerable Contract`, and `Attack Tx`; then `@Info`; then short `@Analysis`. Format `@KeyInfo - Total Lost :` from the real transaction impact, with at most two decimals and a unit.
- Keep social/reference link lines in `@Analysis`; the link value may be empty. Insert one empty comment line before the PoC summary/root-cause comments.
- For proxy/delegatecall-based contracts, use the confirmed implementation/source address for the `Vulnerable Contract` header. Mention the proxy/entry address in analysis, labels, or metadata when it matters to the PoC.
- Put the main test contract that inherits `BaseTestWithBalanceLog` before helper contracts.
- Add short comments for key phases, formatted as `step 1: ...`, `step 2: ...`, etc.
- Do not use leading underscores in authored function names, including private/internal helpers, unless required by an existing interface.
- Preserve official token/protocol casing in `poc_name`, folder names, Solidity contract names, and file names when the name is a short symbol such as `SATX`, `USDC`, `GHO`, or `WETH`. Use lowercase only for generic descriptive names.
- Keep declarations scoped to the contract/helper that uses them. File-scope declarations are for shared addresses and interfaces.
- Keep numeric values near the logic that uses them. Only promote a number to a contract constant when it is reused across phases, names a protocol configuration, or improves a non-obvious formula. Clean setup amounts may stay inline or as local variables.

## PoC Conventions

- Fork at `tx_block - 1`.
- Treat incomplete recon as a blocker. If a core token/protocol/vulnerable contract identity, ABI/source/helper behavior, or address-sensitive behavior cannot be resolved well enough to name roles and write typed calls, stop and report the missing evidence instead of inventing address-prefix names or opaque fallbacks.
- Prefer readable reconstruction over opaque replay:
  - Use typed contract calls with named interfaces, addresses, and local variables.
  - Do not copy transaction input, large raw calldata blobs, or raw helper/orchestrator replay.
  - Build calldata or bytes from readable primitives. For ASCII callback markers, use forms like `bytes("1")`; for protocol-encoded data, use `abi.encode` or `abi.encodePacked` with named values.
  - Derive trace-exact irregular amounts from balances, reserves, allowances, function parameters, or return values. For no-arg helper calls, source changing amounts inside the helper scope from `call_evidence` or local reads. Use fixed trace amounts only when there is no reliable state-derived source.
- Rebuild attacker-controlled execution locally. Do not delegate the core exploit to historical attacker/coordinator/helper contracts.
- In PoC code, call the entry/state address seen in the trace. Use implementation/code-target evidence for interfaces, labels, and source links; do not call the implementation directly unless the trace does.
- Do not force local attacker or attack-contract addresses to match the trace. Use `vm.etch` at a historical address only when source or trace evidence shows exact `address(this)` behavior matters.
- Preserve core economics at a high level: asset provenance, callbacks, phase order, and state-dependent repetition should match the trace when they matter to the exploit.
- A tx trace cannot prove `for` vs `while`. Use `for` when the repeat count is a known fixed procedure. Use `while` when the repeat count should come from changing state: balances, reserves, price, debt, collateral, or output amount.
- Use `deal` only for explicit initial capital or non-core setup. Do not use it to replace protocol-acquired funds.
- Final profit handling should follow the trace's final asset and receiver role. If the trace has a clear final profit receiver, forward profit there and assert that receiver's balance change. Use a local test receiver only when the trace receiver is unclear or intentionally abstracted, and explain why.

Before finalizing, check:

- no placeholders or empty tests.
- no raw transaction input or opaque calldata replay.
- every exploit/profit phase named in `attack_analysis.md` appears in `$POC_FILE`, unless the analysis explicitly says that phase is intentionally omitted and why.
- key vulnerable calls and callbacks are present or the omission is explained.
- profit or state-change assertion passes.

## Script Map

- `check_env.py`: environment preflight.
- `trace_tx.py`: fetch trace, normalize it, and write summary/context artifacts.
- `decode_calldata.py`: decode one calldata payload.
- `state_probe.py`: probe pre-attack address/token/accounting state.

## References

- `references/poc_template.sol`: starting Solidity template.
- `references/good_poc_rules.md`: final quality review checklist.
- `references/evidence_commands.md`: command examples for selective evidence checks.
