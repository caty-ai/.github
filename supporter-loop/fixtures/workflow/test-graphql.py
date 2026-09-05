#!/usr/bin/env python3
"""Run the actual reconciliation collector offline through POST-only GraphQL doubles."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

with tempfile.TemporaryDirectory(prefix='supporter-graphql-', dir=Path(__file__).resolve().parent) as directory:
    root = Path(directory)
    binary = root / 'bin'
    binary.mkdir()
    launcher = binary / 'gh'
    launcher.write_text('#!' + sys.executable + '\n' + Path(__file__).with_name('test-decide.py').read_text())
    launcher.chmod(0o700)
    (root / 'mock-config.json').write_text(json.dumps(dict(discussions=True, live_act=False, stargazers=[])))
    env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ['PATH'], MOCK_STATE=str(root),
               SOURCE_REPO='caty-ai/x-collector', REWARD_REPO='caty-ai/ask-ai-widget',
               GH_TOKEN='fixture-source', SUPPORTER_LEDGER_TOKEN='fixture-ledger')
    state = dict(ledger=[], baseline=dict(collaborators=[], invitations=[]), manual_allowlist=[], manual_markers_allowlist=[])
    result = subprocess.run(['/bin/bash', 'supporter-loop/reconcile-audit.sh', '--mode', 'record-only', '--live-gh'],
                            input=json.dumps(state), env=env, text=True, capture_output=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'reconciliation clean (record-only)' in result.stdout, result.stdout
    assert (root / 'graphql-calls').read_text().splitlines() == ['listing:POST', 'comments:POST', 'replies:POST']
    print('PASS actual reconcile collector: GraphQL listing/comments/replies require POST; record-only has no delivery writes')
