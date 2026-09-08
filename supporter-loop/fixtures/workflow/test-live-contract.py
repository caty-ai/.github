#!/usr/bin/env python3
"""Run actual act helpers and event/catch-up blocks with local, fail-closed API doubles."""
import base64
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
import yaml

source = Path('.github/workflows/supporter-loop-reusable.yml').read_text()
wf = yaml.safe_load(source)
act = wf['jobs']['act']['steps'][1]['run']
prefix, main = act.split('read_ledger\nif [ "$SWEEP" != true ]; then', 1)
event_block = 'if [ "$SWEEP" != true ]; then' + main.split('sweep_cleanup() {', 1)[0]
catchup_block = '# §11 step 4b:' + act.split('# §11 step 4b:', 1)[1]
repo = 'caty-ai/x-collector'
now = int(datetime(2026,9,8,tzinfo=timezone.utc).timestamp())
fixture_dir = Path(__file__).resolve().parent

def row(id=42, action='invite', result='ok', ts='2026-09-08T00:00:00Z', tier=1, run='1-1', key=None):
    return dict(schema=1, ts=ts, run_id=run, repo=repo, event='watch', actor='user-'+str(id), actor_id=id,
                tier=tier, subject='', action=action, mode='live', result=result, dedup_key=key or f'{repo}:{tier}:{id}', gen=1)

clock = r'''
date() {
  case "$*" in
    '-u +%s') cat "$SWEEP_CLOCK_FILE" ;;
    '-u +%Y-%m-%dT%H:%M:%SZ') echo 2026-09-08T00:00:00Z ;;
    '-u -d '*) python3 -B -c 'import datetime,sys; print(int(datetime.datetime.fromisoformat(sys.argv[1].replace("Z","+00:00")).timestamp()))' "$3" ;;
    *) command date "$@" ;;
  esac
}
sleep() {
  printf 'WAIT %s\n' "$1" >> "$RUNNER_TEMP/trace"
  echo "$(( $(cat "$SWEEP_CLOCK_FILE") + $1 ))" > "$SWEEP_CLOCK_FILE"
}
'''
doubles = r'''
read_ledger() {
  echo READ_LEDGER >> "$RUNNER_TEMP/trace"
  cp "$RUNNER_TEMP/api-ledger" "$ledger"
}
get() {
  local endpoint="$2" target="$3" id
  echo "GET $endpoint" >> "$RUNNER_TEMP/trace"
  code=200
  case "$endpoint" in
    user/*)
      id="${endpoint#user/}"
      jq --arg id "$id" '.[$id] // {id:($id|tonumber),login:("user-"+$id),type:"User"}' "$RUNNER_TEMP/identities.json" > "$target" ;;
    "repos/$REWARD_REPO/collaborators/"*) code=404; echo '{}' > "$target" ;;
    "repos/$REWARD_REPO/contents/SUPPORTERS.header.md")
      jq -n --rawfile header "$RUNNER_TEMP/header" '{content:($header|@base64)}' > "$target" ;;
    "repos/$REWARD_REPO/contents/SUPPORTERS.md")
      if [ -f "$RUNNER_TEMP/published" ]; then
        jq -n --rawfile body "$RUNNER_TEMP/published" '{sha:"supporter-sha",size:($body|utf8bytelength),content:($body|@base64)}' > "$target"
      else code=404; echo '{}' > "$target"; fi ;;
    "repos/$REWARD_REPO/contents/ledger/manual-allowlist.json"|"repos/$REWARD_REPO/contents/ledger/manual-markers-allowlist.json")
      code=404; echo '{}' > "$target" ;;
    "repos/$REWARD_REPO/contents/ledger/$base.sweep-state.json")
      if [ -f "$RUNNER_TEMP/previous-state" ]; then
        jq -n --rawfile state "$RUNNER_TEMP/previous-state" '{sha:"state-sha",content:($state|@base64)}' > "$target"
      else code=404; echo '{}' > "$target"; fi ;;
    *) echo "UNEXPECTED GET $endpoint" >&2; return 1 ;;
  esac
}
pages() {
  [ "$1" = "$ADMIN_TOKEN" ] && [ "$2" = "repos/$REWARD_REPO/invitations?per_page=100" ] || return 1
  cp "$RUNNER_TEMP/pending.json" "$3"
}
append() {
  pace_write
  echo "WRITE $(cat "$SWEEP_CLOCK_FILE") APPEND $(jq -r '.action+" "+.result+" "+(.actor_id|tostring)' <<< "$1")" >> "$RUNNER_TEMP/trace"
  printf '%s\n' "$1" >> "$RUNNER_TEMP/api-ledger"
  printf '%s\n' "$1" >> "$ledger"
}
mutate() {
  pace_write
  echo "WRITE $(cat "$SWEEP_CLOCK_FILE") $2 $3" >> "$RUNNER_TEMP/trace"
  code=200
  case "$3" in
    "repos/$REWARD_REPO/collaborators/"*)
      [ "$1" = "$ADMIN_TOKEN" ] && [ "$2" = PUT ] || return 1
      jq -e '.permission=="pull"' "$4" >/dev/null || return 1
      code="$INVITE_STATUS"
      cp "$RUNNER_TEMP/invite-response" "$work/mutation.json" ;;
    "repos/$REWARD_REPO/contents/SUPPORTERS.md")
      [ "$1" = "$LEDGER_TOKEN" ] && [ "$2" = PUT ] || return 1
      if [ "$RENDER_CONFLICT" = true ] && [ ! -f "$RUNNER_TEMP/conflict-used" ]; then
        touch "$RUNNER_TEMP/conflict-used"
        cat "$RUNNER_TEMP/concurrent-row" >> "$RUNNER_TEMP/api-ledger"
        echo '{"message":"sha does not match"}' > "$work/mutation.json"
        code="$CONFLICT_STATUS"
      elif [ "$RENDER_FAIL" = true ]; then code="$RENDER_STATUS"
      else jq -jr '.content|@base64d' "$4" > "$RUNNER_TEMP/published"; fi ;;
    "repos/$REWARD_REPO/contents/ledger/$base.sweep-state.json")
      [ "$1" = "$LEDGER_TOKEN" ] && [ "$2" = PUT ] || return 1
      jq -jr '.content|@base64d' "$4" > "$RUNNER_TEMP/new-state" ;;
    *) echo "UNEXPECTED MUTATION $3" >&2; return 1 ;;
  esac
}
rotate() { echo ROTATE >> "$RUNNER_TEMP/trace"; }
reminder() { :; }
comment() { echo COMMENT_SENT >> "$RUNNER_TEMP/trace"; result=ok; }
'''

