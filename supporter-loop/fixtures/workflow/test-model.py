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

def row(action, tier=1, result='ok', gen=1, run='1-1', ts='2026-01-01T00:00:00Z', **extra):
    return dict(schema=1, ts=ts, run_id=run, repo=REPO, event='watch', actor='supporter',
                actor_id=ID, tier=tier, subject='', action=action, mode='live',
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
    ('rehearsal contributes to achieved tier', [row('would-comment', 2)], 'achieved($repo;$id)', 2),
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
    for name, ledger, expression, expected in cases:
        model.write_text(models[0] + '\n' + expression + '\n')
        result = subprocess.run(['jq', '--arg', 'repo', REPO, '--argjson', 'id', str(ID), '-f', str(model)],
                                input=json.dumps(ledger), capture_output=True, text=True)
        if result.returncode:
            raise SystemExit(f'FAIL {name}: {result.stderr}')
        actual = json.loads(result.stdout)
        if actual != expected:
            raise SystemExit(f'FAIL {name}: expected {expected!r}, got {actual!r}')
        print(f'PASS {name}')
print(f'{len(cases)} contract transition cases passed')

render = re.search(r"jq -sr -L \"\$work\" --arg repo \"\$GITHUB_REPOSITORY\" '(.*?)' \"\$derive\"", workflow, re.S)
if render is None:
    raise SystemExit('Actual SUPPORTERS.md projection missing')
expression = models[0] + render.group(1).replace('include "model";', '')
render_cases = [
    ('projected success raises tier after failed comment', [row('invite'), row('comment', 3, 'error-500'), row('supporters-append', 3)], '@supporter | 3 |', True),
    ('closed identity omitted', [row('invite'), row('revoke', 0)], '@supporter', False),
    ('renamed identity remains one row', [row('invite'), dict(row('comment', 2), actor='renamed')], '@renamed | 2 |', True),
    ('family never listed', [dict(row('invite'), actor='CaTy2')], '@CaTy2', False),
]
for name, ledger, fragment, present in render_cases:
    result = subprocess.run(['jq', '-sr', '--arg', 'repo', REPO, expression],
                            input='\n'.join(json.dumps(item) for item in ledger), capture_output=True, text=True)
    if result.returncode or (fragment in result.stdout) != present:
        raise SystemExit(f'FAIL {name}: {result.stderr or result.stdout}')
    if 'renamed' in name and result.stdout.count('@') != 1:
        raise SystemExit('FAIL renamed identity duplicated')
    print(f'PASS actual SUPPORTERS.md model: {name}')
print(f'{len(render_cases)} derived-file cases passed')
