#!/usr/bin/env python3
"""Recursively scan directories and update git repositories."""

import argparse
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from importlib.metadata import version
from pathlib import Path
from typing import List, Optional

__version__ = version("repos-update")


class Color:
    """ANSI color codes."""
    GREEN = "\033[32m"
    YELLOW = "\033[38;5;229m"
    ORANGE = "\033[38;5;214m"
    RED = "\033[31m"
    MAGENTA = "\033[95m"
    GRAY = "\033[90m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


# Global settings for path display
_base_dirs: List[Path] = []
_full_path: bool = False


def set_path_display(base_dirs: List[Path], full_path: bool) -> None:
    """Configure how paths are displayed."""
    global _base_dirs, _full_path
    _base_dirs = [d.resolve() for d in base_dirs]
    _full_path = full_path


def format_path(path: Path) -> str:
    """Format a path for display (relative or absolute)."""
    if _full_path:
        return str(path)

    # Try to make path relative to one of the base directories
    path = path.resolve()
    for base in _base_dirs:
        try:
            return str(path.relative_to(base.parent))
        except ValueError:
            continue
    return str(path)


_SUMMARY_WIDTH = 50


def _summary_start(title: str = "Summary:") -> None:
    """Print summary section opener."""
    print(f"\n{Color.BOLD}{'═' * _SUMMARY_WIDTH}{Color.RESET}")
    print(f"{Color.BOLD}{title}{Color.RESET}")
    print(f"{'─' * _SUMMARY_WIDTH}")


def _summary_end(total: int) -> None:
    """Print summary section closer."""
    print(f"{'─' * _SUMMARY_WIDTH}")
    print(f"Total: {total} repositories")


class Status(Enum):
    """Repository update status."""
    UPDATED = "updated"
    UP_TO_DATE = "up_to_date"
    ERROR = "error"
    NO_REMOTE = "no_remote"


@dataclass
class RepoResult:
    """Result of a repository operation."""
    path: Path
    status: Status
    message: str = ""
    branch: str = ""
    changes: str = ""  # Change hints (e.g., "3 commits" or commit subject)


def find_repos(directories: List[Path], max_depth: int | None = None) -> List[Path]:
    """Find all git repositories in the given directories.

    Args:
        directories: List of directories to scan.
        max_depth: Maximum depth to search. None means unlimited.
                   Depth 1 = immediate subdirectories only.
    """
    repos = []
    for directory in directories:
        directory = directory.resolve()
        if not directory.exists():
            continue
        base_depth = len(directory.parts)
        for root, dirs, _ in os.walk(directory):
            current_depth = len(Path(root).parts) - base_depth
            if ".git" in dirs:
                repos.append(Path(root))
                dirs.remove(".git")  # Don't descend into .git
                dirs[:] = [d for d in dirs if not d.startswith(".")]  # Skip hidden dirs
            # Prune dirs if we've reached max depth
            if max_depth is not None and current_depth >= max_depth:
                dirs[:] = []
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


def get_remote_url(repo: Path, remote: str = "origin") -> str:
    """Get the URL of a remote."""
    result = run_git(repo, "remote", "get-url", remote)
    return result.stdout.strip() if result.returncode == 0 else ""


def _get_repo_remotes(repo: Path) -> tuple[Path, dict[str, str]]:
    """Get remotes for a single repo. Returns (repo, {}) if none configured."""
    result = run_git(repo, "remote", "-v")
    remotes: dict[str, str] = {}
    for line in result.stdout.strip().split("\n"):
        if line and "(fetch)" in line:
            parts = line.split()
            if len(parts) >= 2:
                remotes[parts[0]] = parts[1]
    return (repo, remotes)


