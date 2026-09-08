#!/usr/bin/env python3
"""Contract v2 §7/11: exercise the workflow model and actual page-order expressions."""
import json
import re
import subprocess
from pathlib import Path
import yaml

wf = yaml.safe_load(Path('.github/workflows/supporter-loop-reusable.yml').read_text())
decide = wf['jobs']['decide']['steps'][1]['run']
act = wf['jobs']['act']['steps'][1]['run']
model = re.search(r"cat > .*model.jq.*<<'JQ'\n(.*?)\nJQ", decide, re.S).group(1)
assert model == re.search(r"cat > .*model.jq.*<<'JQ'\n(.*?)\nJQ", act, re.S).group(1)
repo = 'caty-ai/x-collector'
now = 1788825600  # fixed clock, independent of host date

def row(id=42, action='invite', result='ok', ts='2026-09-08T00:00:00Z', tier=1, gen=1, run='1-1', key=None):
    return dict(schema=1, repo=repo, actor_id=id, actor='user-'+str(id), action=action, result=result,
                ts=ts, tier=tier, gen=gen, run_id=run, event='watch', mode='live', subject='',
                dedup_key=key or f'{repo}:{tier}:{id}')

def evaluate(rows, expression, mode='live'):
    r = subprocess.run(['jq', '--arg', 'mode', mode, '--arg', 'repo', repo, model+'\n'+expression],
                       input=json.dumps(rows), capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)

def ids(rows, stars=(99, 42, 7), tiers='1,2,3', mode='live'):
    return evaluate(rows, f'catchup($repo;{json.dumps(stars)};"{tiers}")|map(.actor_id)', mode)

cases = [
    ('empty burst is recovered in page order', [], [99,42,7]),
    ('delivered invite is projection repair', [row()], [99,7,42]),
    ('whole bundle already delivered', [row(),row(action='supporters-append')], [99,7]),
    ('tier key exclusion', [row(action='skip',result='excluded-family')], [99,7]),
    ('tier2 member exclusion', [row(action='skip',result='excluded-member',tier=2)], [99,7]),
    ('tier3 member exclusion', [row(action='skip',result='excluded-member',tier=3)], [99,7]),
    ('sweep key exclusion', [row(action='skip',result='excluded-bot',tier=0,key=repo+':sweep:42')], [99,7]),
    ('stop line does not self exclude', [row(action='skip',result='deferred-quota',tier=0,key=repo+':sweep:42')], [99,42,7]),
    ('error invitation retries', [row(result='error-422')], [99,42,7]),
    ('closed generation waits for event', [row(action='revoke',tier=0)], [99,7]),
    ('new event reopens after closure', [row(action='revoke',tier=0),row(gen=2,result='deferred-quota')], [99,42,7]),
    ('old generation exclusion no longer applies', [row(action='skip',result='excluded-family'),row(action='revoke',tier=0),row(gen=2,result='deferred-quota')], [99,42,7]),
    ('disabled skip is not exclusion', [row(action='skip',result='tier-disabled')], [99,42,7]),
]
for name, rows, expected in cases:
    assert ids(rows) == expected, (name,ids(rows),expected)
    print('PASS catchup '+name)
assert ids([],tiers='2,3') == []
print('PASS tier1 must be enabled')
# Two distinct expired cycles, across event and sweep paths, with rotation duplicate safety.
cycles=[row(ts='2026-08-01T00:00:00Z'), row(action='cancel-invite',tier=0,result='expired',ts='2026-08-09T00:00:00Z',run='2-1'),
        row(result='ok-catchup',ts='2026-08-10T00:00:00Z',run='3-1'),row(action='cancel-invite',tier=0,result='expired',ts='2026-08-18T00:00:00Z',run='4-1')]
