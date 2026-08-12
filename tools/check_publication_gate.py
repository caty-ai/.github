#!/usr/bin/env python3
"""Fail closed when publication sources expose private context."""

import html
from pathlib import Path
import re
import urllib.parse


REPO_ROOT = Path(__file__).resolve().parent.parent
SCANNED_SUFFIXES = {".md", ".json", ".py", ".yml", ".yaml", ".svg", ".sh"}
EXCLUDED_DIRS = {".git", ".omc", ".omx"}
ACCOUNT_SLUG = "sho" + "jikumaru"

# Sensitive literals are split so the gate does not trip on its own source when self-scanned.
DENYLIST_PATTERNS = (
    (
        "personal real name",
        re.compile(r"\b(?:" + "Sho" + "ji|Ku" + "maru" + r")\b", re.IGNORECASE),
    ),
    (
        "personal real name",
        re.compile("翔" + "さん|翔" + "士|翔" + "どん", re.IGNORECASE),
    ),
    (
        "approval record",
        re.compile(
            "承認"
            + "記録|オーナー"
            + "承認|approved"
            + r"\s+by|CP-\d+[A-Za-z]{0,2}\s*(?:GO|承認)",
            re.IGNORECASE,
        ),
    ),
    ("absolute personal path", re.compile(re.escape("/" + "Users" + "/"))),
    (
        "private network address",
        re.compile(r"\b100\.(?:6[4-9]|[7-9][0-9]|1[01][0-9]|12[0-7])\.\d+\.\d+\b"),
    ),
    ("local service address", re.compile("local" + r"host:\d+", re.IGNORECASE)),
    ("local service address", re.compile(r"\b(?:127\.0\.0\.1|0\.0\.0\.0)\b")),
    (
        "email address",
        re.compile(r"\b[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
    (
        "private repository reference",
        re.compile(
            r"\b(?:"
            + "alpha-" + "loom|alpha-" + "wiki|alpha-" + "mission-control|"
            + "family-" + "vault|wip-" + "caty-talk|sitter-" + "private|claude-" + "workspace"
            + r")\b",
            re.IGNORECASE,
        ),
    ),
)
PERSONAL_GITHUB_URL = re.compile(
    r"(?<![A-Za-z0-9.-])(?:www\.)?github\.com/"
    + re.escape(ACCOUNT_SLUG)
    + r"(?:/(?P<repo>[A-Za-z0-9_.-]*[A-Za-z0-9_-])(?=$|[^A-Za-z0-9_-])|/?(?![A-Za-z0-9_.-]))",
    re.IGNORECASE,
)


def iter_paths(root):
    for path in root.rglob("*"):
        if any(part in EXCLUDED_DIRS for part in path.parts):
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in SCANNED_SUFFIXES:
            yield path


def scan_views(text):
    views = [text]
    current = text
    for _ in range(3):
        unquoted = urllib.parse.unquote(current)
        if unquoted not in views:
            views.append(unquoted)
        unescaped = html.unescape(unquoted)
        if unescaped not in views:
            views.append(unescaped)
        if unescaped == current:
            break
        current = unescaped
    return tuple(views)


def line_number(text, offset):
    return text.count("\n", 0, offset) + 1


def scan_file(path, failures, root=REPO_ROOT):
    rel = path.relative_to(root).as_posix()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        failures.append(f"source-read: {rel} could not be read as UTF-8: {exc}")
        return []

    hits = []
    views = scan_views(text)
    reported = set()
    for view in views:
        for description, pattern in DENYLIST_PATTERNS:
            for match in pattern.finditer(view):
                finding = (line_number(view, match.start()), description)
                if finding in reported:
                    continue
                reported.add(finding)
                hits.append((rel, finding[0], description))
    if path.suffix.lower() == ".md":
        reported_urls = set()
        for view in views:
            for match in PERSONAL_GITHUB_URL.finditer(view):
                repo_name = match.group("repo")
                finding = (
                    line_number(view, match.start()),
                    (repo_name or ACCOUNT_SLUG).casefold(),
                )
                if finding in reported_urls:
                    continue
                reported_urls.add(finding)
                hits.append((rel, finding[0], "personal GitHub URL"))
    return hits


def main(root=REPO_ROOT):
    root = Path(root).resolve()
    files = sorted(iter_paths(root))
    if not files:
        print("No files matched publication gate scan.")
        return 1
    if root / "README.md" not in files:
        print("README.md anchor is required for publication gate scan.")
        return 1

    failures = []
    for path in files:
        for rel, line, description in scan_file(path, failures, root):
            failures.append(f"{rel}:{line}: contains {description}")

    if failures:
        for failure in sorted(set(failures)):
            print(failure)
        return 1

    print(f"PASS ({len(files)} files scanned)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
