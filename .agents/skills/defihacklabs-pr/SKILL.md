---
name: defihacklabs-pr
description: Export a completed tx2poc case into a local DeFiHackLabs fork, test it, push it, and open a draft PR.
---

# DeFiHackLabs PR

Use only after `tx2poc` generated a case and PoC. The user should provide `cases/<case>`. Read `AGENTS.md` for the local DeFiHackLabs path and PR defaults.

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

## Approval Gate

Use one bundled approval after the precheck phase. Ask before creating the export branch, copying the PoC, editing README files, committing, pushing, or opening the PR.

Before asking, show:

- source fork repo/owner, derived from `origin`
- target repo: `SunWeb3Sec/DeFiHackLabs`
- base branch: `main`
- fork repo branch name
- PoC copy path
- README target(s)
- PR/commit title
- PR body
- `git user.name`
- `git user.email`
- push remote/owner
- GitHub account/auth state
- action scope: write/copy, README update, test, commit, push, draft PR

If approved, continue through copy, README update, test, commit, push, and draft PR without more prompts while those details remain unchanged.

Ask again only for material changes or exceptions:

- dirty DeFiHackLabs worktree
- duplicate tx, target path collision, or PoC basename collision
- unexpected diff, README routing, branch, remote, account, PR title/body, or non-draft PR state
- failing or inconclusive Forge test
- need to push/update fork `main`
- different GitHub credential/account than approved
- changes to `GITHUB_TOKEN`, `GH_TOKEN`, active `gh` account, or stored credentials

No magic phrase. Case inspection, local fork validation, upstream fetch/sync, duplicate searches, and local tests do not need confirmation. Never push fork `main` without explicit user approval. If approval is narrower than the bundle, ask before exceeding it.

## Workflow

### Precheck

Run this phase without user confirmation. Stop before approval if any required input is missing, the fork is dirty or misconfigured, upstream sync fails, the tx already exists, or a path collides.

1. Inspect `cases/<case>`.
   - Require `metadata.json`, `block.json`, `attack_analysis.md`, and a passing `poc_run.log` or equivalent.
   - If more than one `*_exp.sol` exists, ask which PoC to export.
   - Do not inspect a same-transaction DeFiHackLabs sample before the generated PoC exists.

2. Validate `DeFiHackLabs/`.

   ```bash
   cd DeFiHackLabs
   git status --short
   git remote -v
   git config --get user.name
   git config --get user.email
   gh auth status
   ```

   Require a clean worktree, `origin` as the user's fork, and `upstream` as `SunWeb3Sec/DeFiHackLabs`.

3. Sync before duplicate checks.

   ```bash
   git fetch upstream
   git switch main
   git merge --ff-only upstream/main
   ```

4. Check the synced fork for the attack tx.

   ```bash
   rg -ni "<attack_tx_hash>" . --glob '!.git/**'
   ```

   Stop if the transaction already exists.

5. Check destination collisions.

   Derive `YYYY-MM` from `block.json`; use the same timestamp in `add_new_entry.py`. Before approval, ensure the target path and PoC basename do not already exist.

   ```bash
   test ! -e src/test/YYYY-MM/<poc_name>_exp.sol
   rg -ni "<poc_name>_exp.sol" README.md src/test
   ```

   Treat any `rg` output as a collision.

### Approval

Follow Approval Gate now, before writing PR changes to `DeFiHackLabs/`. Prefer one approval that covers copy, README update, test, commit, push, and draft PR creation.

### Execute

1. Create the branch and copy only the final PoC.

   ```bash
   git switch -c tx2poc/<case-or-victim>
   mkdir -p src/test/YYYY-MM
   cp ../cases/<case>/<poc_name>_exp.sol src/test/YYYY-MM/<poc_name>_exp.sol
   ```

2. Run the DeFiHackLabs helper.

   ```bash
   python add_new_entry.py
   ```

   Select the matching network. Answer `no` to manual incident entry and `yes` to process `.sol` files missing README entries. Provide the attack timestamp, lost amount, concise root cause, and source link. Use the helper as the source of truth for entry text and expected Forge command, but not for year-based README routing.

3. Route README entries.

   `add_new_entry.py` writes root `README.md`. DeFiHackLabs also keeps year archives under `past/YYYY/README.md`.

   - Keep or add the root `README.md` table-of-contents link for the incident.
   - For incidents whose year has `past/YYYY/README.md`, move the full incident entry from root `README.md` into `past/YYYY/README.md`.
   - In root `README.md`, the incident link should point to `past/YYYY/README.md#<anchor>` instead of a same-file anchor.
   - In `past/YYYY/README.md`, contract links must be relative to that file, e.g. `../../src/test/YYYY-MM/<poc_name>_exp.sol`.
   - If `past/YYYY/README.md` does not exist, keep the full entry in root `README.md` unless the user explicitly wants a new archive file.
   - Keep incident counters consistent in every README file edited.

4. Verify and test.

   Verify the README Forge command matches the case chain. Add required network flags, especially `--evm-version shanghai` for Base, optimism, or bsc when expected. Test with the README Forge command before staging.

   For named forks, temporarily copy only the matching RPC URL from this repo's `foundry.toml` to the same alias in `DeFiHackLabs/foundry.toml`; restore it after the test and confirm `git diff -- foundry.toml` is empty. Do not use `--config-path ../foundry.toml` or use this to hide compile, revert, or invariant failures.

   ```bash
   forge test --contracts ./src/test/YYYY-MM/<poc_name>_exp.sol -vvv
   ```

5. Commit, push, and open a draft PR.

   Use the PR title as the commit message. Derive `<owner>` from `origin`, not `upstream`. Stage only README files actually edited; also run `git add past/YYYY/README.md` if the year archive changed.

   ```bash
   git add src/test/YYYY-MM/<poc_name>_exp.sol README.md
   git commit -m "Add <Name> PoC. <Mon D>. <Lost Amount>"
   git push origin tx2poc/<case-or-victim>
   git remote get-url origin
   gh pr create --repo SunWeb3Sec/DeFiHackLabs --base main --head <owner>:tx2poc/<case-or-victim> --title "Add <Name> PoC. <Mon D>. <Lost Amount>" --body "source: <tweet-or-source-link>" --draft
   ```

   Prefer the verified README Forge command if it differs.

   Auth fallback: if `gh auth status` fails but `git push origin <branch>` succeeds, Git and `gh` are using different credentials. If GitHub writes are approved, prefer `gh pr create`, then the GitHub connector. If both fail, use the Git HTTPS credential helper only in memory for the single PR API request; never print, save, or commit the credential from `git credential fill`. Ask again before changing auth state or switching to a different credential/account than the approved one.

## Hard Rules

- Treat `DeFiHackLabs/` as a gitignored local clone of the user's fork, not as a tx2poc submodule.
- Use a separate branch for each DeFiHackLabs PR.
- Do not overwrite existing DeFiHackLabs PoCs or reuse an existing PoC basename.
- Copy only the final Solidity PoC into DeFiHackLabs. Do not copy tx2poc trace JSON, benchmark output, notes, or reviews.
- Create draft PRs by default.
