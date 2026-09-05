#!/usr/bin/env python3
"""Offline execution of the actual decide run block, with fail-closed API doubles."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import yaml

# Invoked through temporary curl/gh symlinks. Unknown requests are fatal.
if Path(sys.argv[0]).name in ('curl', 'gh'):
    args = sys.argv[1:]
    root = Path(os.environ['MOCK_STATE'])
    name = Path(sys.argv[0]).name
    if name == 'gh':
        endpoint = next((x for x in args if x.startswith('repos/')), '')
        config = json.loads((root / 'mock-config.json').read_text())
        if '/contents/ledger?' in endpoint:
            data = [dict(name=p.name, type='file') for p in root.iterdir() if p.suffix == '.ndjson' or p.name.startswith('baseline-')]
        elif '/actions/runs?' in endpoint:
            runs = [] if 'status=failure' in endpoint else [dict(path='.github/workflows/supporter-loop.yml', created_at='2026-01-01T00:00:00Z')]
            data = dict(total_count=len(runs), workflow_runs=runs)
        elif '/stargazers?' in endpoint:
            data = config['stargazers']
        elif '/collaborators?' in endpoint or '/issues/comments?' in endpoint:
            data = []
        else:
            raise SystemExit('UNEXPECTED gh request: ' + endpoint)
        print(json.dumps([data]))
    else:
        url = next((x for x in args if x.startswith('https://')), '')
        output = Path(args[args.index('-o') + 1])
        method = args[args.index('-X') + 1] if '-X' in args else 'GET'
        prefix = 'https://api.github.com/repos/caty-ai/ask-ai-widget/contents/ledger/'
        if not url.startswith(prefix):
            if method != 'GET':
                raise SystemExit('UNEXPECTED nonledger mutation: ' + method + ' ' + url)
            if url.endswith('/invitations'):
                code, response = '403', dict(message='Forbidden')
            elif url == 'https://api.github.com/repos/caty-ai/ask-ai-widget/contents/ledger' or url.endswith('/collaborators?per_page=1'):
                code, response = '200', []
            elif url in ('https://api.github.com/repos/caty-ai/ask-ai-widget', 'https://api.github.com/repos/caty-ai/x-collector'):
                code, response = '200', dict(has_discussions=False)
            else:
                raise SystemExit('UNEXPECTED curl request: ' + method + ' ' + url)
            output.write_text(json.dumps(response))
            print(code, end='')
            raise SystemExit(0)
        relative = url[len(prefix):]
        if '/' in relative or not relative.endswith(('.ndjson', '.json')):
            raise SystemExit('UNEXPECTED ledger path: ' + relative)
        path = root / relative
        if method == 'GET':
            code = '200' if path.exists() else '404'
            response = dict(sha='fixture-sha', content=base64.b64encode(path.read_bytes()).decode()) if path.exists() else dict(message='Not Found')
        elif method == 'PUT':
            assert relative.endswith('.ndjson'), 'Only ledger writes allowed'
            payload = json.loads(Path(args[args.index('--data-binary') + 1].lstrip('@')).read_text())
            response = dict(content=dict(sha='fixture-sha'))
            code = '200' if path.exists() else '201'
            assert payload['message'].startswith('supporter-loop: ') and len(payload['message'].split()) == 4, payload['message']
            assert payload['committer'] == dict(name='supporter-loop[bot]', email='supporter-loop@caty-ai.noreply')
            if os.environ.get('MOCK_CAS_CONFLICT') == '1' and not (root / 'conflict-used').exists():
                (root / 'conflict-used').touch()
                code, response = '409', dict(message='sha conflict')
            else:
                path.write_bytes(base64.b64decode(payload['content']))
        else:
            raise SystemExit('UNEXPECTED mutation: ' + method)
        output.write_text(json.dumps(response))
        print(code, end='')
    raise SystemExit(0)

workflow = yaml.safe_load(Path('.github/workflows/supporter-loop-reusable.yml').read_text())
steps = workflow['jobs']['decide']['steps']
validate = steps[0]['run']
script = next(s['run'] for s in steps if s.get('id') == 'decide')
REPO = 'caty-ai/x-collector'
KEYS = ['schema', 'ts', 'run_id', 'repo', 'event', 'actor', 'actor_id', 'tier', 'subject', 'action', 'mode', 'result', 'dedup_key', 'gen']

def execute(event, payload, mode='record-only', tiers='1,2,3', prior=None, cas_conflict=False, sweep=False, stargazers=None, expected_error=False):
    with tempfile.TemporaryDirectory(prefix='supporter-decide-', dir=Path(__file__).resolve().parent) as directory:
        root = Path(directory)
        mock_bin = root / 'bin'
        mock_bin.mkdir()
        state = root / 'state'
        state.mkdir()
        (state / 'mock-config.json').write_text(json.dumps(dict(stargazers=stargazers or [])))
        if sweep:
            (state / 'baseline-2026-01-01.json').write_text(json.dumps(dict(collaborators=[], invitations=[])))
        launcher = mock_bin / 'double'
        launcher.write_text('#!' + sys.executable + '\n' + Path(__file__).read_text())
        launcher.chmod(0o700)
        for command in ('curl', 'gh'):
            (mock_bin / command).symlink_to(launcher)
        ledger = state / 'caty-ai--x-collector.ndjson'
        if prior:
            ledger.write_text(''.join(json.dumps(row) + '\n' for row in prior))
        event_file = root / 'event.json'
        event_file.write_text(json.dumps(payload))
        output = root / 'output'
        output.touch()
        env = dict(os.environ, PATH=str(mock_bin) + os.pathsep + os.environ['PATH'], MOCK_STATE=str(state),
                   MOCK_CAS_CONFLICT='1' if cas_conflict else '0',
                   RUNNER_TEMP=str(root), GITHUB_EVENT_PATH=str(event_file), GITHUB_OUTPUT=str(output),
                   GITHUB_REPOSITORY=REPO, GITHUB_RUN_ID='1234', GITHUB_RUN_ATTEMPT='2',
                   MODE=mode, REWARD_REPO='caty-ai/ask-ai-widget', TIERS_ENABLED=tiers, SWEEP='true' if sweep else 'false', EXPIRY_DATES='{}',
                   EVENT_NAME=event, RUN_KEY='1234-2', GH_TOKEN='fixture-source', LEDGER_TOKEN='fixture-ledger', LEDGER_EXPIRES='')
        result = subprocess.run(['/bin/bash', '-c', validate + '\n' + script], env=env, capture_output=True, text=True)
        if bool(result.returncode) != expected_error:
            raise AssertionError(f'{event}: exit {result.returncode}\n{result.stdout}\n{result.stderr}')
        assert not result.stderr, result.stderr
        if expected_error:
            assert '::error::' in result.stdout, result.stdout
        if cas_conflict:
            assert (state / 'conflict-used').exists()
        rows = [json.loads(line) for line in ledger.read_text().splitlines()] if ledger.exists() else []
        fresh = rows[len(prior or []):]
        for row in fresh:
            assert list(row) == KEYS, list(row)
            assert row['run_id'] == '1234-2'
            assert row['repo'] == REPO
            assert row['mode'] == mode
            assert row['action'] == 'skip' or row['action'].startswith('would-')
            assert 'fixture-' not in json.dumps(row)
        return fresh, rows, output.read_text()

user = dict(id=42, login='external-supporter', type='User')
owner = dict(id=7, login='caty-ai', type='Organization')
repo = dict(full_name=REPO, owner=owner)

def payload(event, actor=None, assoc='NONE', merged=True):
    actor = actor or user
    base = dict(repository=repo, sender=dict(id=999, login='merger', type='User'))
    if event == 'watch':
        base.update(action='started', sender=actor)
    else:
        key, action, segment = {'issues': ('issue', 'opened', 'issues'), 'discussion': ('discussion', 'created', 'discussions'), 'pull_request_target': ('pull_request', 'closed', 'pull')}[event]
        base.update(action=action)
        base[key] = dict(user=actor, author_association=assoc, number=5, html_url=f'https://github.com/{REPO}/{segment}/5', merged=merged,
                         title='$(touch SHOULD_NOT_EXIST)', body='actor body must never enter ledger')
    return base

for event, tier in [('watch', 1), ('issues', 2), ('discussion', 2), ('pull_request_target', 3)]:
    fresh, prior, output = execute(event, payload(event))
    assert fresh and all(r['actor_id'] == 42 for r in fresh), fresh
    assert any(r['action'] == 'would-invite' for r in fresh), fresh
    assert sum(r['action'] == 'would-supporters-append' for r in fresh) == 1, fresh
    assert max(r['tier'] for r in fresh) == tier, fresh
    assert all('SHOULD_NOT_EXIST' not in json.dumps(r) and 'actor body' not in json.dumps(r) for r in fresh)
    second, _, _ = execute(event, payload(event), prior=prior)
    assert second and all(r['action'] == 'skip' for r in second), second
    assert len(second) == len(fresh), ('one skip per attempted action', fresh, second)
    print('PASS actual decide actor/tier/ledger/dedup: ' + event)

for label, actor, assoc, expected in [
    ('case-insensitive family', dict(user, login='CaTy2'), 'NONE', 'excluded-family'),
    ('bot type', dict(user, type='Bot'), 'NONE', 'excluded-bot'),
    ('bot suffix', dict(user, login='service[bot]'), 'NONE', 'excluded-bot'),
    ('organization', dict(user, type='Organization'), 'NONE', 'excluded-org'),
    ('member', user, 'MEMBER', 'excluded-member'),
    ('owner association', user, 'OWNER', 'excluded-member'),
    ('workflow identity', dict(user, login='github-actions[bot]'), 'NONE', None),
]:
    fresh, _, _ = execute('issues', payload('issues', actor, assoc))
    assert len(fresh) == 1 and fresh[0]['action'] == 'skip', fresh
    assert fresh[0]['result'] == expected if expected else fresh[0]['result'].startswith('excluded-'), fresh
    print('PASS actual decide exclusion: ' + label)
fresh, _, _ = execute('issues', payload('issues'), tiers='1,3')
assert len(fresh) == 1 and fresh[0]['result'] == 'tier-disabled', fresh
print('PASS actual decide disabled tier')
fresh, _, _ = execute('watch', payload('watch'), cas_conflict=True)
assert len(fresh) == 2, fresh
print('PASS actual decide CAS conflict reread and retry')
print('Actual decide offline cases passed')

# Actual reduced sweep: stale rehearsals never re-arm, and entitlement/id gates hold.
_, initial, _ = execute('watch', payload('watch'))
for label, history, stars, expect_revoke, bad in [
    ('unstarred tier1 would-revoke only', initial, [], True, False),
    ('still-starring numeric ID protected across rename', initial, [dict(id=42, login='renamed')], False, False),
    ('tier2 never revoked on unstar', initial + [dict(initial[-1], action='would-comment', tier=2, dedup_key=REPO + ':2:42')], [], False, False),
    ('tier3 never revoked on unstar', initial + [dict(initial[-1], action='would-comment', tier=3, dedup_key=REPO + ':3:42')], [], False, False),
    ('malformed stargazer data fails closed', initial, [dict(login='missing-id')], False, True),
]:
    fresh, _, _ = execute('schedule', dict(repository=repo), prior=history, sweep=True, stargazers=stars, expected_error=bad)
    assert all(r['action'] != 'would-cancel-invite' for r in fresh), fresh
    assert any(r['action'] == 'would-revoke' for r in fresh) == expect_revoke, fresh
    print('PASS actual reduced sweep: ' + label)
print('Actual reduced sweep offline cases passed')
