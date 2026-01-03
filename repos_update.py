#!/usr/bin/env python3
"""Recursively scan directories and update git repositories."""

import argparse
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import List, Optional

__version__ = "0.1.0"


class Color:
    """ANSI color codes."""
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


class Status(Enum):
    """Repository update status."""
    UPDATED = "updated"
    UP_TO_DATE = "up_to_date"
    ERROR = "error"
    NO_REMOTE = "no_remote"
    DIRTY = "dirty"


@dataclass
class RepoResult:
    """Result of a repository operation."""
    path: Path
    status: Status
    message: str = ""
    branch: str = ""


def find_repos(directories: List[Path]) -> List[Path]:
    """Find all git repositories in the given directories."""
    repos = []
    for directory in directories:
        directory = directory.resolve()
        if not directory.exists():
            continue
        for root, dirs, _ in os.walk(directory):
            if ".git" in dirs:
                repos.append(Path(root))
                dirs.remove(".git")  # Don't descend into .git
                dirs[:] = [d for d in dirs if not d.startswith(".")]  # Skip hidden dirs
    return repos


def run_git(repo: Path, *args: str, capture: bool = True) -> subprocess.CompletedProcess:
    """Run a git command in the given repository."""
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=capture,
        text=True,
    )


def has_remote(repo: Path) -> bool:
    """Check if repository has a remote configured."""
    result = run_git(repo, "remote")
    return bool(result.stdout.strip())


def get_current_branch(repo: Path) -> str:
    """Get the current branch name."""
    result = run_git(repo, "branch", "--show-current")
    return result.stdout.strip() or "HEAD"


def is_dirty(repo: Path) -> bool:
    """Check if repository has uncommitted changes."""
    result = run_git(repo, "status", "--porcelain")
    return bool(result.stdout.strip())


def check_updates_available(repo: Path) -> tuple[bool, str]:
    """Fetch and check if updates are available (for dry-run)."""
    # Fetch all remotes
    fetch_result = run_git(repo, "fetch", "--all", "--quiet")
    if fetch_result.returncode != 0:
        return False, fetch_result.stderr.strip()

    # Check if behind remote
    result = run_git(repo, "status", "-uno")
    output = result.stdout.lower()
    if "your branch is behind" in output:
        return True, "Updates available"
    return False, "Already up to date"


def update_repo(repo: Path, dry_run: bool = False) -> RepoResult:
    """Update a single repository."""
    branch = get_current_branch(repo)

    if not has_remote(repo):
        return RepoResult(repo, Status.NO_REMOTE, "No remote configured", branch)

    if dry_run:
        has_updates, message = check_updates_available(repo)
        if has_updates:
            return RepoResult(repo, Status.UPDATED, message, branch)
        return RepoResult(repo, Status.UP_TO_DATE, message, branch)

    # Run git pull --all
    pull_result = run_git(repo, "pull", "--all")

    # Prune stale remote branches
    run_git(repo, "remote", "prune", "origin")

    if pull_result.returncode != 0:
        error_msg = pull_result.stderr.strip() or pull_result.stdout.strip()
        return RepoResult(repo, Status.ERROR, error_msg, branch)

    output = pull_result.stdout.lower()
    if "already up to date" in output or "already up-to-date" in output:
        return RepoResult(repo, Status.UP_TO_DATE, "Already up to date", branch)

    return RepoResult(repo, Status.UPDATED, pull_result.stdout.strip(), branch)


def check_dirty_repos(repos: List[Path], quiet: bool = False) -> List[RepoResult]:
    """Check which repositories have uncommitted changes."""
    results = []
    for repo in repos:
        branch = get_current_branch(repo)
        if is_dirty(repo):
            result = run_git(repo, "status", "--porcelain")
            results.append(RepoResult(repo, Status.DIRTY, result.stdout.strip(), branch))
            if not quiet:
                print(f"{Color.YELLOW}Dirty:{Color.RESET} {repo}")
    return results


