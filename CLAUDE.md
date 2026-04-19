# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Python CLI tool to recursively scan directories and update all git repositories.

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
# Commands
uv run repos-update ~/Code                  # Update repos (default command)
uv run repos-update update ~/Code --dry-run # Show what would be updated
uv run repos-update dirty ~/Code            # List repos with uncommitted changes
uv run repos-update status ~/Code           # Show branch, ahead/behind, dirty state
uv run repos-update age ~/Code              # Show last commit age (color-coded)
uv run repos-update age ~/Code --stale --old --ancient # Filter by age category
uv run repos-update remote ~/Code           # List repos by remote configuration (both buckets)
uv run repos-update remote ~/Code --without-remote # Only repos without a remote

# Global options (all commands)
-j N, --jobs N                              # Process N repos in parallel
-t N, --tree N                              # Limit search depth to N levels
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
- `show_remotes()` - Display repos grouped by remote configuration, with optional bucket filtering
- `get_last_commit_age()` - Get last commit date and formatted age string
- `get_age_color()` - Return color based on commit age thresholds
- `get_age_category()` - Return age category name (recent, aging, stale, old)
- `show_age()` - Display last commit age for all repos (supports category filtering)

## Important

- Alway update the README.md, and the CLAUDE.md (if applicable) before of making a commit.