def execute(rows=(), stars=(42,), identities=None, pending=(), sweep=True, invite_status=201, body=None,
            conflict=False, render_fail=False, gate=True, setup='', previous=None, block=None, conflict_status=409, tiers='1,2,3', render_status=500):
    with tempfile.TemporaryDirectory(prefix='v2-live-') as directory:
        root=Path(directory)
        (root/'api-ledger').write_text(''.join(json.dumps(r)+'\n' for r in rows))
        (root/'clock').write_text(str(now))
        (root/'trace').touch()
        (root/'identities.json').write_text(json.dumps(identities or {}))
        (root/'pending.json').write_text(json.dumps(pending))
        (root/'header').write_bytes((fixture_dir/'SUPPORTERS.header.sample.md').read_bytes())
        (root/'invite-response').write_text(json.dumps(body or {}))
        (root/'concurrent-row').write_text(json.dumps(row(id=200,action='comment',tier=2))+'\n')
        if previous is not None: (root/'previous-state').write_text(previous if isinstance(previous,str) else json.dumps(previous))
        actions=[dict(actor='user-42',actor_id=42,gen=1,tier=t,subject='',event='issues',action=a)
                 for a,t in [('invite',1),('comment',2),('supporters-append',2)]]
        env=dict(os.environ, RUNNER_TEMP=str(root), SWEEP_CLOCK_FILE=str(root/'clock'), MODE='live',
                 SWEEP=str(sweep).lower(), GITHUB_REPOSITORY=repo, REWARD_REPO='caty-ai/ask-ai-widget',
                 GH_TOKEN='fixture-source',LEDGER_TOKEN='fixture-ledger',ADMIN_TOKEN='fixture-admin',RUN_KEY='91-1',
                 STARGAZERS=json.dumps(stars),TIERS_ENABLED=tiers,SWEEP_GATE=str(gate).lower(),
                 RED_RUN=str(not gate).lower(),CANCELLED_EVENT='3',CANCELLED_SCHEDULE='2',
                 INVITE_STATUS=str(invite_status),CONFLICT_STATUS=str(conflict_status),RENDER_CONFLICT=str(conflict).lower(),RENDER_FAIL=str(render_fail).lower(),RENDER_STATUS=str(render_status),
                 LEDGER_EXPIRES='',ADMIN_EXPIRES='',ACTIONS=json.dumps(actions))
        script=clock+prefix+doubles+'\nread_ledger\ncp "$RUNNER_TEMP/pending.json" "$work/pending.json"\n'+setup+'\n'+(block if block is not None else catchup_block if sweep else event_block)
        result=subprocess.run(['/bin/bash','-c',script],env=env,capture_output=True,text=True)
        assert not result.stderr,(result.stdout,result.stderr)
        files={p.name:p.read_text() for p in root.iterdir() if p.is_file()}
        all_rows=[json.loads(v) for v in files['api-ledger'].splitlines()]
        state=json.loads(files['new-state']) if 'new-state' in files else None
        messages=(root/'supporter-loop/sweep-messages').read_text() if (root/'supporter-loop/sweep-messages').exists() else ''
        return result,all_rows[len(rows):],state,files,messages

