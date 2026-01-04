# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Python CLI tool to recursively scan directories and update all git repositories.

## Installation

```bash
uv pip install -e .
```

## Usage

```bash
# Commands
uv run repos-update ~/Code                  # Update repos (default command)
uv run repos-update update ~/Code --dry-run # Show what would be updated
uv run repos-update dirty ~/Code            # List repos with uncommitted changes
uv run repos-update status ~/Code           # Show branch, ahead/behind, dirty state
uv run repos-update remote ~/Code           # List repos that have a remote
uv run repos-update no-remote ~/Code        # List repos without a remote

# Global options (all commands)
-j N, --jobs N                              # Process N repos in parallel
--full-path                                 # Show absolute paths
-q, --quiet                                 # Quiet mode
```

## Project Structure

Single-file module: `repos_update.py`

## Key Functions

- `find_repos()` - Recursively find `.git` directories
- `update_repo()` - Run `git pull --all` + `git remote prune origin`
- `is_dirty()` - Check for uncommitted changes
- `update_repos_parallel()` - ThreadPoolExecutor for parallel updates
- `get_change_summary()` - Get commit count and diff stats
- `get_diff_stats()` - Parse `git diff --shortstat` for files/lines changed
- `format_path()` - Format paths as relative or absolute
- `get_repo_status()` - Get branch, ahead/behind, dirty state
- `show_status()` - Display status for all repos
- `list_remotes()` - List repos that have remotes configured

## Important

- Alway update the README.md, and the CLAUDE.md (if applicable) before of making a commit.