assert evaluate(cycles,'exhausted($repo;42)') is True
assert evaluate(cycles[:2]*2,'exhausted($repo;42)') is False
assert evaluate([cycles[0],dict(cycles[0],run_id='other-put'),cycles[1]],'exhausted($repo;42)') is False, 'one expiry is not two completed cycles'
assert evaluate(cycles,'invite_delivered($repo;42)') is False
assert ids(cycles) == [99,7,42]
assert evaluate(cycles+[row(ts='2026-09-08T00:00:00Z')],'invite_delivered($repo;42)') is True
assert evaluate([row(result='ok-backfill',key=repo+':sweep:42')],'invite_delivered($repo;42)') is True
print('PASS rearm ordering / two-invitation bound / historical sweep-key backfill')
# Quota window fixtures: only actual successful PUT lines count, strict lower boundary.
from datetime import datetime, timezone
now=int(datetime(2026,9,8,tzinfo=timezone.utc).timestamp())
quota_rows=[row(id=1),row(id=2,result='ok-backfill'),row(id=3,result='ok-catchup'),row(id=4,result='already-1'),
            row(id=5,ts='2026-09-07T00:00:00Z'),row(id=6,ts='2026-09-07T00:00:01Z'),row(id=7,result='deferred-quota'),row(id=8,ts='2026-09-09T00:00:00Z')]
pending=[dict(invitee=dict(id=1),created_at='2026-09-08T00:00:00Z'),dict(invitee=dict(id=9),created_at='2026-09-08T00:00:00Z')]
q=evaluate(quota_rows,f'quota($repo;{json.dumps(pending)};{now})')
assert q == dict(B=5,Q=40,age_out=1),q
assert evaluate([row(id=i) for i in range(50)],f'quota($repo;[];{now})')['Q']==0
assert evaluate(quota_rows*2,f'quota($repo;{json.dumps(pending)};{now})')==q
print('PASS quota actual PUT results / already-1 excluded / pending dedup / 24h boundary / nonnegative Q / rotation copies')
# Actual stars job and decide re-emit jq source; builtin unique would sort this fixture.
pages=[[dict(id=90),dict(id=2)],[dict(id=90),dict(id=17),dict(id=2),dict(id=1)]]
for name, script, data in [('stars',wf['jobs']['stars']['steps'][0]['run'],pages),('decide',decide,[v for page in pages for v in page])]:
    expression=re.search(r"stars=\$\(jq -c '(.*?)'",script).group(1)
    r=subprocess.run(['jq','-c',expression],input=json.dumps(data),capture_output=True,text=True,check=True)
    assert json.loads(r.stdout)==[90,2,17,1],(name,r.stdout)
    print('PASS ordering across pages with duplicates: '+name)
# Real line helper shares the same namespace rule in both jobs.
for action,event,tier,key in [('invite','sweep',1,'1'),('supporters-append','sweep',1,'1'),('would-invite','sweep',1,'1'),
                             ('would-supporters-append','sweep',1,'1'),('revoke','sweep',0,'sweep'),('cancel-invite','sweep',0,'sweep'),
                             ('skip','sweep',0,'sweep'),('comment','issues',2,'2'),('skip','watch',0,'0')]:
    assert evaluate([],f'key_namespace("{action}";"{event}";{tier})')==key
print('PASS shared action-key namespace table')
# Mode parity for the same ledger when pending has no unledgered entries.
for _,rows,_ in cases:
    assert ids(rows,mode='record-only')==ids(rows)
print('PASS live / record-only candidate parity on same live ledger')
# Projection omission and restoration after rearm, with higher-tier recognition preserved.
render=re.search(r"jq -sr -L \"\$work\" [^\n]*'(.*?)' \"\$derive\"",act,re.S).group(1).replace('include "model";','')
for name,rows,present in [('expired tier1 omitted',cycles,False),('excluded unresponsive omitted',cycles+[row(action='skip',result='excluded-unresponsive',tier=0)],False),
                          ('reinvite restores without append',cycles+[row()],True),('tier2 recognition stays',cycles+[row(action='comment',tier=2)],True)]:
    r=subprocess.run(['jq','-r','--arg','mode','live','--arg','repo',repo,model+'\n'+render],input=json.dumps(rows),text=True,capture_output=True,check=True)
    assert ('@user-42' in r.stdout)==present,(name,r.stdout)
    print('PASS projection '+name)