def show_remotes(
    repos: List[Path],
    jobs: int = 1,
    show_with: bool = True,
    show_without: bool = True,
    quiet: bool = False,
) -> tuple[list[tuple[Path, dict[str, str]]], list[Path]]:
    """Show repos grouped by remote configuration (with-remote, no-remote).

    Live output prints whichever sections are selected by `show_with` /
    `show_without`, with the with-remote section first and a blank line
    separating the two when both are non-empty and both selected.
    """
    if jobs > 1:
        with ThreadPoolExecutor(max_workers=jobs) as executor:
            results = list(executor.map(_get_repo_remotes, repos))
    else:
        results = [_get_repo_remotes(repo) for repo in repos]

    with_remote: list[tuple[Path, dict[str, str]]] = [
        (repo, remotes) for repo, remotes in results if remotes
    ]
    without_remote: list[Path] = [
        repo for repo, remotes in results if not remotes
    ]
    with_remote.sort(key=lambda item: item[0].name.lower())
    without_remote.sort(key=lambda r: r.name.lower())

    if not quiet:
        printed_with = False
        if show_with:
            for repo, remotes in with_remote:
                path_str = format_path(repo)
                remote_str = ", ".join(f"{k}: {v}" for k, v in remotes.items())
                print(f"{Color.GREEN}●{Color.RESET} {path_str}")
                print(f"  {Color.GRAY}{remote_str}{Color.RESET}")
            printed_with = bool(with_remote)
        if show_without and without_remote:
            if printed_with:
                print()
            for repo in without_remote:
                print(f"{Color.GRAY}○{Color.RESET} {format_path(repo)}")

    return with_remote, without_remote


def show_remotes_raw(repos: List[Path], jobs: int = 1) -> None:
    """Print sorted origin URLs, one per line. Skips repos without origin."""
    if jobs > 1:
        with ThreadPoolExecutor(max_workers=jobs) as executor:
            results = list(executor.map(_get_repo_remotes, repos))
    else:
        results = [_get_repo_remotes(repo) for repo in repos]

    urls = sorted(
        remotes["origin"]
        for _, remotes in results
        if "origin" in remotes
    )
    for url in urls:
        print(url)


def print_remote_summary(
    with_remote: list[tuple[Path, dict[str, str]]],
    without_remote: list[Path],
    show_with: bool,
    show_without: bool,
) -> None:
    """Print counts-only summary for the remote command.

    Only buckets selected by the filter flags are shown; `Total:` reflects
    the included buckets so it stays consistent with the live output.
    """
    _summary_start()
    total = 0
    if show_with and with_remote:
        print(f"{Color.GREEN}● With remote:{Color.RESET} {len(with_remote)}")
        total += len(with_remote)
    if show_without and without_remote:
        print(f"{Color.GRAY}○ No remote:{Color.RESET} {len(without_remote)}")
        total += len(without_remote)
    _summary_end(total)


def get_repo_status(repo: Path, needs_fetch: bool = True) -> dict:
    """Get status info for a repository.

    When `needs_fetch` is False, skip the network calls (`git fetch` and the
    `rev-list` ahead/behind query) — useful when only the local dirty state is
    being inspected.
    """
    branch = get_current_branch(repo)
    dirty = is_dirty(repo)
    has_rem = has_remote(repo)
    ahead = behind = 0

    if has_rem and needs_fetch:
        run_git(repo, "fetch", "--quiet")
        result = run_git(repo, "rev-list", "--left-right", "--count", "@{u}...HEAD")
        if result.returncode == 0:
            parts = result.stdout.strip().split()
            if len(parts) == 2:
                behind, ahead = int(parts[0]), int(parts[1])

    return {
        "branch": branch,
        "dirty": dirty,
        "ahead": ahead,
        "behind": behind,
        "has_remote": has_rem,
    }


def _get_status_with_path(repo: Path, needs_fetch: bool = True) -> tuple[Path, dict]:
    """Get status for a repo along with its path."""
    return (repo, get_repo_status(repo, needs_fetch=needs_fetch))


def _format_status_line(repo: Path, status: dict) -> str:
    """Format one repo's status as a display line."""
    path_str = format_path(repo)
    branch = status["branch"]

    if not status["has_remote"]:
        return f"{Color.GRAY}○{Color.RESET} {path_str} ({branch}) {Color.GRAY}no remote{Color.RESET}"

    indicators = []
    if status["ahead"] > 0:
        indicators.append(f"{Color.GREEN}↑{status['ahead']}{Color.RESET}")
    if status["behind"] > 0:
        indicators.append(f"{Color.RED}↓{status['behind']}{Color.RESET}")
    if status["dirty"]:
        indicators.append(f"{Color.YELLOW}✗ dirty{Color.RESET}")
    if not indicators:
        indicators.append(f"{Color.GREEN}✓{Color.RESET}")

    return f"{Color.GREEN}●{Color.RESET} {path_str} ({branch}) {' '.join(indicators)}"


