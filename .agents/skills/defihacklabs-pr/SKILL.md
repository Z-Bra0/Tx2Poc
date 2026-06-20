---
name: defihacklabs-pr
description: Export a completed tx2poc case into a local DeFiHackLabs fork, test it, push it, and open a draft PR.
---

# DeFiHackLabs PR

Use only after `tx2poc` generated a case and PoC. The user should provide `cases/<case>`. Read `AGENTS.md` for the local DeFiHackLabs path and PR defaults.

## Core Command

After copying the final PoC to `src/test/YYYY-MM/`, run this inside the DeFiHackLabs fork:

```bash
python add_new_entry.py
```

Use it as the source of truth for entry text and the expected Forge command, but not for year-based README routing. The helper writes root `README.md`; DeFiHackLabs also keeps year-specific archive pages under `past/YYYY/README.md`.

## PR Format

Use one branch per PR.

Title:

```text
Add <Name> PoC. <Mon D>. <Lost Amount>
```

Example:

```text
Add TokenHolder PoC. Oct 7. 20 WBNB
```

Body:

```text
source: <tweet-or-source-link>
```

## Approval Gates

Ask before:

- Writing to `DeFiHackLabs/`: show branch, PoC path, README target, PR title/body.
- Committing: show `git user.name`, `git user.email`, commit message.
- GitHub writes: show account, email, remote, branch, action.
- Changing `GITHUB_TOKEN`, `GH_TOKEN`, or active `gh` account.

No magic phrase. Read-only checks, fetches, and local tests do not need confirmation.

## Workflow

1. Inspect the case and identify the PoC.
   - Require `metadata.json`, `block.json`, `attack_analysis.md`, and a passing `poc_run.log` or equivalent.
   - If more than one `*_exp.sol` exists, ask the user which PoC to export.
   - Do not inspect a same-transaction DeFiHackLabs sample before the generated PoC exists.

2. Validate the local DeFiHackLabs fork.

   ```bash
   cd DeFiHackLabs
   git status --short
   git remote -v
   git config --get user.name
   git config --get user.email
   gh auth status
   ```

   Require a clean worktree, `origin` as the user's fork, and `upstream` as `SunWeb3Sec/DeFiHackLabs`.

3. Sync from upstream before duplicate checks.

   ```bash
   git fetch upstream
   git switch main
   git merge --ff-only upstream/main
   ```

   Push `main` only if the user wants their fork updated:

   ```bash
   git push origin main
   ```

4. Check the synced fork for the attack transaction.

   ```bash
   rg -ni "<attack_tx_hash>" . --glob '!.git/**'
   ```

   Stop if the transaction already exists.

5. Re-check PoC quality.

   Do not export unless the PoC is a passing, self-contained exploit test. Reject TODO/FIXME placeholders, compile-only tests, raw replay, trace-frame comments, an empty source/message line under `// @Analysis`, or an empty `// Twitter Guy` value.

   Follow Approval Gates before writing to `DeFiHackLabs/`.

6. Create a branch and copy only the final PoC.

   Derive `YYYY-MM` from `block.json`. Use the same timestamp in `add_new_entry.py`. Before copying, ensure the target path and PoC basename do not already exist.

   ```bash
   git switch -c tx2poc/<case-or-victim>
   mkdir -p src/test/YYYY-MM
   test ! -e src/test/YYYY-MM/<poc_name>_exp.sol
   rg -ni "<poc_name>_exp.sol" README.md src/test
   ```

   Treat any `rg` output as a collision. If clean, copy:

   ```bash
   cp ../cases/<case>/<poc_name>_exp.sol src/test/YYYY-MM/<poc_name>_exp.sol
   ```

