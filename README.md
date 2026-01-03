# repos-update

A Python CLI tool to recursively scan directories and update all git repositories.

## Features

- Recursively finds all git repositories in specified directories
- Runs `git pull --all` to fetch all branches
- Runs `git remote prune origin` to remove stale remote branches
- Colored terminal output (green=updated, gray=unchanged, red=error)
- Parallel updates with `-j N`
- Dry-run mode to preview changes
- Check for dirty (uncommitted) repositories

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
# Update all repos in a directory
uv run repos-update ~/Code

# Update repos in multiple directories
uv run repos-update ~/Code ~/Projects

# Update 8 repos in parallel (faster)
uv run repos-update -j 8 ~/Code

# Preview what would be updated (no changes made)
uv run repos-update --dry-run ~/Code

# List repos with uncommitted changes
uv run repos-update --dirty ~/Code

# Quiet mode - only show final report
uv run repos-update -q ~/Code
```

## Options

| Option | Description |
|--------|-------------|
| `-j N`, `--jobs N` | Update N repos in parallel (default: 1) |
| `--dry-run` | Show what would be updated without pulling |
| `--dirty` | List repos with uncommitted changes |
| `-q`, `--quiet` | Silent mode - only show final report |
| `--version` | Show version number |

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
