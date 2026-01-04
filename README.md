# repos-update

A Python CLI tool to recursively scan directories and update all git repositories.

## Features

- Recursively finds all git repositories in specified directories
- Runs `git pull --all` to fetch all branches
- Runs `git remote prune origin` to remove stale remote branches
- Colored terminal output (green=updated, gray=unchanged, red=error)
- Change summary with commit count, files changed, and lines added/removed
- Parallel updates with `-j N`
- Dry-run mode to preview changes
- Check for dirty (uncommitted) repositories

## Output Example

```
✓ Code/project1 (1 commit, 2 files ▲10 ▼3)
✓ Code/project2 (3 commits, 5 files ▲120 ▼45)
· Code/project3
```

## Installation

### Prerequisites

- [uv](https://docs.astral.sh/uv/) - Fast Python package manager

### Install uv (if not already installed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### Clone and install

```bash
git clone https://github.com/i3oc9i/repos_update.git
cd repos_update

# Initialize the project and install dependencies
uv sync

# Install with dev dependencies (includes poethepoet)
uv sync --extra dev
```

## Usage

```bash
# Show usage/help
uv run repos-update --help

# Update all repos in a directory (default command)
uv run repos-update ~/Code

# Update repos in multiple directories
uv run repos-update ~/Code ~/Projects

# Update 8 repos in parallel (faster)
uv run repos-update update ~/Code -j 8

# Preview what would be updated (no changes made)
uv run repos-update update ~/Code --dry-run

# List repos with uncommitted changes
uv run repos-update dirty ~/Code

# Show status: branch, ahead/behind, dirty state
uv run repos-update status ~/Code

# List repos that have a remote configured
uv run repos-update remote ~/Code

# List repos without any remote
uv run repos-update no-remote ~/Code
```

## Commands

| Command | Description |
|---------|-------------|
| `update` | Update repositories (default command) |
| `dirty` | List repos with uncommitted changes |
| `status` | Show status: branch, ahead/behind, dirty state |
| `remote` | List repos that have a remote configured |
| `no-remote` | List repos without any remote configured |

## Options

| Option | Applies to | Description |
|--------|------------|-------------|
| `-j N`, `--jobs N` | all | Process N repos in parallel (default: 1) |
| `--dry-run` | update | Show what would be updated without pulling |
| `-q`, `--quiet` | all | Quiet mode - only show summary |
| `--full-path` | all | Show full absolute paths instead of relative |
| `--version` | - | Show version number |

## Development Tasks

With dev dependencies installed, you can use poe tasks:

```bash
# Clean build artifacts
uv run poe clean

# Build distribution packages
uv run poe build
```

## Building for Distribution

```bash
uv build
```

This creates distributable packages in the `dist/` directory.
