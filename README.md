# repos-update

A command-line tool to recursively scan directories and update all git repositories. Runs `git pull --all` and `git remote prune origin` on each repo, with colored output showing update status, commit counts, and file changes.

## Installation

```bash
# Install globally as CLI tool
uv tool install .

# Upgrade after making changes
uv tool upgrade repos-update

# Or force reinstall (alternative to upgrade)
uv tool install . --force
```

## Usage

```bash
repos-update ~/Code                    # Update all repos (default command)
repos-update ~/Code ~/Projects         # Update repos in multiple directories
repos-update ~/Code -j 8               # Update 8 repos in parallel
repos-update ~/Code --dry-run          # Preview what would be updated
repos-update dirty ~/Code              # List repos with uncommitted changes
repos-update status ~/Code             # Show branch, ahead/behind, dirty state
repos-update age ~/Code                # Show last commit age (color-coded)
repos-update remote ~/Code             # List repos by remote configuration (both buckets)
repos-update remote ~/Code --without-remote   # Only repos without a remote
repos-update remote ~/Code --raw       # Print only origin URLs, sorted (pipe-friendly)
```

## Commands

| Command | Description |
|---------|-------------|
| `update` | Update repositories (default) |
| `dirty` | List repos with uncommitted changes |
| `status` | Show branch, ahead/behind, dirty state |
| `age` | Show last commit age (green: ≤1mo, yellow: ≤3mo, orange: ≤6mo, red: ≤1yr, magenta: >1yr) |
| `remote` | List repos by remote configuration; `--with-remote` / `--without-remote` filter to one bucket; `--raw` prints sorted origin URLs only |

## Options

| Option | Description |
|--------|-------------|
| `-j N`, `--jobs N` | Process N repos in parallel (default: 1) |
| `-t N`, `--tree N` | Limit search depth to N levels (1 = immediate subdirs only) |
| `--dry-run` | Show what would be updated without pulling (update only) |
| `-q`, `--quiet` | Quiet mode - suppress per-repo output, show summary only |
| `--full-path` | Show full absolute paths instead of relative |

## Summary Output

Every command prints a sorted summary block at the end:

- `update` — grouped by updated / up-to-date / no-remote / dirty / errors, names sorted alphabetically within each group
- `status` — live output streams unsorted (for progress feedback during `git fetch`); summary groups repos by state (clean / ahead / behind / diverged / dirty / no-remote), sorted alphabetically within each group
- `dirty` — live output sorted alphabetically; summary restates counts and names
- `remote` — live output groups with-remote (with URLs) above no-remote, each sorted alphabetically; summary shows counts per bucket
- `age` — live output sorted most recent to oldest; summary shows counts per category (recent / aging / stale / old)

### Age Command Filters

Results are always sorted from most recent to oldest, regardless of filters.

Filter repos by age category (can be combined):

| Option | Category | Threshold |
|--------|----------|-----------|
| `--recent` | Green | ≤30 days |
| `--aging` | Yellow | 31-90 days |
| `--stale` | Orange | 91-180 days |
| `--old` | Red | 181-365 days |
| `--ancient` | Magenta | >365 days |

```bash
repos-update age ~/Code --stale --old    # Show only stale and old repos
repos-update age ~/Code --recent         # Show only recently updated repos
```

### Remote Command Filters

With no flags, both buckets are shown. Flags can be combined; combining both is equivalent to passing neither.

| Option | Bucket |
|--------|--------|
| `--with-remote` | Repos that have at least one remote configured |
| `--without-remote` | Repos with no remotes configured |
| `--raw` | Print only `origin` URLs, sorted alphabetically, one per line. Suppresses headers, colors, and summary. Repos without an `origin` remote are skipped. Cannot be combined with `--without-remote`. |

```bash
repos-update remote ~/Code --with-remote      # Only repos with remotes
repos-update remote ~/Code --without-remote   # Only repos without remotes
repos-update remote ~/Code --raw              # Pure origin URLs, one per line
repos-update remote ~/Code --raw | sort -u    # Dedupe origin URLs across repos
```

## Output Example

```
✓ Code/project1 (1 commit, 2 files ▲10 ▼3)
✓ Code/project2 (3 commits, 5 files ▲120 ▼45)
· Code/project3
```

## Requirements

- Python 3.12+
- Git
