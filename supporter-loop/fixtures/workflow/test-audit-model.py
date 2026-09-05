#!/usr/bin/env python3
"""Run the actual embedded audit expression on every standalone audit fixture."""
import pathlib
import re
import subprocess

workflow = pathlib.Path('.github/workflows/supporter-loop-reusable.yml').read_text()
match = re.search(r"divergences=\$\(jq -r --arg mode live '(.*?)' \"\$work/audit.json\"\)", workflow, re.S)
if match is None:
    raise SystemExit('Embedded reconciliation expression missing')
count = 0
for fixture in sorted(pathlib.Path('supporter-loop/fixtures/reconcile').glob('*.json')):
    # These cases exercise the shell schema gate outside the expression.
    # Checkpoint #4 full zero-send is an owner-only standalone audit, not a sweep.
    if 'incomplete' in fixture.name or 'checkpoint4' in fixture.name:
        continue
    mode = 'record-only' if 'record-only' in fixture.name else 'live'
    result = subprocess.run(['jq', '-r', '--arg', 'mode', mode, match.group(1), str(fixture)], capture_output=True, text=True)
    if result.returncode or result.stderr:
        raise SystemExit(f'FAIL embedded audit {fixture.name}: {result.stderr}')
    expected_clean = fixture.name.startswith('clean-')
    if (not result.stdout.strip()) != expected_clean:
        raise SystemExit(f'FAIL embedded audit {fixture.name}: {result.stdout!r}')
    print(f'PASS embedded audit {fixture.name}')
    count += 1
print(f'{count} embedded audit cases passed')
