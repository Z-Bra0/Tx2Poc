---
name: tx2poc-benchmark
description: Grade live tx2poc output against delayed DeFiHackLabs references.
---

Use this skill to benchmark the live `tx2poc` skill with an existing DeFiHackLabs testcase.

The benchmark does not auto-improve or copy skills. It delegates generation to live `tx2poc`, writes an AI grade, then stops for manual review.

## Core Rule

Do not inspect the same-tx DeFiHackLabs PoC body before generation. Use it only after the generated PoC exists.

## Generation Isolation

Run generation in a subagent.

The subagent receives only:

- chain name
- tx hash
- instruction to use the live `tx2poc` skill

Do not pass the subagent any benchmark/reference context:

- no DeFiHackLabs path
- no case name or victim name from the reference
- no reference header lines
- no loss amount
- no attacker/victim/protocol addresses copied from the reference
- no suspected root cause from the benchmark driver

The subagent must discover all roles and write all generated artifacts from live tx2poc evidence only.

## Workflow

1. Determine the benchmark chain and tx hash.
2. Optionally locate the matching DeFiHackLabs reference path, but do not read the body or pass that path to the generation subagent.
3. Start a generation subagent with only the chain, tx hash, and instruction to use the live `tx2poc` skill.
4. The subagent generates or updates the case under `cases/<case>/` and returns the generated case path.
5. After the generated PoC exists, the benchmark driver may inspect:
   - generated `_exp.sol`
   - `trace.summary.txt`
   - `attack_analysis.md`
   - `metadata.json`, `generation_notes.md`, and `final_review.md` when present
   - `tx2poc`'s `references/good_poc_rules.md`
   - same-tx DeFiHackLabs reference PoC
6. Write the benchmark result under `cases/<case>/benchmark/`.
7. Stop and wait for manual review.

## Output

```text
cases/<case>/
  benchmark/
    ai_grade.md
    metadata.json
```

`metadata.json` records the chain, tx hash, generated PoC path, reference path, grade, and score.

## Grading

Read `tx2poc`'s `references/good_poc_rules.md` and use it as the PoC quality checklist. Do not duplicate that checklist here; cite the relevant good-poc rule when a quality issue appears.

Grade on:

- `good_poc_rules`: pass/needs-work verdict and the highest-impact checklist violations.
- `trace_match`: fork block, call order, callbacks, value movement, and profit path compared with factual trace artifacts.
- `reference_delta`: useful differences between generated output and the same-tx DeFiHackLabs reference.
- `benchmark_hygiene`: reference isolation, generated case location, metadata completeness, and no exact reference copy.

Do not treat the reference as perfect. Prefer trace evidence when the reference simplifies or diverges from the real path.

## Reference Policy

The same-tx DeFiHackLabs file is an eval reference, not authoring context.

- Before generation: do not read or copy it.
- During grading: compare it with trace evidence and the generated output.
- Do not run the same-tx reference PoC.
- Do not turn reference-only knowledge into a rule.
