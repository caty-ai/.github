#!/usr/bin/env python3
"""Hash-cached markdown translation for family repos (claude-mem pattern).

Translates a repo's Japanese markdown tree into i18n/<lang>/ mirrors using the
`claude` CLI. A sha256 cache per (file, language) means only files whose source
changed since the last run are re-translated.

Layout contract:
  <repo>/docs/01-x.md            (Japanese canonical)
  <repo>/i18n/en/docs/01-x.md    (generated)
  <repo>/i18n/.translation-cache.json

The mirrored tree keeps relative links between translated files working
unchanged. Links to the repo-root README.ja.md are rewritten deterministically
to the language's README. Every output starts with a canonical-note header:
machine translation, Japanese wins on any disagreement.

Usage:
  python3 -B translate_docs.py --repo <path> [--langs en,zh,th]
      [--files "docs/*.md,templates/*.md"] [--only docs/01-milestone-loop.md]
      [--model sonnet] [--force] [--dry-run]

Requires: python3 (stdlib only) and the `claude` CLI on PATH.
"""

import argparse
import glob
import hashlib
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LANGUAGE_NAMES = {
    "en": "English",
    "zh": "Simplified Chinese",
    "th": "Thai",
}

README_FOR_LANG = {
    "en": "README.md",
    "zh": "README.zh.md",
    "th": "README.th.md",
}

# Header note injected at the top of every generated file, per language.
# {name} is the source filename, {orig} the relative path back to the original.
NOTE = {
    "en": "> **Machine translation.** The Japanese original ([{name}]({orig})) is canonical — if this page and the original disagree, the Japanese text wins.",
    "zh": "> **机器翻译。**日文原文（[{name}]({orig})）是正本 — 本页与原文不一致时，以日文为准。",
    "th": "> **แปลโดยเครื่อง** ต้นฉบับภาษาญี่ปุ่น ([{name}]({orig})) เป็นฉบับหลัก — หากหน้านี้ขัดกับต้นฉบับ ให้ยึดข้อความภาษาญี่ปุ่นเป็นหลัก",
}

PROMPT = """You are a precise technical translator. Translate the following Markdown document from Japanese to {language}.

Hard rules:
- Preserve the Markdown structure EXACTLY: same number of headings at the same levels, same number of fenced code blocks, same tables, same list structure, same horizontal rules, same HTML comments and anchors.
- Do NOT translate or alter: fenced code block contents, inline code spans, rule IDs (L0-1, L1-7, FP-9, E-3, B-5 and the like), URLs, file paths, link targets in parentheses, HTML tags and comments.
- Translate link TEXT but never link TARGETS.
- Keep the tone plain and confident, matching a well-written engineering handbook.
- Technical terms that the document itself keeps in English (Issue, PR, worktree, merge, WIP, HOLD, rebase, fail-open ...) stay in English.
- Output ONLY the translated Markdown document. No preamble, no code fence around the whole document, no commentary.

Document:
{content}"""