def _classify_status(status: dict) -> str:
    """Classify a repo status into a single bucket."""
    if not status["has_remote"]:
        return "no_remote"
    if status["dirty"]:
        return "dirty"
    if status["ahead"] > 0 and status["behind"] > 0:
        return "diverged"
    if status["ahead"] > 0:
        return "ahead"
    if status["behind"] > 0:
        return "behind"
    return "clean"


_NETWORK_CATEGORIES = frozenset({"clean", "ahead", "behind", "diverged"})


def show_status(
    repos: List[Path],
    jobs: int = 1,
    categories: set[str] | None = None,
    quiet: bool = False,
) -> None:
    """Show status summary for all repositories.

    Live output streams as each repo completes (unsorted) so the user gets
    progress feedback during network-bound `git fetch`. A sorted summary is
    printed at the end.

    When `categories` is provided, only repos whose classification falls in the
    set are shown. If none of the network-requiring categories is requested,
    `git fetch` is skipped entirely (e.g. `--dirty` alone runs offline).
    """
    needs_fetch = categories is None or bool(categories & _NETWORK_CATEGORIES)

    results: list[tuple[Path, dict]] = []

    def _emit(result: tuple[Path, dict]) -> None:
        results.append(result)
        if quiet:
            return
        if categories is not None and _classify_status(result[1]) not in categories:
            return
        print(_format_status_line(*result))

    if jobs > 1:
        with ThreadPoolExecutor(max_workers=jobs) as executor:
            futures = {
                executor.submit(_get_status_with_path, repo, needs_fetch): repo
                for repo in repos
            }
            for future in as_completed(futures):
                _emit(future.result())
    else:
        for repo in repos:
            _emit(_get_status_with_path(repo, needs_fetch))

    print_status_summary(results, categories=categories)


def print_status_summary(
    results: list[tuple[Path, dict]],
    categories: set[str] | None = None,
) -> None:
    """Print status summary grouped by state, sorted alphabetically.

    When `categories` is provided, only those buckets are shown and the total
    counts only the matching repos.
    """
    buckets: dict[str, list[tuple[Path, dict]]] = {
        "clean": [], "ahead": [], "behind": [], "diverged": [], "dirty": [], "no_remote": [],
    }
    for item in results:
        buckets[_classify_status(item[1])].append(item)
    for key in buckets:
        buckets[key].sort(key=lambda x: x[0].name.lower())

    def _show(bucket: str) -> bool:
        return categories is None or bucket in categories

    # When filters are active, the live output already lists the matching
    # repos — print only the bucket counts to avoid duplicating that detail.
    show_details = categories is None

    _summary_start()

    if _show("clean") and buckets["clean"]:
        print(f"{Color.GREEN}✓ Clean:{Color.RESET} {len(buckets['clean'])}")
    if _show("ahead") and buckets["ahead"]:
        print(f"{Color.GREEN}↑ Ahead:{Color.RESET} {len(buckets['ahead'])}")
        if show_details:
            for repo, s in buckets["ahead"]:
                print(f"  {format_path(repo)} ({s['branch']}) ↑{s['ahead']}")
    if _show("behind") and buckets["behind"]:
        print(f"{Color.RED}↓ Behind:{Color.RESET} {len(buckets['behind'])}")
        if show_details:
            for repo, s in buckets["behind"]:
                print(f"  {format_path(repo)} ({s['branch']}) ↓{s['behind']}")
    if _show("diverged") and buckets["diverged"]:
        print(f"{Color.RED}⇅ Diverged:{Color.RESET} {len(buckets['diverged'])}")
        if show_details:
            for repo, s in buckets["diverged"]:
                print(f"  {format_path(repo)} ({s['branch']}) ↑{s['ahead']} ↓{s['behind']}")
    if _show("dirty") and buckets["dirty"]:
        print(f"{Color.YELLOW}✗ Dirty:{Color.RESET} {len(buckets['dirty'])}")
        if show_details:
            for repo, s in buckets["dirty"]:
                sync = ""
                if s["ahead"] > 0:
                    sync += f" ↑{s['ahead']}"
                if s["behind"] > 0:
                    sync += f" ↓{s['behind']}"
                print(f"  {format_path(repo)} ({s['branch']}){sync}")
    if _show("no_remote") and buckets["no_remote"]:
        print(f"{Color.GRAY}○ No remote:{Color.RESET} {len(buckets['no_remote'])}")
        if show_details:
            for repo, s in buckets["no_remote"]:
                print(f"  {format_path(repo)} ({s['branch']})")

    if categories is None:
        total = len(results)
    else:
        total = sum(len(buckets[c]) for c in categories if c in buckets)
    _summary_end(total)