limit=json.loads((fixture_dir/'invitation-limit-422.json').read_text())
for body,expected,red in [(limit,'deferred-quota',False),({'message':'sha does not match'},'error-422',True),({'message':'Validation Failed'},'error-422',True)]:
    r,rows,state,files,_=execute(sweep=False,invite_status=422,body=body)
    assert [v['result'] for v in rows]==[expected]*3, rows
    assert bool(r.returncode)==red,(r.stdout,r.returncode)
    assert 'COMMENT_SENT' not in files['trace'] and 'published' not in files
    assert all('invitations_backlog' not in v for v in rows)
print('PASS invitation-limit 422 / CAS and generic negatives / whole event bundle declines siblings / green deferral')

r,rows,state,files,_=execute()
assert r.returncode==0,r.stdout
assert [(v['action'],v['result'],v['tier'],v['dedup_key']) for v in rows]==[
    ('invite','ok-catchup',1,repo+':1:42'),('supporters-append','ok',1,repo+':1:42')],rows
assert set(state)=={'last_sweep_ts','backlog','cancelled_runs','capacity_pct','alarm_state'}
assert state['backlog']==0 and state['cancelled_runs']==dict(event=3,schedule=2)
assert state['capacity_pct']['invitations']==1/45
assert files['trace'].index('PUT repos/caty-ai/ask-ai-widget/contents/SUPPORTERS.md') < files['trace'].index('APPEND supporters-append')
assert '@user-42' in files['published']
write_times=[int(line.split()[1]) for line in files['trace'].splitlines() if line.startswith('WRITE ')]
assert all(b-a>=1 for a,b in zip(write_times,write_times[1:])),write_times
print('PASS actual catchup ok-catchup tier key / PUT precedes append queue / state derivation / <=1 write per second')

r,rows,state,files,_=execute(rows=[row()],pending=[dict(invitee=dict(id=42),created_at='2026-09-08T00:00:00Z')])
assert r.returncode==0 and [v['action'] for v in rows]==['supporters-append']
assert 'GET user/' not in files['trace'] and 'PUT repos/caty-ai/ask-ai-widget/collaborators/' not in files['trace']
print('PASS crash-between-actions stranded append repaired in pass1 without identity or invitation')

