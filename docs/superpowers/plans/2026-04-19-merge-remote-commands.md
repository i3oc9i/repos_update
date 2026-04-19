# Merge `remote` and `no-remote` Commands — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Merge `no-remote` into `remote` so a single command reports both buckets, with `--with-remote`/`--without-remote` filter flags and a counts-only bucketed summary.

**Architecture:** Single-file Python module (`repos_update.py`). Refactor `_get_repo_remotes` to always return `(repo, remotes)` (empty dict means no remote). Replace `list_remotes` with a function that produces two buckets and prints live output as two grouped sections (with-remote first, blank line, no-remote second). Rewrite `print_remote_summary` to take both buckets plus the active filter set and emit only bucket counts (no per-repo lists). Delete `print_no_remote_summary`, the `no-remote` subparser, and its `_run_command` branch.

**Tech Stack:** Python 3.12+, stdlib only (`argparse`, `subprocess`, `concurrent.futures`).

**Testing approach:** This project has no test framework wired up. Verification is by running the CLI against the user's `~/Code` directory and inspecting output. Each task that changes behavior includes a manual verification step with the exact command to run and the expected output shape.

**Spec:** `docs/superpowers/specs/2026-04-19-merge-remote-commands-design.md`

---

## File Structure

All code changes are in one file: `repos_update.py`. Docs:

- **Modify:** `repos_update.py` — refactor remote functions, rewrite summary, update CLI parser and dispatch
- **Modify:** `README.md` — drop `no-remote` row, update `remote` row, add "Remote Command Filters" subsection, update "Summary Output" bullet
- **Modify:** `CLAUDE.md` — drop `no-remote` line from Usage section

The project's CLAUDE.md mandates: "Always update the README.md, and the CLAUDE.md (if applicable) before of making a commit." Therefore docs are bundled into the same commit as the code change (Task 6).

---

## Task 1: Refactor `_get_repo_remotes` to always return a tuple

**Files:**
- Modify: `repos_update.py:142-151`

Currently `_get_repo_remotes` returns `None` for repos without remotes. The merged command needs both buckets, so the helper must always return `(repo, remotes_dict)` where `remotes_dict` is empty for no-remote repos. Callers decide how to bucket.

- [ ] **Step 1: Replace the function**

Replace lines 142-151 of `repos_update.py`:

```python
def _get_repo_remotes(repo: Path) -> tuple[Path, dict]:
    """Get remotes for a single repo. Returns (repo, {}) if none configured."""
    result = run_git(repo, "remote", "-v")
    remotes: dict[str, str] = {}
    for line in result.stdout.strip().split("\n"):
        if line and "(fetch)" in line:
            parts = line.split()
            if len(parts) >= 2:
                remotes[parts[0]] = parts[1]
    return (repo, remotes)
```

The return type is now unconditional — the `Optional[...]` is gone, and the import of `Optional` may still be needed elsewhere (it is used later in the file by `update_repo` and `_check_dirty`), so do not remove the import.

- [ ] **Step 2: Verify no other callers depend on the `None` return**

Run: `grep -n "_get_repo_remotes" repos_update.py`
Expected: only one call site, inside `list_remotes`.

(Use the Grep tool, not bash grep.)

---

## Task 2: Replace `list_remotes` with a two-bucket function

**Files:**
- Modify: `repos_update.py:154-171`

Replace `list_remotes` with `collect_remote_buckets`, which:

1. Collects remote info for every repo (parallel-aware).
2. Splits into `with_remote` (sorted) and `without_remote` (sorted).
3. Prints live output in two grouped sections (with-remote first, blank line separator, then no-remote) — but only sections selected by the filter set; sections that the caller filtered out are not printed live either.
4. Returns both buckets so the summary printer can use them.

- [ ] **Step 1: Replace `list_remotes` with `collect_remote_buckets`**

Replace lines 154-171 with:

```python
def collect_remote_buckets(
    repos: List[Path],
    jobs: int = 1,
    show_with: bool = True,
    show_without: bool = True,
    quiet: bool = False,
) -> tuple[list[tuple[Path, dict]], list[Path]]:
    """Collect repos into with-remote and without-remote buckets.

    Live output prints whichever sections are selected by `show_with` /
    `show_without`, with the with-remote section first and a blank line
    separating the two when both are non-empty and both selected.
    """
    if jobs > 1:
        with ThreadPoolExecutor(max_workers=jobs) as executor:
            results = list(executor.map(_get_repo_remotes, repos))
    else:
        results = [_get_repo_remotes(repo) for repo in repos]

    with_remote: list[tuple[Path, dict]] = [
        (repo, remotes) for repo, remotes in results if remotes
    ]
    without_remote: list[Path] = [
        repo for repo, remotes in results if not remotes
    ]
    with_remote.sort(key=lambda item: item[0].name.lower())
    without_remote.sort(key=lambda r: r.name.lower())

    if not quiet:
        printed_with = False
        if show_with:
            for repo, remotes in with_remote:
                path_str = format_path(repo)
                remote_str = ", ".join(f"{k}: {v}" for k, v in remotes.items())
                print(f"{Color.GREEN}●{Color.RESET} {path_str}")
                print(f"  {Color.GRAY}{remote_str}{Color.RESET}")
            printed_with = bool(with_remote)
        if show_without and without_remote:
            if printed_with:
                print()
            for repo in without_remote:
                print(f"{Color.GRAY}○{Color.RESET} {format_path(repo)}")

    return with_remote, without_remote
```

The blank line is only printed when both sections actually have content and both are selected — avoids a leading or trailing blank line in single-bucket output.

---

## Task 3: Rewrite `print_remote_summary` to be counts-only

**Files:**
- Modify: `repos_update.py:174-185`

Drop the per-repo lists; show only bucket counts, mirroring `age`'s summary. Total reflects only the buckets included after filtering.

- [ ] **Step 1: Replace `print_remote_summary`**

Replace lines 174-185 with:

```python
def print_remote_summary(
    with_remote: list[tuple[Path, dict]],
    without_remote: list[Path],
    show_with: bool,
    show_without: bool,
) -> None:
    """Print counts-only summary for the remote command.

    Only buckets selected by the filter flags are shown; `Total:` reflects
    the included buckets so it stays consistent with the live output.
    """
    _summary_start()
    total = 0
    if show_with and with_remote:
        print(f"{Color.GREEN}● With remote:{Color.RESET} {len(with_remote)}")
        total += len(with_remote)
    if show_without and without_remote:
        print(f"{Color.GRAY}○ No remote:{Color.RESET} {len(without_remote)}")
        total += len(without_remote)
    _summary_end(total)
```

---

## Task 4: Delete `print_no_remote_summary`

**Files:**
- Modify: `repos_update.py:637-646`

The function is no longer needed; its responsibilities are folded into `print_remote_summary`.

- [ ] **Step 1: Delete the function**

Delete lines 637-646 (the entire `print_no_remote_summary` function and the blank line that followed it). Use the Edit tool with the exact block.

The block to delete:

```python
def print_no_remote_summary(no_remote_repos: List[Path], total: int) -> None:
    """Print summary for the no-remote command."""
    _summary_start()
    if no_remote_repos:
        print(f"{Color.GRAY}○ No remote:{Color.RESET} {len(no_remote_repos)}")
        for repo in no_remote_repos:
            print(f"  {format_path(repo)}")
    else:
        print(f"{Color.GREEN}✓ All repositories have remotes configured.{Color.RESET}")
    _summary_end(total)
```

- [ ] **Step 2: Confirm no other references remain**

Use the Grep tool to search `repos_update.py` for `print_no_remote_summary`. Expected: zero matches.

---

## Task 5: Update `_run_command` and CLI parser

**Files:**
- Modify: `repos_update.py:739` (COMMANDS set)
- Modify: `repos_update.py:771-789` (the `remote` and `no-remote` branches)
- Modify: `repos_update.py:927-938` (the `remote` and `no-remote` subparsers)

