# Design: `--with-path` for `remote --raw`

Date: 2026-06-27

## Problem

`repos-update remote ~/Code --raw` prints sorted `origin` URLs, one per line —
convenient for `grep`-filtering remotes. But the user often also wants to know
the local directory on disk where a matching repo lives, which the raw output
discards.

## Solution

Add a `--with-path` flag to the `remote` command. When set, each raw line
becomes `<path>: <url>` instead of just `<url>`.

### Behavior

- `--with-path` **implies** `--raw` (passing it alone enables raw mode).
- Output line format: `f"{format_path(repo)}: {url}"`.
- `<path>` uses the existing `format_path()`, so it honors the global
  `--full-path` flag: relative by default (e.g. `Code/bar`), absolute with
  `--full-path`.
- Repos without an `origin` remote are skipped (unchanged from current `--raw`).

### Example

```
$ repos-update remote ~/Code --raw --with-path
Code/bar: git@github.com:foo/bar.git
Code/me/baz: git@github.com:me/baz.git
```

Still greppable by URL (`| grep github.com:foo`); the path is recoverable with
`cut -d: -f1`.

### Sorting

- Plain `--raw` (no path): sort by URL — unchanged.
- `--raw --with-path`: sort by the displayed line (path leads), giving a natural
  alphabetical-by-location ordering.

### Validation / edge cases

- `--with-path` without `--raw`: treated as raw mode (implies `--raw`).
- `--without-remote` cannot combine with raw mode. The existing check already
  blocks `--raw` + `--without-remote`; it must also fire when raw is active via
  `--with-path`.

## Code changes (`repos_update.py`)

- `show_remotes_raw(repos, jobs=1, with_path=False)`: when `with_path`, build
  `f"{format_path(repo)}: {url}"` lines and sort by the line; otherwise sort by
  URL as today.
- Compute `raw_active = args.raw or args.with_path` in the `remote` handler.
  Use it for the `raw_remote` quiet-suppression flag and to select the raw
  branch. Keep the `--without-remote` conflict check against `raw_active`.
- Add the `--with-path` argument to the `remote` subparser.
- Update `README.md` and `CLAUDE.md`.

## Out of scope (YAGNI)

- A fully configurable `--format` template — a fixed `<path>: <url>` shape is
  sufficient.
- A path-only mode — `cut -d: -f1` covers it.
