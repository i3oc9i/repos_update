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
repos-update remote ~/Code             # List repos with remotes configured
repos-update no-remote ~/Code          # List repos without any remote
```

## Commands

| Command | Description |
|---------|-------------|
| `update` | Update repositories (default) |
| `dirty` | List repos with uncommitted changes |
| `status` | Show branch, ahead/behind, dirty state |
| `age` | Show last commit age (green: <1mo, yellow: <3mo, red: <6mo, orange: >6mo) |
| `remote` | List repos with a remote configured |
| `no-remote` | List repos without any remote |

## Options

| Option | Description |
|--------|-------------|
| `-j N`, `--jobs N` | Process N repos in parallel (default: 1) |
| `-t N`, `--tree N` | Limit search depth to N levels (1 = immediate subdirs only) |
| `--dry-run` | Show what would be updated without pulling (update only) |
| `-q`, `--quiet` | Quiet mode - only show summary |
| `--full-path` | Show full absolute paths instead of relative |

### Age Command Filters

Filter repos by age category (can be combined):

| Option | Category | Threshold |
|--------|----------|-----------|
| `--recent` | Green | ≤30 days |
| `--aging` | Yellow | 31-90 days |
| `--stale` | Red | 91-180 days |
| `--old` | Orange | >180 days |

```bash
repos-update age ~/Code --stale --old    # Show only stale and old repos
repos-update age ~/Code --recent         # Show only recently updated repos
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
