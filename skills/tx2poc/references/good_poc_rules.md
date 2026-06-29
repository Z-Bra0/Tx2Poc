# Good PoC Rules

## PoC Quality Criteria

### Core Validity

- Forge passes with the intended exploit test.
- No placeholders, empty tests, TODO/FIXME, or compile-only assertions.
- The PoC must demonstrate a trace-supported exploited behavior and resulting profit, loss, or abnormal state transition; routine transfers, approvals, swaps, or admin calls without exploit impact are not valid PoCs.
- If the tx only withdraws or sells an attacker/owner/deployer/privileged balance, it is not a standalone attack PoC. Classify it as either `partial attack` when the real setup/exploit is in an earlier tx, or `rug pull` when it only monetizes controlled funds.
- Pre-existing attacker funds are allowed only as seed capital or required setup. The PoC must still show a permissionless or unauthorized vulnerable behavior moving victim/protocol-controlled assets.
- Assert pre/post impact where practical, not only a positive ending balance.
- If core identity, ABI/source, helper behavior, or exact address behavior is unclear, report the blocker instead of inventing names or opaque fallbacks.
- Closed source alone is not a blocker. If a key victim, implementation, router/callback target, or attacker helper is closed source and its internals materially affect root-cause identification, flag it in `final_review.md` and `evidence/generation_notes.md` as an unresolved evidence caveat. It is a blocker only when the PoC must guess unseen behavior instead of proving the behavior from trace-supported calls, balances, state reads, bytecode/ABI, or reliable public evidence.
- Decompiled code may be used as supporting evidence to strengthen root-cause analysis for closed-source contracts, but label it as inferred evidence rather than verified source. Do not cite decompiler output as verified source or copy large unreviewed decompiler blobs into the PoC.
- `metadata.json`, `attack_analysis.md`, and the Solidity agree on attacker, attack contract, vulnerable implementation/source address, fork block, and profit asset. Put proxy, entry, and victim roles in metadata or analysis when useful.
- `attack_analysis.md` only claims phases that appear in the PoC, unless an omission is explicit and justified.

### Roles and Evidence

- Names and roles come from trace evidence, source/ABI, token metadata, or other trusted evidence.
- Set `attack_contract` to the attacker-controlled contract that performs the exploit logic, not a thin deployer/wrapper. Record wrappers separately as `attack_deployer` or `root_deployer`.
- When block data is available, document `block_miner` in `metadata.json`. Do not mark the block miner / block builder as `attacker`, `profit_receiver`, `refund_receiver`, or `victim` based only on a final native-token transfer to that address; classify that transfer as `builder_payment` or `coinbase_payment`.

### Address-Sensitive State

- If the trace uses self-call, attacker `DELEGATECALL`, EIP-7702-like execution, or custom `msg.sender` accounting, compare historical attacker/attack-contract state with local PoC state before choosing fresh local helpers.
- Probe relevant balances, allowances, and simple address-keyed views such as `creditOf`, `creditlessOf`, `lockedOf`, or `debtOf` by passing explicit selectors. Use protocol-specific calls for epoch/snapshot/collateral state. Do not use `vm.etch`; if exact historical address/code injection is unavoidable, report a blocker instead.
- If a historical attack address only matters because a pre-existing callee/helper stores address-keyed state, patch that callee/helper state to recognize the fresh PoC contract and assert the checked state. Do not use `vm.etch` to bypass address-sensitive state.

### Exploit Clarity

- Show the exploit, not the whole trace: precondition, vulnerable behavior, attacker action, and profit or state impact.
- Keep only setup, exploit-triggering calls, required callbacks, and accounting needed to trigger or prove the exploit.
- Omit wrappers, historical transfers, and unrelated balance movement unless they affect permissions, pricing, state, repayment, or profit.
- Prefer a linear `testExploit`; do not hide the vulnerable call or profit assertion behind generic wrappers.

### Factual Fidelity

- Preserve core economics: asset provenance, callbacks, phase order, repeated state-dependent actions, and final profit path.
- Track asset provenance before treating profit as exploit impact. Own-balance withdrawal/sale is `partial attack` or `rug pull`, not a complete attack PoC.
- If the trace has a clear final profit receiver, the PoC should forward profit there and assert that receiver's balance change. If the trace forwards funds through an attacker-controlled root/coordinator before reaching the final receiver, reproduce that forwarding step. Local test receivers need an explicit reason.
- Use `deal` only for initial capital or non-core setup, not to replace protocol-acquired funds.
- Use a normal local attacker/helper; if exact historical `address(this)` behavior matters and cannot be represented by targeted state patching, report a blocker.
- A tx trace cannot prove `for` vs `while`. Use `for` when the repeat count is a known fixed procedure. Use `while` when the repeat count should come from changing state: balances, reserves, price, debt, collateral, or output amount.

### Lean Code