def get_current_branch(repo: Path) -> str:
    """Get the current branch name."""
    result = run_git(repo, "branch", "--show-current")
    return result.stdout.strip() or "HEAD"


def get_head_commit(repo: Path) -> str:
    """Get current HEAD commit hash."""
    result = run_git(repo, "rev-parse", "HEAD")
    return result.stdout.strip()


def get_diff_stats(repo: Path, old_head: str, new_head: str) -> str:
    """Get file/line change stats between two commits."""
    result = run_git(repo, "diff", "--shortstat", f"{old_head}..{new_head}")
    output = result.stdout.strip()
    if not output:
        return ""

    # Parse files, insertions, deletions
    files = insertions = deletions = 0
    if "file" in output:
        match = re.search(r'(\d+) file', output)
        files = int(match.group(1)) if match else 0
    if "insertion" in output:
        match = re.search(r'(\d+) insertion', output)
        insertions = int(match.group(1)) if match else 0
    if "deletion" in output:
        match = re.search(r'(\d+) deletion', output)
        deletions = int(match.group(1)) if match else 0

    # Format: "5 files ▲120 ▼45" with colors
    parts = []
    if files:
        parts.append(f"{files} file{'s' if files != 1 else ''}")
    if insertions or deletions:
        parts.append(f"{Color.GREEN}▲{insertions}{Color.RESET} {Color.RED}▼{deletions}{Color.RESET}")
    return " ".join(parts)


def get_change_summary(repo: Path, old_head: str, new_head: str) -> str:
    """Get summary of changes between two commits."""
    if old_head == new_head:
        return ""

    # Get commit info
    result = run_git(repo, "log", "--oneline", f"{old_head}..{new_head}")
    lines = [l for l in result.stdout.strip().split("\n") if l]

    if not lines:
        return ""

    # Get diff stats
    stats = get_diff_stats(repo, old_head, new_head)

    # Build summary - always show commit count
    count = len(lines)
    commit_info = f"{count} commit{'s' if count != 1 else ''}"

    if stats:
        return f"{commit_info}, {stats}"
    return commit_info


def is_dirty(repo: Path) -> bool:
    """Check if repository has uncommitted changes."""
    result = run_git(repo, "status", "--porcelain")
    return bool(result.stdout.strip())


def get_last_commit_age(repo: Path) -> tuple[datetime | None, str]:
    """Get the date of the last commit and formatted age string."""
    result = run_git(repo, "log", "-1", "--format=%ci")
    if result.returncode != 0 or not result.stdout.strip():
        return None, "no commits"

    # Parse the date (format: 2024-01-15 10:30:45 +0000)
    date_str = result.stdout.strip()
    try:
        commit_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S %z")
    except ValueError:
        return None, "unknown"

    now = datetime.now(timezone.utc)
    delta = now - commit_date

    # Format as human-readable age
    days = delta.days
    if days == 0:
        hours = delta.seconds // 3600
        if hours == 0:
            minutes = delta.seconds // 60
            if minutes == 0:
                return commit_date, "just now"
            return commit_date, f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        return commit_date, f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif days == 1:
        return commit_date, "1 day ago"
    elif days < 30:
        return commit_date, f"{days} days ago"
    elif days < 60:
        return commit_date, "1 month ago"
    elif days < 365:
        months = days // 30
        return commit_date, f"{months} months ago"
    elif days < 730:
        return commit_date, "1 year ago"
    else:
        years = days // 365
        return commit_date, f"{years} years ago"


def get_age_color(commit_date: datetime | None) -> str:
    """Return appropriate color based on commit age."""
    if commit_date is None:
        return Color.GRAY

    now = datetime.now(timezone.utc)
    delta = now - commit_date
    days = delta.days

    if days <= 30:  # Within 1 month
        return Color.GREEN
    elif days <= 90:  # Within 3 months
        return Color.YELLOW
    elif days <= 180:  # Within 6 months
        return Color.ORANGE
    elif days <= 365:  # Within 1 year
        return Color.RED
    else:  # Over 1 year
        return Color.MAGENTA