def update_repos_parallel(
    repos: List[Path],
    jobs: int,
    dry_run: bool = False,
    quiet: bool = False,
) -> List[RepoResult]:
    """Update repositories in parallel."""
    results = []

    with ThreadPoolExecutor(max_workers=jobs) as executor:
        future_to_repo = {
            executor.submit(update_repo, repo, dry_run): repo
            for repo in repos
        }

        for future in as_completed(future_to_repo):
            result = future.result()
            results.append(result)

            if not quiet:
                print_progress(result, dry_run)

    return results


def print_progress(result: RepoResult, dry_run: bool = False) -> None:
    """Print progress for a single repository."""
    prefix = "[DRY-RUN] " if dry_run else ""

    if result.status == Status.UPDATED:
        color = Color.GREEN
        symbol = "✓"
    elif result.status == Status.UP_TO_DATE:
        color = Color.GRAY
        symbol = "·"
    elif result.status == Status.NO_REMOTE:
        color = Color.GRAY
        symbol = "○"
    else:
        color = Color.RED
        symbol = "✗"

    print(f"{color}{symbol}{Color.RESET} {prefix}{result.path}")


def print_report(results: List[RepoResult], dry_run: bool = False) -> None:
    """Print colored summary report."""
    updated = [r for r in results if r.status == Status.UPDATED]
    up_to_date = [r for r in results if r.status == Status.UP_TO_DATE]
    errors = [r for r in results if r.status == Status.ERROR]
    no_remote = [r for r in results if r.status == Status.NO_REMOTE]
    dirty = [r for r in results if r.status == Status.DIRTY]

    print(f"\n{Color.BOLD}{'═' * 50}{Color.RESET}")
    prefix = "[DRY-RUN] " if dry_run else ""
    print(f"{Color.BOLD}{prefix}Summary:{Color.RESET}")
    print(f"{'─' * 50}")

    if updated:
        action = "Would update" if dry_run else "Updated"
        print(f"{Color.GREEN}✓ {action}:{Color.RESET} {len(updated)}")
        for r in updated:
            print(f"  {r.path}")

    if up_to_date:
        print(f"{Color.GRAY}· Already up to date:{Color.RESET} {len(up_to_date)}")

    if no_remote:
        print(f"{Color.GRAY}○ No remote:{Color.RESET} {len(no_remote)}")

    if dirty:
        print(f"{Color.YELLOW}! Dirty repos:{Color.RESET} {len(dirty)}")
        for r in dirty:
            print(f"  {r.path}")

    if errors:
        print(f"{Color.RED}✗ Errors:{Color.RESET} {len(errors)}")
        for r in errors:
            print(f"  {r.path}")
            if r.message:
                for line in r.message.split("\n")[:3]:
                    print(f"    {Color.RED}{line}{Color.RESET}")

    print(f"{'─' * 50}")
    print(f"Total: {len(results)} repositories")


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        prog="repos-update",
        description="Recursively scan directories and update git repositories.",
    )
    parser.add_argument(
        "directories",
        nargs="*",
        default=["."],
        help="Directories to scan (default: current directory)",
    )
    parser.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Silent mode - only show final report",
    )
    parser.add_argument(
        "-j", "--jobs",
        type=int,
        default=1,
        metavar="N",
        help="Update N repos in parallel (default: 1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without pulling",
    )
    parser.add_argument(
        "--dirty",
        action="store_true",
        help="List repos with uncommitted changes (no updates)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args(argv)

    directories = [Path(d) for d in args.directories]

    if not args.quiet:
        print(f"{Color.BOLD}Scanning for git repositories...{Color.RESET}")

    repos = find_repos(directories)

    if not repos:
        print("No git repositories found.")
        return 0

    if not args.quiet:
        print(f"Found {len(repos)} repositories.\n")

    # --dirty mode: just list dirty repos
    if args.dirty:
        results = check_dirty_repos(repos, args.quiet)
        if not results:
            print(f"{Color.GREEN}All repositories are clean.{Color.RESET}")
        else:
            print(f"\n{Color.YELLOW}{len(results)} dirty repositories found.{Color.RESET}")
        return 0

    # Update repos
    results = update_repos_parallel(
        repos,
        jobs=args.jobs,
        dry_run=args.dry_run,
        quiet=args.quiet,
    )

    print_report(results, args.dry_run)

    # Return non-zero if there were errors
    errors = [r for r in results if r.status == Status.ERROR]
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