def sha16(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def load_cache(path: Path) -> dict:
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            print(f"WARN: cache at {path} is invalid JSON; starting fresh", file=sys.stderr)
    return {}


def structural_signature(text: str) -> dict:
    """Count headings, code fences, and relative links — translation must keep all three."""
    in_fence = False
    headings = 0
    fences = 0
    for line in text.splitlines():
        if line.startswith("```"):
            fences += 1
            in_fence = not in_fence
            continue
        if not in_fence and re.match(r"^#{1,6} ", line):
            headings += 1
    rel_links = len(re.findall(r"\]\((?!https?://|#)[^)]+\)", text))
    first = next((l for l in text.splitlines() if l.strip()), "")
    m = re.match(r"^(#{1,6} |> |[-*] |\||```|<)", first)
    first_shape = m.group(1).strip() if m else "text"
    return {"headings": headings, "fences": fences, "rel_links": rel_links,
            "first_shape": first_shape}


def rewrite_readme_links(text: str, lang: str, rel: str) -> str:
    """Point README.ja.md links at the language's README, wherever the file sits.

    Handles optional leading ../ runs, #anchors, and "title" suffixes. The
    root prefix is computed from the output file's depth under i18n/<lang>/.
    """
    readme = README_FOR_LANG[lang]
    root = "../" * (2 + len(Path(rel).parent.parts))
    pattern = re.compile(r'\]\((?:\.\./)*README\.ja\.md(#[^)\s"]*)?(\s+"[^"]*")?\)')

    def sub(m: re.Match) -> str:
        return f"]({root}{readme}{m.group(1) or ''}{m.group(2) or ''})"

    return pattern.sub(sub, text)


def translate_once(content: str, lang: str, model: str, timeout: int) -> str:
    prompt = PROMPT.format(language=LANGUAGE_NAMES[lang], content=content)
    result = subprocess.run(
        ["claude", "--model", model, "-p", prompt],
        capture_output=True, encoding="utf-8", timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI failed ({result.returncode}): {result.stderr[:500]}")
    out = result.stdout.strip()
    # Strip a whole-document code fence if the model added one despite
    # instructions — but only when the source itself does not start with a
    # fence, so fence-first documents are never mangled.
    if (out.startswith("```") and out.endswith("```")
            and not content.lstrip().startswith("```")):
        body = out.split("\n", 1)[1] if "\n" in out else ""
        out = body.rsplit("```", 1)[0].strip()
    # Strip any preamble the model added before the document: when the source
    # starts with a heading, drop output lines until the first heading.
    if content.lstrip().startswith("#"):
        lines = out.splitlines()
        for i, line in enumerate(lines):
            if re.match(r"^#{1,6} ", line):
                out = "\n".join(lines[i:]).strip()
                break
    return out


def process_file(repo: Path, rel: str, lang: str, model: str, cache: dict,
                 force: bool, dry_run: bool, timeout: int) -> str:
    src_path = repo / rel
    out_path = repo / "i18n" / lang / rel
    content = src_path.read_text(encoding="utf-8")
    h = sha16(content)
    entry = cache.setdefault(rel, {"translations": {}})
    entry.setdefault("translations", {})
    entry["source_hash"] = h
    prev = entry["translations"].get(lang)
    if not force and prev and prev.get("hash") == h and out_path.exists():
        return "cached"
    if dry_run:
        return "stale"

    # i18n/<lang>/<rel parents> -> repo root, then down to the original.
    depth_orig = "../" * (2 + len(Path(rel).parent.parts))
    note = NOTE[lang].format(name=Path(rel).name, orig=f"{depth_orig}{rel}")

    # README link rewrites change no counts (link count is target-agnostic),
    # so the source signature is compared as-is.
    src_sig = structural_signature(content)
    last_err = ""
    for attempt in (1, 2):
        try:
            translated = translate_once(content, lang, model, timeout)
        except (RuntimeError, subprocess.TimeoutExpired, OSError) as e:
            last_err = f"{type(e).__name__}: {str(e)[:300]} (attempt {attempt})"
            print(f"  RETRY {rel} [{lang}]: {last_err}", file=sys.stderr)
            time.sleep(5)
            continue
        translated = rewrite_readme_links(translated, lang, rel)
        # Gross-truncation guard: the structural counts can survive a badly
        # shortened body, so also require a sane length ratio vs the source.
        ratio = len(translated) / max(1, len(content))
        if not 0.35 <= ratio <= 4.0:
            last_err = f"length ratio {ratio:.2f} outside [0.35, 4.0] (attempt {attempt})"
            print(f"  RETRY {rel} [{lang}]: {last_err}", file=sys.stderr)
            time.sleep(2)
            continue
        got_sig = structural_signature(translated)
        if got_sig == src_sig:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = out_path.with_suffix(out_path.suffix + ".tmp")
            tmp.write_text(note + "\n\n" + translated + "\n", encoding="utf-8")
            tmp.replace(out_path)
            entry["translations"][lang] = {
                "hash": h,
                "translated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
                "model": model,
            }
            return "translated"
        last_err = f"structure mismatch src={src_sig} got={got_sig} (attempt {attempt})"
        print(f"  RETRY {rel} [{lang}]: {last_err}", file=sys.stderr)
        time.sleep(2)
    return f"failed: {last_err}"


def main() -> int:
    ap = argparse.ArgumentParser(description="Translate a repo's markdown tree with a hash cache")
    ap.add_argument("--repo", required=True, type=Path)
    ap.add_argument("--files", default="docs/*.md,templates/*.md")
    ap.add_argument("--langs", default="en,zh,th")
    ap.add_argument("--only", default=None, help="single relative path to process")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--force", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    repo = args.repo.resolve()
    langs = [l.strip() for l in args.langs.split(",") if l.strip()]
    for lang in langs:
        if lang not in LANGUAGE_NAMES:
            print(f"ERROR: unsupported language '{lang}'", file=sys.stderr)
            return 2

    if args.only:
        rels = [args.only]
    else:
        rels = []
        for pattern in args.files.split(","):
            rels.extend(sorted(
                str(Path(p).relative_to(repo))
                for p in glob.glob(str(repo / pattern.strip()))
            ))
    if not rels:
        print("ERROR: no source files matched", file=sys.stderr)
        return 2

    cache_path = repo / "i18n" / ".translation-cache.json"
    cache = load_cache(cache_path)
    failed = []
    for rel in rels:
        for lang in langs:
            status = process_file(repo, rel, lang, args.model, cache,
                                  args.force, args.dry_run, args.timeout)
            print(f"{status:>10}  {rel} [{lang}]", flush=True)
            if status.startswith("failed"):
                failed.append((rel, lang))
            if not args.dry_run:
                cache_path.parent.mkdir(parents=True, exist_ok=True)
                cache_path.write_text(json.dumps(cache, indent=2, ensure_ascii=False) + "\n",
                                      encoding="utf-8")

    if failed:
        print(f"\n{len(failed)} failed: {failed}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