def get_age_category(commit_date: datetime | None) -> str:
    """Return age category name based on commit date."""
    if commit_date is None:
        return "unknown"

    now = datetime.now(timezone.utc)
    delta = now - commit_date
    days = delta.days

    if days <= 30:  # Within 1 month
        return "recent"
    elif days <= 90:  # Within 3 months
        return "aging"
    elif days <= 180:  # Within 6 months
        return "stale"
    elif days <= 365:  # Within 1 year
        return "old"
    else:  # Over 1 year
        return "ancient"


def _get_age_with_path(repo: Path) -> tuple[Path, datetime | None, str]:
    """Get age info for a repo along with its path."""
    commit_date, age_str = get_last_commit_age(repo)
    return (repo, commit_date, age_str)


def show_age(
    repos: List[Path],
    jobs: int = 1,
    categories: set[str] | None = None,
    quiet: bool = False,
) -> None:
    """Display the age of the last commit for each repository.

    Args:
        repos: List of repository paths to check.
        jobs: Number of parallel jobs.
        categories: If provided, only show repos in these categories
                   ("recent", "aging", "stale", "old").
        quiet: Suppress per-repo output (summary still prints).
    """
    if jobs > 1:
        with ThreadPoolExecutor(max_workers=jobs) as executor:
            results = list(executor.map(_get_age_with_path, repos))
    else:
        results = [_get_age_with_path(repo) for repo in repos]

    # Sort most recent first; repos with no commit date go last
    results.sort(
        key=lambda r: r[1] or datetime.min.replace(tzinfo=timezone.utc),
        reverse=True,
    )

    filtered = []
    for repo, commit_date, age_str in results:
        if categories:
            category = get_age_category(commit_date)
            if category not in categories:
                continue
        filtered.append((repo, commit_date, age_str))

        if not quiet:
            path_str = format_path(repo)
            color = get_age_color(commit_date)
            print(f"{color}●{Color.RESET} {path_str} {color}{age_str}{Color.RESET}")

    print_age_summary(filtered)


def print_age_summary(results: list[tuple[Path, datetime | None, str]]) -> None:
    """Print age summary with counts per category."""
    buckets: dict[str, int] = {
        "recent": 0, "aging": 0, "stale": 0, "old": 0, "ancient": 0, "unknown": 0,
    }
    for _, commit_date, _ in results:
        buckets[get_age_category(commit_date)] += 1

    _summary_start()
    if buckets["recent"]:
        print(f"{Color.GREEN}● Recent (≤30 days):{Color.RESET} {buckets['recent']}")
    if buckets["aging"]:
        print(f"{Color.YELLOW}● Aging (31-90 days):{Color.RESET} {buckets['aging']}")
    if buckets["stale"]:
        print(f"{Color.ORANGE}● Stale (91-180 days):{Color.RESET} {buckets['stale']}")
    if buckets["old"]:
        print(f"{Color.RED}● Old (181-365 days):{Color.RESET} {buckets['old']}")
    if buckets["ancient"]:
        print(f"{Color.MAGENTA}● Ancient (>1 year):{Color.RESET} {buckets['ancient']}")
    if buckets["unknown"]:
        print(f"{Color.GRAY}● Unknown:{Color.RESET} {buckets['unknown']}")
    _summary_end(len(results))


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

    # Capture HEAD before pull
    old_head = get_head_commit(repo)

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

    # Get change summary
    new_head = get_head_commit(repo)
    changes = get_change_summary(repo, old_head, new_head)

    return RepoResult(repo, Status.UPDATED, pull_result.stdout.strip(), branch, changes)


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

    # Add change hints for updated repos
    hint = f" {Color.GRAY}({result.changes}){Color.RESET}" if result.changes else ""
    print(f"{color}{symbol}{Color.RESET} {prefix}{format_path(result.path)}{hint}")