for login,kind,reason in [('CaTy2','User','family'),('helper','Bot','bot'),('helper[bot]','User','bot'),
                          ('caty-ai','User','self'),('github-actions[bot]','Bot','self'),('some-org','Organization','org')]:
    r,rows,state,files,_=execute(stars=[42,99],identities={'42':dict(id=42,login=login,type=kind)})
    assert r.returncode==0,r.stdout
    assert rows[0]['action']=='skip' and rows[0]['result']=='excluded-'+reason and rows[0]['dedup_key']==repo+':sweep:42',rows
    assert rows[1]['actor_id']==99 and rows[1]['result']=='ok-catchup'
    assert state['backlog']==0
    print('PASS actual catchup exclusion / slot refill: '+login)
# MEMBER is only observable from tier2/3 events; current-generation ledger exclusion suppresses identity.
r,rows,state,files,_=execute(rows=[row(action='skip',tier=2,result='excluded-member')])
assert r.returncode==0 and rows==[] and 'GET user/' not in files['trace']
print('PASS catchup excluded-member from event ledger suppresses identity')

cycles=[row(ts='2026-08-01T00:00:00Z'),row(action='cancel-invite',result='expired',tier=0,ts='2026-08-09T00:00:00Z',run='2-1'),
        row(ts='2026-08-10T00:00:00Z',run='3-1'),row(action='cancel-invite',result='expired',tier=0,ts='2026-08-18T00:00:00Z',run='4-1')]
r,rows,state,files,_=execute(rows=cycles)
assert r.returncode==0 and len(rows)==1 and rows[0]['result']=='excluded-unresponsive',rows
assert 'GET user/' not in files['trace'] and state['backlog']==0
print('PASS actual two-invitation bound produces excluded-unresponsive once')

r,rows,state,files,_=execute(stars=[42,99,7],invite_status=422,body=limit)
assert r.returncode==0 and len(rows)==1 and rows[0]['action']=='skip' and rows[0]['result']=='deferred-quota'
assert state['backlog']==3 and state['alarm_state']['deferred_quota']
assert files['trace'].count('GET user/')==1
print('PASS sweep invitation-limit stop emits exactly one skip, remains green, reports every unserved candidate')

r,rows,state,files,_=execute(conflict=True)
assert r.returncode==0,r.stdout
assert '@user-200' in files['published']
operations=[v for v in files['trace'].splitlines() if v=='READ_LEDGER' or v=='GET repos/caty-ai/ask-ai-widget/contents/SUPPORTERS.md' or 'PUT repos/caty-ai/ask-ai-widget/contents/SUPPORTERS.md' in v]
first_put=next(i for i,v in enumerate(operations) if 'PUT ' in v)
assert operations[first_put-2:first_put]==['GET repos/caty-ai/ask-ai-widget/contents/SUPPORTERS.md','READ_LEDGER'],operations
assert operations[first_put+1:first_put+3]==['GET repos/caty-ai/ask-ai-widget/contents/SUPPORTERS.md','READ_LEDGER'],operations
print('PASS two-lane regeneration conflict restarts GET -> read ledger -> render -> PUT; concurrent actor preserved')

r,rows,state,files,_=execute(render_fail=True, stars=[42,99,7])
queued=[v for v in rows if v['action']=='supporters-append']
assert r.returncode!=0 and len(queued)==3 and all(v['result']=='error-500' for v in queued) and state['backlog']==3
print('PASS failed projection closes queued lines with error and keeps backlog red')

r,rows,state,files,_=execute(sweep=False, render_fail=True)
assert r.returncode!=0 and rows[-1]['action']=='supporters-append' and rows[-1]['result']=='error-500'
print('PASS event projection failure records exact PUT status')

r,rows,state,files,_=execute(render_fail=True, render_status='transport')
assert r.returncode!=0 and rows[-1]['result']=='error-regenerate'
print('PASS projection transport failure without HTTP status uses error-regenerate')


r,rows,state,files,_=execute(setup='code=404; : > "$RUNNER_TEMP/header"')
assert r.returncode!=0 and rows[-1]['result']=='error-regenerate' and state['backlog']==1
print('PASS malformed header without HTTP failure uses error-regenerate, never stale status')

r,rows,state,files,_=execute(stars=['invalid'])
assert r.returncode!=0 and '::error::stargazer handoff invalid in act' in r.stdout
assert rows==[] and 'published' in files and state is not None
print('PASS defensive invalid stars handoff is loud and red; reserve still runs')