Three sub-changes: (a) remove `"no-remote"` from `COMMANDS`, (b) replace the two dispatch branches with a single `remote` branch that reads the new flags, (c) replace the two subparsers with a single `remote` subparser carrying `--with-remote` and `--without-remote`.

- [ ] **Step 1: Remove `"no-remote"` from the `COMMANDS` set**

Edit line 739:

```python
COMMANDS = {"update", "dirty", "status", "remote", "age"}
```

- [ ] **Step 2: Replace dispatch branches**

Replace lines 771-789 (the two blocks `if command == "remote":` and `if command == "no-remote":`) with a single block:

```python
    if command == "remote":
        show_with = getattr(args, "with_remote", False)
        show_without = getattr(args, "without_remote", False)
        # No flag set => show both buckets
        if not show_with and not show_without:
            show_with = show_without = True
        with_remote, without_remote = collect_remote_buckets(
            repos,
            jobs=jobs,
            show_with=show_with,
            show_without=show_without,
            quiet=quiet,
        )
        print_remote_summary(with_remote, without_remote, show_with, show_without)
        return 0
```

- [ ] **Step 3: Replace the two subparsers with one**

Replace lines 927-938 (the `remote` and `no-remote` `subparsers.add_parser` blocks) with:

```python
    # remote command
    remote_parser = subparsers.add_parser(
        "remote",
        parents=[shared],
        help="List repos by remote configuration (with/without remotes)",
    )
    remote_parser.add_argument(
        "--with-remote",
        action="store_true",
        help="Show only repos that have a remote configured",
    )
    remote_parser.add_argument(
        "--without-remote",
        action="store_true",
        help="Show only repos without any remote configured",
    )
```

argparse converts `--with-remote` to `args.with_remote` and `--without-remote` to `args.without_remote`, which is what the dispatch branch reads.

- [ ] **Step 4: Confirm no `no-remote` references remain in the source**

Use the Grep tool: pattern `no-remote`, path `repos_update.py`.
Expected: zero matches in code (the string is fully removed from CLI and dispatch).

Note: matches inside docs files are fine — those are updated in Task 7 / Task 8.

---

## Task 6: Manual verification against `~/Code`

**Files:** none modified

Run the CLI in install-from-source mode and confirm the four behaviors.

- [ ] **Step 1: Reinstall the tool**

Run: `uv tool install . --force`
Expected: install succeeds with no errors.

- [ ] **Step 2: Both buckets (no flags)**

Run: `repos-update remote ~/Code -j 8 -t 2`
Expected:
- A run of `●` lines (each followed by an indented gray remote URL line) for repos with remotes, sorted alphabetically
- One blank line
- A run of `○` lines for repos without remotes, sorted alphabetically
- Summary block showing `● With remote: <N>` and `○ No remote: <M>` (only non-empty buckets) with `Total: N+M repositories`

- [ ] **Step 3: With-remote only**

Run: `repos-update remote ~/Code --with-remote -j 8 -t 2`
Expected: only `●` lines (no `○` lines, no separating blank line). Summary shows only `● With remote:` and `Total:` equals that count.

- [ ] **Step 4: Without-remote only**

Run: `repos-update remote ~/Code --without-remote -j 8 -t 2`
Expected: only `○` lines. Summary shows only `○ No remote:` and `Total:` equals that count.

- [ ] **Step 5: Both flags equals no flags**

Run: `repos-update remote ~/Code --with-remote --without-remote -j 8 -t 2`
Expected: identical output to Step 2.

- [ ] **Step 6: Old `no-remote` command is rejected**

Run: `repos-update no-remote ~/Code`
Expected: exits non-zero with the existing `Error: Unknown command: no-remote` message and the help text printed above it (this is the existing unknown-command path in `main()`).

- [ ] **Step 7: Quiet mode still prints the summary**

Run: `repos-update remote ~/Code -q -j 8 -t 2`
Expected: no per-repo lines, but the summary block still prints.

If any step fails, fix the code before continuing.

