# Merge `remote` and `no-remote` into a single command

**Date:** 2026-04-19
**Status:** Approved (design)

## Problem

Today there are two parallel commands:

- `repos-update remote ~/Code` — lists repos that have a remote configured (shows URLs)
- `repos-update no-remote ~/Code` — lists repos that do not

They answer the same question ("which of my repos have remotes?") from opposite directions, and neither shows the full picture in one pass. The summary is also asymmetric: `remote` mentions the no-remote count but never names them; `no-remote` doesn't surface the with-remote count.

This is the same shape `status` and `age` already solved with bucketed summaries.

## Goal

Replace the two commands with a single `remote` command that:

- Reports on **both** with-remote and no-remote repos by default
- Lets the user narrow to one bucket via flags (matching the `age` filter pattern)
- Has a bucketed summary block (matching `status` and `age`)

## Design

### Command surface

```
repos-update remote ~/Code                       # both buckets
repos-update remote ~/Code --with-remote         # only repos with a remote
repos-update remote ~/Code --without-remote      # only repos without a remote
repos-update remote ~/Code --with-remote --without-remote   # equivalent to no flags
```

The `no-remote` subcommand is removed. There is no deprecation period — this is a single-user CLI tool, no external consumers.

### Live output

Two grouped sections, with-remote first, no-remote second. Within each section, repos are sorted alphabetically by directory name (case-insensitive), matching the existing convention.

With-remote rows keep the current format (path on one line, remote URLs indented below in gray). No-remote rows are a single line with the gray `○` marker and path.

```
● Code/project-a
  origin: git@github.com:user/project-a.git
● Code/project-b
  origin: git@github.com:user/project-b.git

○ Code/local-experiment
○ Code/scratch
```

The blank line between sections is intentional — it makes the bucket boundary visible without needing a header.

### Summary

Counts only — no repo lists. Mirrors the `age` summary structure (the per-repo information is already in the live output above; the summary's job is the at-a-glance count). Shows whichever buckets are non-empty:

```
══════════════════════════════════════════════════
Summary:
──────────────────────────────────────────────────
● With remote: 12
○ No remote: 3
──────────────────────────────────────────────────
Total: 15 repositories
```

When a filter flag is active, the filtered-out bucket is not printed in the summary, and `Total:` reflects only the included repos (consistent with how `age` filtering currently behaves).

### Quiet mode (`-q`)

Same as today: suppress per-repo live output, still print the summary.

### Parallelism

Reuse the existing `_get_repo_remotes` worker via `ThreadPoolExecutor` when `--jobs > 1`. No change to that helper.

## Implementation notes

- `print_remote_summary` is rewritten to accept the full bucketed result (both with-remote items and no-remote paths) and the active filter set, so it can omit the unselected bucket.
- `print_no_remote_summary` is deleted.
- The standalone `no-remote` subparser block in `main()` is deleted.
- The `no-remote` branch in `_run_command` is deleted; its logic folds into the `remote` branch.
- `COMMANDS` set drops `"no-remote"`.
- The `remote` subparser gains two boolean flags: `--with-remote` and `--without-remote`.
- README and CLAUDE.md are updated: drop the `no-remote` row from the commands table, update the `remote` row's description, add a "Remote Command Filters" subsection mirroring the existing "Age Command Filters" subsection, and remove `no-remote` from the Summary Output bullet.

## Out of scope

- No change to `status`'s no-remote bucket — that already exists and is correct.
- No new filter on remote name (e.g., "only repos pointing at github.com"). Possible future work, not part of this change.
- No version bump beyond what the next release would do anyway.