r,rows,state,files,_=execute(gate=False)
assert r.returncode!=0 and rows==[] and 'published' in files and state['backlog']==1 and state['alarm_state']['red_run']
print('PASS red-run sweep skips catchup but unconditionally regenerates and writes state')

for setup in ['writeCount=148; reservedCount=2', 'echo "$((started+361))" > "$SWEEP_CLOCK_FILE"']:
    r,rows,state,files,_=execute(setup=setup)
    assert r.returncode==0 and rows==[] and state['backlog']==1 and 'ROTATE' in files['trace'] and 'published' in files
print('PASS whole-sweep write/time budget stops green and still executes reserve')
# Pass1 reservations cap 148 queued lines with two final writes reserved; no identities.
r,rows,state,files,_=execute(rows=[row(id=i) for i in range(1,5)],stars=[1,2,3,4],setup='writeCount=146')
assert r.returncode==0 and len(rows)==2 and state['backlog']==2
print('PASS pass1 queued repairs reserve writes at enqueue time')

# End-of-sweep latch only fires edges, including clear; corrupt latch self heals.
_,_,state,_,_=execute()
r,rows,state2,files,messages=execute(previous=state)
assert len(messages.splitlines())==1 and state2==state
r,rows,state2,files,messages=execute(previous={'alarm_state':{'stars_70':True,'red_run':True,'deferred_quota':True,'invitations_backlog':True}})
assert messages.count('cleared')==4
r,rows,state2,files,messages=execute(previous='not JSON')
assert r.returncode==0 and len(messages.splitlines())==1
print('PASS sweep-state latch repeat / raised-to-cleared transitions / unparsable recovery')

# Dynamic quota wait helper with the actual rolling model, injectable clock and sleep.
quota_rows=[row(id=i,ts='2026-09-07T00:02:00Z') for i in range(45)]
block='quota_room\necho "WAIT_TOTAL=$waitCount"\n'
r,_,_,files,_=execute(rows=quota_rows,block=block)
assert r.returncode==0 and 'WAIT_TOTAL=120' in r.stdout
quota_rows=[row(id=i,ts='2026-09-07T00:04:00Z') for i in range(45)]
r,_,_,files,_=execute(rows=quota_rows,block=block)
assert r.returncode!=0 and 'WAIT ' not in files['trace']
quota_rows=[row(id=i,ts='2026-09-07T00:02:00Z') for i in range(45)]
r,_,_,files,_=execute(rows=quota_rows,setup='waitCount=100',block=block)
assert r.returncode!=0 and 'WAIT ' not in files['trace']
print('PASS quota ages out dynamically / 5min lookahead / cumulative wait <=3min')
# Reserve quota before identities, re-evaluate per PUT, lazy selection at capacity.
r,rows,state,files,_=execute(rows=[row(id=i) for i in range(1,45)],stars=[90,91,92])
assert r.returncode==0 and state['backlog']==2 and files['trace'].count('GET user/')==1
assert [v['actor_id'] for v in rows]==[90,90]
print('PASS per-PUT quota reevaluation and identity calls bounded by available capacity')

# A sha-mismatch 422 follows the same restart path as 409, never quota deferral.
r,rows,state,files,_=execute(conflict=True,conflict_status=422)
assert r.returncode==0 and '@user-200' in files['published'],(r.stdout,rows)
assert all(v['result']!='deferred-quota' for v in rows)
operations=[v for v in files['trace'].splitlines() if v=='READ_LEDGER' or v=='GET repos/caty-ai/ask-ai-widget/contents/SUPPORTERS.md' or 'PUT repos/caty-ai/ask-ai-widget/contents/SUPPORTERS.md' in v]
first_put=next(i for i,v in enumerate(operations) if 'PUT ' in v)
assert operations[first_put+1:first_put+3]==['GET repos/caty-ai/ask-ai-widget/contents/SUPPORTERS.md','READ_LEDGER'],operations
print('PASS 422 catch-up CAS restarts GET and fresh ledger read without quota deferral')