---

## Task 7: Update README.md

**Files:**
- Modify: `README.md:29` (Usage block)
- Modify: `README.md:40-41` (Commands table)
- Modify: `README.md:59` (Summary Output bullet)
- Modify: `README.md:79` (after Age Command Filters block)

- [ ] **Step 1: Update the Usage code block**

In the fenced bash block (lines 20-30), delete the `no-remote` line and update the `remote` line:

Replace:

```
repos-update remote ~/Code             # List repos with remotes configured
repos-update no-remote ~/Code          # List repos without any remote
```

With:

```
repos-update remote ~/Code             # List repos by remote configuration (both buckets)
repos-update remote ~/Code --without-remote   # Only repos without a remote
```

- [ ] **Step 2: Update the Commands table**

Replace the two table rows:

```
| `remote` | List repos with a remote configured |
| `no-remote` | List repos without any remote |
```

With one row:

```
| `remote` | List repos by remote configuration; `--with-remote` / `--without-remote` filter to one bucket |
```

- [ ] **Step 3: Update the Summary Output bullet for `dirty`/`remote`/`no-remote`**

Replace:

```
- `dirty`, `remote`, `no-remote` — live output sorted alphabetically; summary restates counts and names
```

With two bullets (split because `remote` now matches the `age` shape, not `dirty`):

```
- `dirty` — live output sorted alphabetically; summary restates counts and names
- `remote` — live output groups with-remote (with URLs) above no-remote, each sorted alphabetically; summary shows counts per bucket
```

- [ ] **Step 4: Add a "Remote Command Filters" subsection**

After the Age Command Filters block (after line 79, just before the `## Output Example` heading), insert:

```markdown
### Remote Command Filters

With no flags, both buckets are shown. Flags can be combined; combining both is equivalent to passing neither.

| Option | Bucket |
|--------|--------|
| `--with-remote` | Repos that have at least one remote configured |
| `--without-remote` | Repos with no remotes configured |

```bash
repos-update remote ~/Code --with-remote      # Only repos with remotes
repos-update remote ~/Code --without-remote   # Only repos without remotes
```

```

(Yes, the closing triple backticks of the bash example are followed by a blank line before the next `##` heading — match the spacing convention used by the Age Command Filters block above.)

---

## Task 8: Update CLAUDE.md

**Files:**
- Modify: `CLAUDE.md:25-31` (Commands block in Usage section)

- [ ] **Step 1: Update the commands listing**

Replace:

```bash
uv run repos-update remote ~/Code           # List repos that have a remote
uv run repos-update no-remote ~/Code        # List repos without a remote
```

With:

```bash
uv run repos-update remote ~/Code           # List repos by remote configuration (both buckets)
uv run repos-update remote ~/Code --with-remote --without-remote # Filter to one bucket
```

- [ ] **Step 2: Remove `list_remotes` from the Key Functions list**

In the "Key Functions" section, replace:

```
- `list_remotes()` - List repos that have remotes configured
```

With:

```
- `collect_remote_buckets()` - Bucket repos into with-remote and without-remote, with optional filtering
```

---

## Task 9: Final commit

**Files:** all of the above

Per project convention (CLAUDE.md), code and docs ship in the same commit so the docs never describe a version of the code that doesn't exist on disk.

- [ ] **Step 1: Review the diff**

Run: `git status` and `git diff`
Expected: changes in `repos_update.py`, `README.md`, `CLAUDE.md`. No other files touched.

- [ ] **Step 2: Stage and commit**

Run:

```bash
git add repos_update.py README.md CLAUDE.md
git commit -m "$(cat <<'EOF'
Merge no-remote command into remote with bucket summary

Replace the separate no-remote command with --with-remote /
--without-remote filter flags on the remote command. Live output
groups with-remote (with URLs) above no-remote; summary shows
counts per bucket, mirroring the age command.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

Expected: commit succeeds.

- [ ] **Step 3: Verify the working tree is clean**

Run: `git status`
Expected: `nothing to commit, working tree clean`.