def print_report(results: List[RepoResult], dry_run: bool = False) -> None:
    """Print colored summary report."""
    def by_name(rs: List[RepoResult]) -> List[RepoResult]:
        return sorted(rs, key=lambda r: r.path.name.lower())

    updated = by_name([r for r in results if r.status == Status.UPDATED])
    up_to_date = [r for r in results if r.status == Status.UP_TO_DATE]
    errors = by_name([r for r in results if r.status == Status.ERROR])
    no_remote = [r for r in results if r.status == Status.NO_REMOTE]

    prefix = "[DRY-RUN] " if dry_run else ""
    _summary_start(f"{prefix}Summary:")

    if updated:
        action = "Would update" if dry_run else "Updated"
        print(f"{Color.GREEN}✓ {action}:{Color.RESET} {len(updated)}")
        for r in updated:
            hint = f" {Color.GRAY}({r.changes}){Color.RESET}" if r.changes else ""
            print(f"  {format_path(r.path)}{hint}")

    if up_to_date:
        print(f"{Color.GRAY}· Already up to date:{Color.RESET} {len(up_to_date)}")

    if no_remote:
        print(f"{Color.GRAY}○ No remote:{Color.RESET} {len(no_remote)}")

    if errors:
        print(f"{Color.RED}✗ Errors:{Color.RESET} {len(errors)}")
        for r in errors:
            print(f"  {format_path(r.path)}")
            if r.message:
                for line in r.message.split("\n")[:3]:
                    print(f"    {Color.RED}{line}{Color.RESET}")

    _summary_end(len(results))


COMMANDS = {"update", "status", "remote", "age"}


def _run_command(args: argparse.Namespace) -> int:
    """Run the selected command."""
    directories = [Path(d) for d in args.directories]

    # Configure path display
    set_path_display(directories, args.full_path)

    quiet = getattr(args, "quiet", False)
    raw_remote = args.command == "remote" and getattr(args, "raw", False)

    if not quiet and not raw_remote:
        print(f"{Color.BOLD}Scanning for git repositories...{Color.RESET}")

    repos = find_repos(directories, args.tree)

    if not repos:
        if not raw_remote:
            print("No git repositories found.")
        return 0

    if not quiet and not raw_remote:
        print(f"Found {len(repos)} repositories.\n")

    command = args.command
    jobs = args.jobs

    if command == "remote":
        if args.raw:
            if args.without_remote:
                print(
                    f"{Color.RED}Error:{Color.RESET} "
                    "--raw cannot be combined with --without-remote",
                    file=sys.stderr,
                )
                return 1
            show_remotes_raw(repos, jobs=jobs)
            return 0
        show_with = args.with_remote
        show_without = args.without_remote
        if not (show_with or show_without):
            show_with = show_without = True
        with_remote, without_remote = show_remotes(
            repos,
            jobs=jobs,
            show_with=show_with,
            show_without=show_without,
            quiet=quiet,
        )
        print_remote_summary(with_remote, without_remote, show_with, show_without)
        return 0

    if command == "status":
        status_categories = {
            cat
            for cat in ("clean", "ahead", "behind", "diverged", "dirty")
            if getattr(args, cat, False)
        }
        show_status(
            repos,
            jobs=jobs,
            categories=status_categories or None,
            quiet=quiet,
        )
        return 0

    if command == "age":
        categories = set()
        for cat in ("recent", "aging", "stale", "old", "ancient"):
            if getattr(args, cat, False):
                categories.add(cat)
        show_age(repos, jobs=jobs, categories=categories or None, quiet=quiet)
        return 0

    # Default: update command
    results = update_repos_parallel(
        repos,
        jobs=jobs,
        dry_run=getattr(args, "dry_run", False),
        quiet=quiet,
    )

    print_report(results, getattr(args, "dry_run", False))

    # Return non-zero if there were errors
    errors = [r for r in results if r.status == Status.ERROR]
    return 1 if errors else 0


def _looks_like_path(arg: str) -> bool:
    """Check if argument looks like a path (not a command typo)."""
    # Starts with path-like prefix
    if arg.startswith(("/", "~", ".", "..")):
        return True
    # Contains path separator
    if "/" in arg or "\\" in arg:
        return True
    # Actually exists as a directory
    path = Path(arg).expanduser()
    if path.is_dir():
        return True
    return False