# One expired cycle keeps the existing append delivered: only re-invite is ledgered.
r,rows,state,files,_=execute(rows=cycles[:2]+[row(action='supporters-append',ts='2026-08-01T00:00:00Z')])
assert r.returncode==0 and [(v['action'],v['result']) for v in rows]==[('invite','ok-catchup')],rows
assert '@user-42' in files['published'] and state['backlog']==0
print('PASS rearmed invite restores projection without queue or redundant append line')
r,rows,state,files,_=execute(tiers='2,3')
assert r.returncode==0 and rows==[] and state['backlog']==0 and 'GET user/' not in files['trace']
print('PASS actual catch-up is empty when tier1 disabled')

# Error fields can identify the limit, but generic validation must never be swallowed.
for field in ('message','code'):
    r,rows,_,files,_=execute(sweep=False,invite_status=422,body={'message':'Validation Failed','errors':[{field:'too many invitations'}]})
    assert r.returncode==0 and all(v['result']=='deferred-quota' for v in rows)
    assert 'COMMENT_SENT' not in files['trace']
print('PASS invitation-limit nested errors message/code recognition')

# Exercise the real steps 2-4 loops with a fake clock, then the real reserve tail.
cleanup_block='sweep_cleanup() {'+main.split('sweep_cleanup() {',1)[1]
cleanup_doubles=r'''
# Only these two exhaustive list reads are allowed during cleanup.
pages() {
  case "$2" in
    "repos/$REWARD_REPO/collaborators?per_page=100") echo '[{"id":42}]' > "$3" ;;
    "repos/$REWARD_REPO/invitations?per_page=100") echo '[]' > "$3" ;;
    *) return 1 ;;
  esac
}
baseline() { echo '{"collaborators":[],"invitations":[]}' > "$work/baseline.json"; }
all_markers() { echo '[]' > "$work/markers.json"; }
'''
r,rows,state,files,_=execute(rows=[row()],setup=cleanup_doubles+'\necho "$((started+361))" > "$SWEEP_CLOCK_FILE"',block=cleanup_block)
assert r.returncode!=0 and rows==[] and 'audit deadline exceeded' in r.stdout
assert 'published' in files and state is not None and 'ROTATE' in files['trace']
print('PASS step2 deadline fails incomplete audit closed and still executes steps5-8')
# Advance while collecting marker evidence: the per-subject loop must not start reads.
setup=cleanup_doubles+r'''
all_markers() {
  echo '[]' > "$work/markers.json"
  echo "$((started+361))" > "$SWEEP_CLOCK_FILE"
}
'''
comment_row=dict(row(action='comment',tier=2),subject='https://github.com/'+repo+'/issues/5')
r,rows,state,files,_=execute(rows=[row(),comment_row],setup=setup,block=cleanup_block)
assert r.returncode!=0 and 'audit deadline exceeded' in r.stdout and 'published' in files and state is not None
assert 'GET repos/'+repo+'/issues/5' not in files['trace']
print('PASS per-subject audit deadline stops reads, blocks cleanup, preserves reserve')
# With no subjects, the same boundary is checked inside marker reconciliation.
r,rows,state,files,_=execute(rows=[row()],stars=[],setup=setup,block=cleanup_block)
assert r.returncode!=0 and 'audit deadline exceeded' in r.stdout and 'published' in files and state is not None
assert 'DELETE ' not in files['trace']
print('PASS marker reconciliation deadline blocks destructive cleanup and preserves reserve')
# Once the audit is complete, unrevoked actors wait; this budget stop stays green.
setup=cleanup_doubles+r'''
within_deadline() {
  if [ "${audit_complete:-false}" = true ]; then echo "$((started+361))" > "$SWEEP_CLOCK_FILE"; fi
  [ "$(elapsed)" -le 360 ]
}
'''
r,rows,state,files,_=execute(rows=[row()],stars=[],setup=setup,block=cleanup_block)
assert r.returncode==0 and rows==[] and 'DELETE ' not in files['trace'] and 'published' in files and state is not None,(r.stdout,rows)
print('PASS revoke deadline defers unrevoked actors green and executes steps5-8')
