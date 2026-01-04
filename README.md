# repos-update

A command-line tool to recursively scan directories and update all git repositories. Runs `git pull --all` and `git remote prune origin` on each repo, with colored output showing update status, commit counts, and file changes.

## Installation

```bash
uv pip install -e .
```

## Usage

```bash
repos-update ~/Code                    # Update all repos (default command)
repos-update ~/Code ~/Projects         # Update repos in multiple directories
repos-update ~/Code -j 8               # Update 8 repos in parallel
repos-update ~/Code --dry-run          # Preview what would be updated
repos-update dirty ~/Code              # List repos with uncommitted changes
repos-update status ~/Code             # Show branch, ahead/behind, dirty state
repos-update remote ~/Code             # List repos with remotes configured
repos-update no-remote ~/Code          # List repos without any remote
```

## Commands

| Command | Description |
|---------|-------------|
| `update` | Update repositories (default) |
| `dirty` | List repos with uncommitted changes |
| `status` | Show branch, ahead/behind, dirty state |
| `remote` | List repos with a remote configured |
| `no-remote` | List repos without any remote |

## Options

| Option | Description |
|--------|-------------|
| `-j N`, `--jobs N` | Process N repos in parallel (default: 1) |
| `--dry-run` | Show what would be updated without pulling (update only) |
| `-q`, `--quiet` | Quiet mode - only show summary |
| `--full-path` | Show full absolute paths instead of relative |

## Output Example

```
✓ Code/project1 (1 commit, 2 files ▲10 ▼3)
✓ Code/project2 (3 commits, 5 files ▲120 ▼45)
· Code/project3
```

## Requirements

- Python 3.12+
- Git
