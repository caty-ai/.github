#!/usr/bin/env bash
# Offline regression guard for wrapped GitHub Contents API base64 responses.
set -euo pipefail
if [ "$#" -ne 2 ] || [ ! -f "$1" ] || [ ! -d "$2" ]; then
  echo 'usage: check-contents-decode.sh <workflow.yml> <fixtures-dir>' >&2
  exit 2
fi
decode='.content | gsub("[\\n\\r]"; "") | @base64d'
# Match the exact guard used below; inspect every occurrence, even on one line.
python3 -B - "$1" "$decode" <<'PY'
import re
import sys
from pathlib import Path

guard = re.compile(re.escape(sys.argv[2].split(" | ", 1)[1]))
bad = False
for number, line in enumerate(Path(sys.argv[1]).read_text().splitlines(), 1):
    if "@base64d" in guard.sub("", line):
        print(f"{sys.argv[1]}:{number}: unguarded base64 decode: {line.strip()}")
        bad = True
sys.exit(1 if bad else 0)
PY

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
for name in ledger baseline; do
  fixture="$2/$name-blob.json"
  case "$name" in
    ledger) expected="$2/expected/ledger.ndjson" ;;
    baseline) expected="$2/expected/baseline.json" ;;
  esac
  # -j preserves the decoded bytes, including the fixture's own final newline.
  if ! jq -ej "$decode" "$fixture" > "$work/decoded"; then
    echo "Decode failed: $fixture" >&2
    exit 1
  fi
  if ! cmp "$expected" "$work/decoded"; then
    echo "Decoded bytes differ: $fixture" >&2
    exit 1
  fi
  if jq -ej '.content | @base64d' "$fixture" > /dev/null 2> "$work/plain-error"; then
    echo "Not a regression fixture: plain base64 decode succeeded: $fixture" >&2
    exit 1
  fi
done
echo 'Contents API decode: all sites guarded; 2 fixtures byte-identical; plain decoding rejected for both'
