#!/usr/bin/env bash
# CONTRACT §5.3: one violating NDJSON line is counted once, in either direction.
set -euo pipefail
if [ "$#" -eq 0 ]; then
  echo 'usage: check-ledger.sh <ndjson files...>' >&2
  exit 2
fi
count=0
for file in "$@"; do
  [ -r "$file" ] || { echo "Unreadable ledger: $file" >&2; exit 2; }
  while IFS= read -r line || [ -n "$line" ]; do
    # Invalid JSON, unknown modes/actions and non-object records fail closed too.
    if ! printf '%s\n' "$line" | jq -se '
      length == 1 and (.[0] | type == "object" and
      ((.mode == "record-only" and (.action | IN("would-invite", "would-comment", "would-supporters-append", "would-revoke", "would-cancel-invite", "skip"))) or
       (.mode == "live" and (.action | IN("invite", "comment", "supporters-append", "revoke", "cancel-invite", "skip")))))
    ' >/dev/null 2>&1; then
      count=$((count + 1))
    fi
  done < "$file"
done
printf '%s\n' "$count"
[ "$count" -eq 0 ]