7. Run the DeFiHackLabs helper.

   ```bash
   python add_new_entry.py
   ```

   Select the matching network. Answer `no` to manual incident entry and `yes` to process `.sol` files missing README entries. Provide the attack timestamp, lost amount, concise root cause, and source link.

   Verify the README Forge command matches the case chain. Add required network flags, especially `--evm-version shanghai` for Base, optimism, or bsc when expected.

   Then route the generated README entry to the year archive expected by DeFiHackLabs:

   - Keep or add the root `README.md` table-of-contents link for the incident.
   - For incidents whose year has `past/YYYY/README.md`, move the full incident entry from root `README.md` into `past/YYYY/README.md`.
   - In root `README.md`, the incident link should point to `past/YYYY/README.md#<anchor>` instead of a same-file anchor.
   - In `past/YYYY/README.md`, contract links must be relative to that file, e.g. `../../src/test/YYYY-MM/<poc_name>_exp.sol`.
   - If `past/YYYY/README.md` does not exist, keep the full entry in root `README.md` unless the user explicitly wants a new archive file.
   - Keep incident counters consistent in every README file edited.

   Do not assume `add_new_entry.py` handles this routing; it defaults to root `README.md`.

8. Test, commit, push, and open a draft PR.

   Use the PR title as the commit message. Derive `<owner>` from `origin`, not `upstream`.
   Follow Approval Gates before committing, pushing, or creating the PR.

   Test with the README Forge command before staging. For named forks, temporarily copy only the matching RPC URL from this repo's `foundry.toml` to the same alias in `DeFiHackLabs/foundry.toml`; restore it after the test and confirm `git diff -- foundry.toml` is empty. Do not use `--config-path ../foundry.toml` or use this to hide compile, revert, or invariant failures.

   ```bash
   forge test --contracts ./src/test/YYYY-MM/<poc_name>_exp.sol -vvv
   git add src/test/YYYY-MM/<poc_name>_exp.sol README.md past/YYYY/README.md
   git commit -m "Add <Name> PoC. <Mon D>. <Lost Amount>"
   git push origin tx2poc/<case-or-victim>
   git remote get-url origin
   gh pr create --repo SunWeb3Sec/DeFiHackLabs --base main --head <owner>:tx2poc/<case-or-victim> --title "Add <Name> PoC. <Mon D>. <Lost Amount>" --body "source: <tweet-or-source-link>" --draft
   ```

   Prefer the verified README Forge command if it differs.

   Auth fallback: if `gh auth status` fails but `git push origin <branch>` succeeds, Git and `gh` are using different credentials. After GitHub write approval, prefer `gh pr create`, then the GitHub connector. If both fail, use the Git HTTPS credential helper only in memory for the single PR API request; never print, save, or commit the credential from `git credential fill`.

## Guardrails

- Treat `DeFiHackLabs/` as a gitignored local clone of the user's fork, not as a tx2poc submodule.
- Require the DeFiHackLabs repo to be clean before applying changes.
- Require `origin` to be the user's fork and `upstream` to point to `SunWeb3Sec/DeFiHackLabs`.
- Sync from `upstream` with fast-forward only before duplicate checks or branch creation.
- Use a separate branch for each DeFiHackLabs PR.
- After syncing latest upstream, stop if the attack transaction hash already appears in DeFiHackLabs.
- Follow Approval Gates.
- Use the attack timestamp from `block.json` for both the `src/test/YYYY-MM/` folder and the timestamp entered into `add_new_entry.py`.
- Use the attack year from `block.json` to decide whether the full README incident entry belongs in `past/YYYY/README.md`. `add_new_entry.py` does not do this automatically.
- Do not overwrite existing DeFiHackLabs PoCs or reuse an existing PoC basename.
- Do not export PoCs with TODO/FIXME placeholders, compile-only tests, raw replay, trace-frame comments, an empty source/message line under `// @Analysis`, or an empty `// Twitter Guy` header value.
- Copy only the final Solidity PoC into DeFiHackLabs. Do not copy tx2poc trace JSON, benchmark output, notes, or reviews.
- Create draft PRs by default.
