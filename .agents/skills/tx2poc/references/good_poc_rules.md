# Good PoC Rules

Use this checklist for final review. Keep feedback concrete and limited to issues that materially improve the PoC.

## Basic

- Forge passes with the intended exploit test.
- `metadata.json`, `attack_analysis.md`, and the Solidity agree on attacker, attack contract, vulnerable implementation/source address, fork block, and profit asset. Put proxy, entry, and victim roles in metadata or analysis when useful.
- `@KeyInfo - Total Lost :` is based on real transaction impact, not generated PoC output, and uses at most two decimals plus a unit.
- Social/reference link lines are kept in `@Analysis`, with empty links allowed, followed by one empty comment line before the PoC summary/root-cause comments.
- All imports are used. Do not import `../interface.sol` unless at least one interface/type from it is referenced; check it before writing common local interfaces.
- No placeholders, empty tests, TODO/FIXME, or compile-only assertions.
- Names and roles come from trace evidence, source/ABI, token metadata, or other trusted evidence.
- If core identity, ABI/source, helper behavior, or exact address behavior is unclear, report the blocker instead of inventing names or opaque fallbacks.
- `attack_analysis.md` only claims phases that appear in the PoC, unless an omission is explicit and justified.
- Preserve core economics: asset provenance, callbacks, phase order, repeated state-dependent actions, and final profit path.
- If the trace has a clear final profit receiver, the PoC should forward profit there and assert that receiver's balance change. Local test receivers need an explicit reason.
- Use `deal` only for initial capital or non-core setup, not to replace protocol-acquired funds.
- Use a normal local attacker/helper unless source or trace proves exact historical `address(this)` behavior matters.
- A tx trace cannot prove `for` vs `while`. Use `for` when the repeat count is a known fixed procedure. Use `while` when the repeat count should come from changing state: balances, reserves, price, debt, collateral, or output amount.

## Address-Sensitive State

- If the trace uses self-call, attacker `DELEGATECALL`, EIP-7702-like execution, or custom `msg.sender` accounting, compare historical attacker/attack-contract state with local PoC state before choosing fresh local helpers.
- Probe relevant balances, allowances, and simple address-keyed views such as `creditOf`, `creditlessOf`, `lockedOf`, or `debtOf`. Use protocol-specific calls for epoch/snapshot/collateral state. If historical state matters, use `vm.etch` or historical-address execution and explain why.

## Format

- Keep the main `BaseTestWithBalanceLog` contract first.
- Preserve official short-symbol casing.
- Avoid leading underscores in authored helper names.
- Add short `step N:` comments for key phases.

## Calldata

- Prefer typed calls and named interfaces over raw replay.
- Do not copy transaction input, large raw calldata blobs, or raw helper/orchestrator replay.
- Build calldata or bytes from readable primitives such as `bytes("1")`, `abi.encode`, or `abi.encodePacked` with named values.
- If raw calldata remains, decode the selector and fields, replace it with typed calls or named encoded values, or mark it as `needs work` with the missing ABI/source evidence.

## Magic Numbers

- Any fixable hardcoded trace-exact irregular amount is `needs work`, not `pass`. Derive it from balances, reserves, allowances, function parameters, return values, or other state reads when a reasonable source exists. Retain a fixed value only after derivation was attempted and unreliable; keep it local and record the trace/source and reason in `generation_notes.md`.
- Use `tx_context.json.call_evidence` before keeping an irregular amount. If a helper call has no amount parameter, derive the amount inside that helper from same-scope call outputs, balances, reserves, or state reads.
- When the source of a magic amount is unclear, add temporary logs for likely sources before keeping it: caller balance, helper balance, pool balance, reserve values, allowance, callback delta, and repayment amount. Use those logs to test derivation candidates.
- Native-token amounts may come from `address(target).balance`. `callTracer` does not show this opcode read, so use trace value movement as evidence when a native market/account sends the same amount later.
- Avoid exact trace-profit assertions unless exact value equality is the exploit property. Prefer threshold/range assertions such as `assertGt(profit, expectedMinimum)` so the PoC proves impact without overfitting dust-level trace output.
- Keep clean setup amounts near the step that uses them; promote numbers to constants only when reused, protocol-configured, or clarifying a formula.

## Review Output

Return:

- `pass` or `needs work`
- top blocking issues, with file/line references when possible
- magic-number audit: list unresolved magic numbers, derivation attempted, and why each retained value could not be derived; otherwise `none`
- concrete fixes to try next
- whether another iteration is worth doing

When reporting a concrete PoC problem, include:

- file path
- line number
- a small code snippet
- why it violates this checklist
- the concrete fix to try

## Final Cleanup

Before returning `pass`, remove temporary debug logs, probes, and one-off diagnostic variables from the PoC, then rerun Forge with `-vv` and save the final user-facing log to `poc_run.log`. Do not use `-vvvv` for the saved log.

## Generation Notes

After review/fix rounds, the main agent writes `generation_notes.md` before returning the PoC:

- `Environment`: RPC/explorer/test failures and fallbacks used.
- `Evidence gaps`: unresolved identity, ABI/source, helper, or address-sensitive behavior gaps.
- `Review rounds`: reviewer result, fixes applied, and Forge result for each round.
- `Remaining flaws`: known PoC weaknesses, unresolved magic numbers, and intentional omissions.
- `Return summary`: short points to mention to the user with the PoC.

## Final Review

After the last review/fix round, write `final_review.md` as the user-facing summary:

- `Attack Summary`: concise exploit path and impact.
- `Forge Result`: exact `forge test --match-path ... -vv` command and pass/fail result from `poc_run.log`.
- `Good PoC Rules Review`: final verdict and high-signal findings.
- `Line-Specific Findings`: every remaining PoC issue with file path, line number, and a small code snippet; write `None` when no blocking issues remain.
- `Remaining Weaknesses`: evidence gaps, fixture limitations, or intentional omissions that are not blockers.
