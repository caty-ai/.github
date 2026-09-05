#!/usr/bin/env python3
"""Exercise the workflow's actual jq model against contract §7 transitions."""
import json
import pathlib
import re
import subprocess
import tempfile

workflow = pathlib.Path('.github/workflows/supporter-loop-reusable.yml').read_text()
models = []
for match in re.finditer(r"[^\n]*model\.jq[^\n]*<<['\"]?(\w+)['\"]?[^\n]*\n", workflow):
    delimiter = match.group(1)
    body = workflow[match.end():]
    end = re.search(r'^\s*' + re.escape(delimiter) + r'\s*$', body, re.M)
    if end:
        models.append(body[:end.start()])
if not models:
    raise SystemExit('Workflow jq model heredoc not found')
if len(set(models)) != 1:
    raise SystemExit('decide/act jq models differ')

REPO = 'caty-ai/x-collector'
ID = 42

def row(action, tier=1, result='ok', gen=1, run='1-1', ts='2026-01-01T00:00:00Z', mode='live', **extra):
    return dict(schema=1, ts=ts, run_id=run, repo=REPO, event='watch', actor='supporter',
                actor_id=ID, tier=tier, subject='', action=action, mode=mode,
                result=result, dedup_key=f'{REPO}:{tier}:{ID}', gen=gen, **extra)

cases = [
    ('empty starts generation 1', [], 'generation($repo;$id)', 1),
    ('failed revoke never closes', [row('invite'), row('revoke', 0, 'error-403')], 'generation($repo;$id)', 1),
    ('same run revoke and cancel close once', [row('invite'), row('revoke', 0, run='2-1'), row('cancel-invite', 0, run='2-1')], 'generation($repo;$id)', 2),
    ('rotation duplicates do not double-close', [row('revoke', 0, run='2-1')] * 2, 'generation($repo;$id)', 2),
    ('expired only rearms invitation', [row('invite'), row('cancel-invite', 0, 'expired', run='2-1')], 'generation($repo;$id)', 1),
    ('no-op revoke closes', [row('invite'), row('revoke', 0, 'noop', run='2-1')], 'generation($repo;$id)', 2),
    ('failed tier upgrade does not achieve', [row('invite'), row('comment', 3, 'error-500')], 'achieved($repo;$id)', 1),
    ('skip never raises achieved tier', [row('invite'), row('skip', 3, 'already-3')], 'achieved($repo;$id)', 1),
    ('rehearsal cannot raise live achieved tier', [row('invite'), row('would-comment', 2, mode='record-only')], 'achieved($repo;$id)', 1),
    ('backfilled live entitlement counts', [row('comment', 2, result='ok-backfill')], 'achieved($repo;$id)', 2),
    ('closed generation has no active entitlement', [row('invite'), row('revoke', 0, run='2-1')], 'achieved($repo;$id)', 0),
    ('new event reopens next generation', [row('invite'), row('revoke', 0, run='2-1'), row('comment', 2, gen=2, run='3-1')], 'achieved($repo;$id)', 2),
    ('rehearsal never satisfies live delivery', [row('would-invite')], 'delivered($repo;$id;1;"invite")', False),
    ('rehearsal deduplicates itself', [row('would-invite')], 'delivered($repo;$id;1;"would-invite")', True),
    ('error action retries', [row('comment', 2, 'error-500')], 'delivered($repo;$id;2;"comment")', False),
    ('successful sibling does not suppress retry', [row('comment', 2), row('supporters-append', 2, 'error-500')], 'delivered($repo;$id;2;"supporters-append")', False),
    ('already marker counts delivered', [row('comment', 2, 'already-2')], 'delivered($repo;$id;2;"comment")', True),
    ('expired rearms invitation', [row('invite'), row('cancel-invite', 0, 'expired', ts='2026-01-09T00:00:00Z')], 'delivered($repo;$id;1;"invite")', False),
    ('expired preserves comment', [row('comment', 2), row('cancel-invite', 0, 'expired', ts='2026-01-09T00:00:00Z')], 'delivered($repo;$id;2;"comment")', True),
    ('successful reinvite ends rearm', [row('invite'), row('cancel-invite', 0, 'expired', ts='2026-01-09T00:00:00Z'), row('invite', ts='2026-01-10T00:00:00Z')], 'delivered($repo;$id;1;"invite")', True),
    ('same-second reinvite ends rearm', [row('invite'), row('cancel-invite', 0, 'expired', ts='2026-01-09T00:00:00Z'), row('invite', ts='2026-01-09T00:00:00Z')], 'delivered($repo;$id;1;"invite")', True),
    ('same-second expiry rearms prior invite', [row('invite'), row('cancel-invite', 0, 'expired')], 'delivered($repo;$id;1;"invite")', False),
    ('delivery requires the exact frozen dedup key', [dict(row('invite'), dedup_key='wrong:key')], 'delivered($repo;$id;1;"invite")', False),
    ('rename preserves delivery identity', [dict(row('invite'), actor='old-login')], 'delivered($repo;$id;1;"invite")', True),
    ('other actor closure does not affect generation', [dict(row('revoke'), actor_id=43)], 'generation($repo;$id)', 1),
    ('other repository closure does not affect generation', [dict(row('revoke'), repo='caty-ai/other')], 'generation($repo;$id)', 1),
]
with tempfile.TemporaryDirectory(prefix='supporter-model-', dir=pathlib.Path(__file__).resolve().parent) as scratch:
    model = pathlib.Path(scratch, 'test.jq')
    mode_cases = [(name, ledger, expression, expected, 'live') for name, ledger, expression, expected in cases]
    mode_cases += [('record-only ignores live upgrade', [row('would-invite', mode='record-only'), row('comment', 2)], 'achieved($repo;$id)', 1, 'record-only'),
                   ('record-only honors rehearsal upgrade', [row('invite'), row('would-comment', 2, mode='record-only')], 'achieved($repo;$id)', 2, 'record-only')]
    for name, ledger, expression, expected, mode in mode_cases:
        model.write_text(models[0] + '\n' + expression + '\n')
        result = subprocess.run(['jq', '--arg', 'mode', mode, '--arg', 'repo', REPO, '--argjson', 'id', str(ID), '-f', str(model)],
                                input=json.dumps(ledger), capture_output=True, text=True)
        if result.returncode:
            raise SystemExit(f'FAIL {name}: {result.stderr}')
        actual = json.loads(result.stdout)
        if actual != expected:
            raise SystemExit(f'FAIL {name}: expected {expected!r}, got {actual!r}')
        print(f'PASS {name}')