- Temporary debug logs, probes, and one-off diagnostic variables are removed.
- Do not define Solidity constants, labels, interfaces, or helpers for addresses/contracts that are only metadata roles and are not used by the executable PoC. Keep unused historical roles in `metadata.json`, `attack_analysis.md`, and header comments only.
- Avoid single-use wrappers around one external call, `userCmd`, or `abi.encode`. Inline the call at the exploit step unless the helper is reused or hides real multi-step logic. For one-off command IDs/selectors, prefer an adjacent comment or same-scope local only when it improves clarity; do not replace a wrapper with file-scope constants for values used once.

### Typed Reconstruction

- Prefer typed calls and named interfaces over raw replay.
- Do not copy transaction input, large raw calldata blobs, or raw helper/orchestrator replay.
- Build calldata or bytes from readable primitives such as `bytes("1")`, `abi.encode`, or `abi.encodePacked` with named values.
- Final PoCs retain raw calldata only when the selector and fields are decoded, named, and evidence-backed.

### Numbers and Assertions

- Numeric literals are acceptable when they are common units or protocol constants: `1e18`, bps denominators, ERC20 decimals, small fixed loop counts, documented enum IDs, and values copied from verified source.
- Derive irregular amounts from same-scope balances, reserves, allowances, return values, calldata parameters, or verified constants when those sources are available.
- Retained trace-exact irregular amounts have a documented trace/source and rationale in `evidence/generation_notes.md`.
- If a helper call has no amount parameter, derive the amount inside that helper from same-scope call outputs, balances, reserves, or state reads.
- Native-token amounts may come from `address(target).balance`. `callTracer` does not show this opcode read, so use trace value movement as evidence when a native market/account sends the same amount later.
- Avoid exact trace-profit assertions unless exact value equality is the exploit property. Prefer threshold/range assertions such as `assertGt(profit, expectedMinimum)` so the PoC proves impact without overfitting dust-level trace output.
- Keep clean setup amounts near the step that uses them. Promote numbers to constants only when reused, protocol-configured, or clarifying a formula.
- Keep fork blocks, flash-loan amounts, seed amounts, minimum-profit thresholds, trace-exact amounts, and one-off selectors local to the use site.
- Avoid huge bound/sentinel literals such as long runs of 9s. Use `type(uint256).max`, verified protocol constants, or small expressions derived from verified bounds. If a large literal must remain, keep it near the use site and cite the source in `evidence/generation_notes.md`.

## DeFiHackLabs Format Requirements

### PoC Header Format

- Follows this header shape:

```solidity
// @KeyInfo - Total Lost : 123.45 USDC
// Attacker : 0x00000000000000000000000000000000cafebabe
// Attack Contract : 0x00000000000000000000000000000000deadbeef
// Vulnerable Contract : 0x00000000000000000000000000000000baddcafe
// Attack Tx : https://skylens.certik.com/tx/eth/0x123456789
//
// @Info
// Vulnerable Contract Code : https://etherscan.io/address/0x00000000000000000000000000000000baddcafe#code
//
// @Analysis
// Twitter Guy : https://x.com/1nf0s3cpt/status/1583011233363824640
//
// Attack summary: ...
// Root cause: ...
```

- Header values are plain final text. Do not wrap addresses or links in `{}` and do not prefix links with `link:`.
- X/Twitter, Telegram, or empty source links go on the `// Twitter Guy :` line.
- `@KeyInfo - Total Lost :` reflects real transaction impact, not generated PoC output, and uses at most two decimals plus a unit.
- In named `@KeyInfo` and `@Info` fields, every value except total lost should be an address, an address link, or a transaction link.

### Solidity Layout, Imports, And Helpers

- All imports are used. Import shared helpers only when referenced: `../interface.sol`, `../StableMath.sol`, `../tokenhelper.sol`.
- Check `../interface.sol` before declaring any local interface. If the needed interface or function signature already exists there, import and use it; reimplementation in the PoC is `needs work`.
- Reuse shared helpers before writing local code: `StableMath.sol` for Balancer stable math and `tokenhelper.sol`/`TokenHelper` for token helpers. Define local interfaces or helpers only for trace-specific surfaces missing from shared helpers.
- Keep the main `BaseTestWithBalanceLog` contract first.
- Name the main test contract `ContractTest`; do not use lower snake case names such as `<poc_name>_exp` for Solidity contract names.
- Preserve official short-symbol casing.
- Use EIP-55 checksummed address literals for fixed EVM addresses. Avoid `address(bytes20(hex"..."))` or similar wrappers unless the conversion itself is part of the behavior being tested.
- Avoid leading underscores in authored helper names.
- Use short numbered phase comments such as `step 1:` and `step 2:` for setup, trigger, callback/repay, and profit assertion; avoid trace-frame narration.
- Use `vm.createSelectFork("<chain-alias>", forkBlock)` with a local `forkBlock`, where `<chain-alias>` is defined in `[rpc_endpoints]` in `foundry.toml`; do not use `vm.envOr(...)` or hardcoded provider URLs in Solidity, because provider selection belongs in `foundry.toml`.
- Fork at the block before the attack transaction, usually `attackBlock - 1`, unless same-block state is required and documented.
