# translate — hash-cached doc translation for family repos

Translates a repo's Japanese markdown tree (docs/, templates/) into `i18n/<lang>/` mirrors with the `claude` CLI, following the pattern popularized by [claude-mem](https://github.com/thedotmack/claude-mem): a sha256 cache per (file, language) so only files whose source changed get re-translated.

## Usage

```bash
# See what would be (re)translated
python3 -B tools/translate/translate_docs.py --repo ~/path/to/repo --dry-run

# Translate everything stale into en/zh/th
python3 -B tools/translate/translate_docs.py --repo ~/path/to/repo

# One file, one language
python3 -B tools/translate/translate_docs.py --repo ~/path/to/repo \
  --only docs/why-issue-first.md --langs en
```

## What it guarantees

- **Mirrored layout** — `docs/x.md` → `i18n/en/docs/x.md`, so relative links between translated files keep working untouched. Links to `README.ja.md` are rewritten deterministically to the language's README.
- **Canonical note** — every generated file starts with a per-language header: machine translation, the Japanese original is canonical and wins on any disagreement.
- **Structural check** — heading count, code-fence count, and relative-link count must match the source, or the file is retried once and then reported failed. A failed file is never written.
- **Cache** — `i18n/.translation-cache.json` (committed in the target repo) records source hashes; unchanged files are skipped. `--force` overrides.

## Requirements

`python3` (stdlib only) and the `claude` CLI on PATH. No API key handling here — the CLI's own session is used.