print(f'{len(mode_cases)} contract transition cases passed')

render = re.search(r"jq -sr -L \"\$work\" [^\n]*'(.*?)' \"\$derive\"", workflow, re.S)
if render is None:
    raise SystemExit('Actual SUPPORTERS.md projection missing')
expression = models[0] + render.group(1).replace('include "model";', '')
render_cases = [
    ('rehearsal-only omitted from live projection', [row('would-comment', 2, mode='record-only')], '@supporter', False),
    ('rehearsal upgrade leaves live tier1', [row('invite'), row('would-comment', 2, mode='record-only')], '@supporter | 1 |', True),
    ('projected success raises tier after failed comment', [row('invite'), row('comment', 3, 'error-500'), row('supporters-append', 3)], '@supporter | 3 |', True),
    ('closed identity omitted', [row('invite'), row('revoke', 0)], '@supporter', False),
    ('renamed identity remains one row', [row('invite'), dict(row('comment', 2), actor='renamed')], '@renamed | 2 |', True),
    ('family never listed', [dict(row('invite'), actor='CaTy2')], '@CaTy2', False),
]
for name, ledger, fragment, present in render_cases:
    result = subprocess.run(['jq', '-sr', '--arg', 'mode', 'live', '--arg', 'repo', REPO, expression],
                            input='\n'.join(json.dumps(item) for item in ledger), capture_output=True, text=True)
    if result.returncode or (fragment in result.stdout) != present:
        raise SystemExit(f'FAIL {name}: {result.stderr or result.stdout}')
    if 'renamed' in name and result.stdout.count('@') != 1:
        raise SystemExit('FAIL renamed identity duplicated')
    print(f'PASS actual SUPPORTERS.md model: {name}')
print(f'{len(render_cases)} derived-file cases passed')

# Execute the actual Bash regenerator, including header validation and Contents payload.
import base64
import os
import textwrap

