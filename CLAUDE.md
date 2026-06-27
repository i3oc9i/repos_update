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
uv run repos-update status ~/Code           # Show branch, ahead/behind, dirty state
uv run repos-update status ~/Code --dirty   # Only repos with uncommitted changes (skips fetch)
uv run repos-update status ~/Code --ahead --behind # Combine filters; fetch runs
uv run repos-update age ~/Code              # Show last commit age (color-coded)
uv run repos-update age ~/Code --stale --old --ancient # Filter by age category
uv run repos-update stars ~/Code            # Show GitHub star count (requires `gh auth login`)
uv run repos-update stars ~/Code --famous --iconic # Filter by star-count category
uv run repos-update remote ~/Code           # List repos by remote configuration (both buckets)
uv run repos-update remote ~/Code --without-remote # Only repos without a remote
uv run repos-update remote ~/Code --raw     # Print only origin URLs, sorted (pipe-friendly)
uv run repos-update remote ~/Code --with-path # Raw output as '<path>: <url>' (implies --raw)

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
- `get_repo_status()` - Get branch, ahead/behind, dirty state; `needs_fetch=False` skips network for offline checks
- `show_status()` - Display status for all repos; supports category filtering (clean/ahead/behind/diverged/dirty); skips fetch when only local categories are requested
- `show_remotes()` - Display repos grouped by remote configuration, with optional bucket filtering
- `show_remotes_raw()` - Print sorted origin URLs only (pipe-friendly), skipping repos without origin; `with_path=True` prints `<path>: <url>` sorted by path
- `get_last_commit_age()` - Get last commit date and formatted age string
- `get_age_color()` - Return color based on commit age thresholds
- `get_age_category()` - Return age category name (recent, aging, stale, old)
- `show_age()` - Display last commit age for all repos (supports category filtering)
- `parse_github_url()` - Parse SSH/HTTPS GitHub remote URL into `(owner, repo)`; returns `None` for non-GitHub URLs
- `get_github_stars()` - Query star count via `gh api repos/{owner}/{repo} --jq .stargazers_count`; returns `None` on any error
- `get_stars_color()` / `get_stars_category()` - Map a star count to color / bucket name (modest/popular/notable/famous/iconic)
- `show_stars()` - Display star count per repo, parallelized via `--jobs`; supports category filtering

## Important

- Alway update the README.md, and the CLAUDE.md (if applicable) before of making a commit.