def main(argv: Optional[List[str]] = None) -> int:
    """Main entry point."""
    if argv is None:
        argv = sys.argv[1:]

    # Check for unknown command before setting up parser
    unknown_command = None
    if argv and argv[0] not in COMMANDS and argv[0] not in ("-h", "--help", "--version"):
        if argv[0].startswith("-"):
            # It's an option, let argparse handle it
            argv = ["update"] + list(argv)
        elif _looks_like_path(argv[0]):
            # It's a path, use implicit update command
            argv = ["update"] + list(argv)
        else:
            # Unknown command - save it and show help + error later
            unknown_command = argv[0]
            argv = []  # Clear to trigger help display

    parser = argparse.ArgumentParser(
        prog="repos-update",
        description="Recursively scan directories and update git repositories.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", title="commands", metavar="")

    # Shared arguments for all commands
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument(
        "directories",
        nargs="+",
        metavar="DIRECTORY",
        help="Directories to scan",
    )
    shared.add_argument(
        "-j", "--jobs",
        type=int,
        default=1,
        metavar="N",
        help="Process N repos in parallel (default: 1)",
    )
    shared.add_argument(
        "--full-path",
        action="store_true",
        help="Show full absolute paths instead of relative paths",
    )
    shared.add_argument(
        "-q", "--quiet",
        action="store_true",
        help="Quiet mode - only show summary",
    )
    def positive_int(value: str) -> int:
        """Validate that value is a positive integer (>= 1)."""
        try:
            ivalue = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError(f"invalid int value: '{value}'")
        if ivalue < 1:
            raise argparse.ArgumentTypeError(f"must be >= 1, got {ivalue}")
        return ivalue

    shared.add_argument(
        "-t", "--tree",
        type=positive_int,
        default=None,
        metavar="N",
        help="Limit search depth to N levels (1 = immediate subdirs only)",
    )

    # update command
    update_parser = subparsers.add_parser(
        "update",
        parents=[shared],
        help="Update repositories (default command)",
    )
    update_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be updated without pulling",
    )

    # remote command
    remote_parser = subparsers.add_parser(
        "remote",
        parents=[shared],
        help="List repos by remote configuration (with/without remotes)",
    )
    remote_parser.add_argument(
        "--with-remote",
        action="store_true",
        help="Show only repos that have a remote configured",
    )
    remote_parser.add_argument(
        "--without-remote",
        action="store_true",
        help="Show only repos without any remote configured",
    )
    remote_parser.add_argument(
        "--raw",
        action="store_true",
        help="Print only origin URLs, sorted, one per line (pipe-friendly)",
    )

    # status command
    status_parser = subparsers.add_parser(
        "status",
        parents=[shared],
        help="Show status: branch, ahead/behind, dirty state",
    )
    status_parser.add_argument(
        "--clean",
        action="store_true",
        help="Show only clean repos (in sync, no uncommitted changes)",
    )
    status_parser.add_argument(
        "--ahead",
        action="store_true",
        help="Show only repos with unpushed commits",
    )
    status_parser.add_argument(
        "--behind",
        action="store_true",
        help="Show only repos with unpulled commits",
    )
    status_parser.add_argument(
        "--diverged",
        action="store_true",
        help="Show only repos both ahead and behind",
    )
    status_parser.add_argument(
        "--dirty",
        action="store_true",
        help="Show only repos with uncommitted changes (skips fetch — fast/offline)",
    )

    # age command
    age_parser = subparsers.add_parser(
        "age",
        parents=[shared],
        help="Show age of last commit for each repository",
    )
    age_parser.add_argument(
        "--recent",
        action="store_true",
        help="Show repos updated within 1 month (green)",
    )
    age_parser.add_argument(
        "--aging",
        action="store_true",
        help="Show repos updated 1-3 months ago (yellow)",
    )
    age_parser.add_argument(
        "--stale",
        action="store_true",
        help="Show repos updated 3-6 months ago (orange)",
    )
    age_parser.add_argument(
        "--old",
        action="store_true",
        help="Show repos updated 6-12 months ago (red)",
    )
    age_parser.add_argument(
        "--ancient",
        action="store_true",
        help="Show repos not updated in over 1 year (magenta)",
    )

    # Reorder help sections: commands before options
    for i, group in enumerate(parser._action_groups):
        if group.title == "commands":
            parser._action_groups.insert(0, parser._action_groups.pop(i))
            break

    # Print usage if no arguments provided (or unknown command)
    if not argv:
        parser.print_help()
        if unknown_command:
            print(f"\n{Color.RED}Error:{Color.RESET} Unknown command: {unknown_command}")
            return 1
        return 0

    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return _run_command(args)


if __name__ == "__main__":
    sys.exit(main())