function = re.search(r'^          regenerate\(\) \{\n.*?^          \}', workflow, re.M | re.S)
assert function, 'Actual regenerate function missing'
header_sample = pathlib.Path(__file__).with_name('SUPPORTERS.header.sample.md').read_bytes()
error = '::error::SUPPORTERS.header.md missing or malformed in reward repo (child #1); regeneration skipped'
double = r'''
get() {
  [ "$1" = "$LEDGER_TOKEN" ] || return 1
  printf '%s\n' "$2" >> "$work/gets"
  case "$2" in
    "repos/$REWARD_REPO/contents/SUPPORTERS.header.md")
      code="$HEADER_STATUS"; cp "$work/header.json" "$3" ;;
    "repos/$REWARD_REPO/contents/SUPPORTERS.md") code=404; printf '{}' > "$3" ;;
    *) return 1 ;;
  esac
}
mutate() {
  [ "$1" = "$LEDGER_TOKEN" ] && [ "$2" = PUT ] &&
    [ "$3" = "repos/$REWARD_REPO/contents/SUPPORTERS.md" ] || return 1
  cp "$4" "$work/published.json"
  code=200
}
'''
with tempfile.TemporaryDirectory(prefix='supporter-render-', dir=pathlib.Path(__file__).resolve().parent) as directory:
    root = pathlib.Path(directory)
    (root / 'model.jq').write_text(models[0])
    script = 'set -euo pipefail\n' + double + textwrap.dedent(function.group()) + '\nregenerate\n'
    sample_row = dict(row('invite', ts='2026-09-06T00:00:00Z'), actor='example-supporter')
    variants = [
        ('child #1 byte identity', 200, header_sample, True),
        ('header without final LF', 200, header_sample.rstrip(b'\n'), True),
        ('header trailing LF normalization', 200, header_sample + b'\n\n', True),
        ('404 header', 404, b'', False),
        ('wrong last line', 200, header_sample + b'wrong\n', False),
        ('empty header', 200, b'', False),
        ('newline-only header', 200, b'\n\n', False),
    ]
    reference = pathlib.Path('.omc-brief/child1-SUPPORTERS.md')
    reference_header = pathlib.Path('.omc-brief/child1-SUPPORTERS.header.md')
    if reference.exists() and reference_header.exists():
        variants.append(('local child #1 byte identity', 200, reference_header.read_bytes(), True))
    for name, status, header, success in variants:
        for output in ('SUPPORTERS.md', 'published.json', 'gets'):
            (root / output).unlink(missing_ok=True)
        (root / 'header.json').write_text(json.dumps(dict(content=base64.b64encode(header).decode())))
        (root / 'ledger.ndjson').write_text(json.dumps(sample_row) + '\n')
        env = dict(os.environ, work=str(root), ledger=str(root / 'ledger.ndjson'), MODE='live',
                   GITHUB_REPOSITORY=REPO, REWARD_REPO='caty-ai/ask-ai-widget',
                   LEDGER_TOKEN='fixture-ledger', HEADER_STATUS=str(status))
        result = subprocess.run(['/bin/bash', '-c', script], env=env, capture_output=True, text=True)
        assert (result.returncode == 0) == success, (name, result.stdout, result.stderr)
        assert not result.stderr, (name, result.stderr)
        gets = (root / 'gets').read_text().splitlines()
        assert gets[0] == 'repos/caty-ai/ask-ai-widget/contents/SUPPORTERS.header.md', gets
        if success:
            rendered = base64.b64decode(json.loads((root / 'published.json').read_text())['content'])
            expected = header.rstrip(b'\n') + b'\n\n| Supporter | Tier | Since |\n| --- | --- | --- |\n| @example-supporter | 1 | 2026-09-06 |\n'
            assert rendered == expected, name
            assert (root / 'SUPPORTERS.md').read_bytes() == expected
            if name == 'local child #1 byte identity':
                subprocess.run(['cmp', str(root / 'SUPPORTERS.md'), str(reference)], check=True)
                print('PASS cmp rendered SUPPORTERS.md == local child #1 original (exit 0)')
        else:
            assert result.stdout.splitlines() == [error], (name, result.stdout)
            assert len(gets) == 1, gets
            assert not (root / 'published.json').exists(), name
            assert not (root / 'SUPPORTERS.md').exists(), name
        print('PASS actual regenerate: ' + name)
    # All existing projection cases also pass through the complete header + table render.
    for name, ledger_rows, fragment, present in render_cases:
        (root / 'header.json').write_text(json.dumps(dict(content=base64.b64encode(header_sample).decode())))
        (root / 'ledger.ndjson').write_text('\n'.join(json.dumps(item) for item in ledger_rows))
        env['HEADER_STATUS'] = '200'
        result = subprocess.run(['/bin/bash', '-c', script], env=env, capture_output=True, text=True)
        assert result.returncode == 0, (name, result.stdout, result.stderr)
        table = subprocess.run(['jq', '-sr', '--arg', 'mode', 'live', '--arg', 'repo', REPO, expression],
                               input='\n'.join(json.dumps(item) for item in ledger_rows).encode(), capture_output=True, check=True).stdout
        assert (root / 'SUPPORTERS.md').read_bytes() == header_sample.rstrip(b'\n') + b'\n\n' + table, name
        print('PASS actual regenerate header + projection: ' + name)
    (root / 'gets').unlink()
    env['MODE'] = 'record-only'
    result = subprocess.run(['/bin/bash', '-c', script], env=env, capture_output=True, text=True)
    assert result.returncode != 0 and not (root / 'gets').exists()
    print('PASS actual regenerate: record-only refuses before GET')
