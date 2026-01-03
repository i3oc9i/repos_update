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
uv run repos-update [directories...]     # Update repos in directories
uv run repos-update -j 4                 # Update 4 repos in parallel
uv run repos-update --dry-run            # Show what would be updated
uv run repos-update --dirty              # List repos with uncommitted changes
uv run repos-update -q                   # Quiet mode (only show final report)
```

## Project Structure

Single-file module: `repos_update.py`

## Key Functions

- `find_repos()` - Recursively find `.git` directories
- `update_repo()` - Run `git pull --all` + `git remote prune origin`
- `is_dirty()` - Check for uncommitted changes
- `update_repos_parallel()` - ThreadPoolExecutor for parallel updates
