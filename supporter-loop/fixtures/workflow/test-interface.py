#!/usr/bin/env python3
"""Check the frozen interface, credential scopes, and template/roster contracts."""
from pathlib import Path
import re
import os
import subprocess
import yaml

path = Path('.github/workflows/supporter-loop-reusable.yml')
text = path.read_text()
workflow = yaml.safe_load(text)
call = workflow.get('on', workflow.get(True))['workflow_call']
assert set(call['inputs']) == {'mode', 'reward_repo', 'tiers_enabled', 'sweep'}
assert call['inputs']['mode']['required'] is True
assert call['inputs']['reward_repo']['default'] == 'caty-ai/ask-ai-widget'
assert call['inputs']['tiers_enabled']['default'] == '1,2,3'
assert call['inputs']['sweep']['default'] is False
assert set(call['secrets']) == {'SUPPORTER_LEDGER_TOKEN', 'SUPPORTER_LOOP_TOKEN', 'TELEGRAM_BOT_TOKEN', 'TELEGRAM_CHAT_ID'}
assert all(spec.get('description') for spec in list(call['inputs'].values()) + list(call['secrets'].values()))
assert call['secrets']['SUPPORTER_LOOP_TOKEN']['required'] is False
assert all(v['required'] is True for k, v in call['secrets'].items() if k != 'SUPPORTER_LOOP_TOKEN')
# Contract §4.2 descriptions are part of the frozen call surface.
expected_descriptions = {
    'mode': 'record-only | live. Anything else fails the run before any step touches the network.',
    'reward_repo': 'owner/name of the private reward repo (ledger + invitations).',
    'tiers_enabled': 'Comma-separated subset of 1,2,3. Events for a disabled tier are ledgered as action=skip result=tier-disabled.',
    'sweep': 'true only from the scheduled sweep job (§11). Mutually exclusive with a tier event.',
    'SUPPORTER_LEDGER_TOKEN': 'Fine-grained PAT, reward_repo only, Contents R/W (§8). Used by decide (ledger) and act (SUPPORTERS.md). Required in both modes.',
    'SUPPORTER_LOOP_TOKEN': 'Fine-grained PAT, reward_repo only, Administration R/W (§8). Loaded only by the act job; may be left unset until checkpoint #4. act fails loud if empty in live.',
    'TELEGRAM_BOT_TOKEN': 'Owner notification bot (§9).',
    'TELEGRAM_CHAT_ID': 'Owner notification chat (§9).',
}
assert {k: v['description'] for group in ('inputs', 'secrets') for k, v in call[group].items()} == expected_descriptions
for step in workflow['jobs']['decide']['steps']:
    variable_refs = [v for v in step.get('env', {}).values() if 'vars' in str(v)]
    assert all(v == '${{ vars.SUPPORTER_LEDGER_TOKEN_EXPIRES }}' for v in variable_refs)
assert 'toJSON(vars)' not in text
assert workflow['permissions'] == {}
assert set(workflow['jobs']) == {'decide', 'act', 'alert'}
expected = {
    'decide': {'contents': 'none', 'actions': 'read', 'issues': 'read', 'pull-requests': 'read', 'discussions': 'read'},
    'act': {'contents': 'none', 'issues': 'write', 'pull-requests': 'write', 'discussions': 'write'},
    'alert': {},
}
assert not workflow.get('env')
for job_id, job in workflow['jobs'].items():
    assert job['permissions'] == expected[job_id]
    assert 0 < job['timeout-minutes'] <= (2 if job_id == 'alert' else 10)
    assert not job.get('env')
    for step in job['steps']:
        assert 'uses' not in step
        assert '${{' not in step.get('run', ''), 'No expressions enter shell source'
act = workflow['jobs']['act']
assert act['needs'] == 'decide'
assert act['if'] == "${{ inputs.mode == 'live' && (needs.decide.outputs.has_live_actions == 'true' || inputs.sweep == true) }}"
assert act['steps'][0]['id'] == 'preflight'
assert all("steps.preflight.outcome == 'success'" in step.get('if', '') for step in act['steps'][1:])
alert = workflow['jobs']['alert']
assert alert['needs'] == ['decide', 'act']
assert alert['if'] == "${{ !cancelled() && failure() && inputs.mode == 'live' }}"
assert len(alert['steps']) == 1
assert not re.search(r'\b(gh|curl)\b', workflow['jobs']['decide']['steps'][0]['run'])
print('PASS frozen four-input/four-secret interface; three jobs; permissions; mode/preflight gates')
for tier in (2, 3):
    template = Path(f'supporter-loop/comment-tier{tier}.md').read_text()
    assert template.splitlines()[0] == f'<!-- supporter-loop:tier{tier}:{{{{actor_id}}}} -->'
    assert set(re.findall(r'{{(.*?)}}', template)) == {'actor_id', 'login', 'reward_repo_url'}
    assert 'checkpoint #4' in template.splitlines()[1]
print('PASS template markers, substitution allowlist and checkpoint wording')
old = Path('.github/workflows/external-input-watch.yml').read_text()
roster = lambda source: re.search(r'^\s*fam_roster=(.*)$', source, re.M).group(1)
assert roster(text) == roster(old)
assert "tr '[:upper:]' '[:lower:]'" in text
print('PASS copied family roster and case-insensitive comparison')

for mode in ('', 'dry-run', 'LIVE', 'record-only\nlive'):
    result = subprocess.run(['/bin/bash', '-c', workflow['jobs']['decide']['steps'][0]['run']],
                            env=dict(os.environ, MODE=mode), capture_output=True, text=True)
    assert result.returncode == 1 and '::error::invalid mode' in result.stdout, result
print('PASS invalid modes fail in the first step before network access')
