import copy
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch, Mock

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / 'server'))
import craft_mcp as cm
import craft_page as page


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.patch = patch.object(cm, 'STATE_DIR', self.temp.name)
        self.patch.start(); self.addCleanup(self.patch.stop)
        self.app = cm.App('wordcraft')
        self.app.root = self.temp.name

    def test_connection_and_root_decisions(self):
        cases = [(True, False, None, False), (True, False, self.app.root, False),
                 (True, False, '/other-workspace', 'another workspace'),
                 (False, True, None, 'already open without'),
                 (True, False, None, 'connection unavailable')]
        for listening, uncontrolled, root, outcome in cases:
            with self.subTest(listening=listening, uncontrolled=uncontrolled, root=root, outcome=outcome), \
                 patch.object(self.app, 'install', return_value=('/tmp', '/tmp/wordcraft', '/tmp/cli')), \
                 patch.object(self.app, 'listening_pid', return_value=12 if listening else None), \
                 patch.object(self.app, 'running_without_control', return_value=uncontrolled), \
                 patch.object(self.app, 'read_state', return_value={'root': root}), \
                 patch.object(self.app, 'verify_connection', side_effect=cm.ToolError('connection unavailable') if outcome == 'connection unavailable' else None), \
                 patch.object(cm.subprocess, 'Popen') as launch:
                if isinstance(outcome, str):
                    with self.assertRaisesRegex(cm.ToolError, outcome): self.app.ensure_open()
                else: self.assertFalse(self.app.ensure_open())
                launch.assert_not_called()

    def test_two_launches_start_one_process(self):
        listening = threading.Event()
        child = Mock(); child.poll.return_value = None
        def launch(*args, **kwargs): listening.set(); return child
        with patch.object(self.app, 'install', return_value=('/tmp', '/tmp/wordcraft', '/tmp/cli')), \
             patch.object(cm.App, 'listening_pid', side_effect=lambda: 12 if listening.is_set() else None), \
             patch.object(cm.App, 'running_without_control', return_value=False), \
             patch.object(cm.App, 'verify_connection', return_value={}), \
             patch.object(cm.subprocess, 'Popen', side_effect=launch) as popen:
            results = []
            threads = [threading.Thread(target=lambda: results.append(self.app.ensure_open())) for _ in range(2)]
            for thread in threads: thread.start()
            for thread in threads: thread.join(timeout=5)
            self.assertEqual(sorted(results), [False, True]); self.assertEqual(popen.call_count, 1)

    def test_recovery_does_not_trust_old_launch_state(self):
        # Independent fixture: launch metadata from an older extension, no live app.
        pathlib.Path(self.app.state_file).write_text('{"root":"/old-workspace","started":1}')
        child = Mock(); child.poll.return_value = None
        with patch.object(self.app, 'install', return_value=('/tmp', '/tmp/wordcraft', '/tmp/cli')), \
             patch.object(self.app, 'listening_pid', side_effect=[None, 42]), \
             patch.object(self.app, 'running_without_control', return_value=False), \
             patch.object(self.app, 'verify_connection', return_value={}), \
             patch.object(cm.subprocess, 'Popen', return_value=child):
            self.assertTrue(self.app.ensure_open())
            self.assertEqual(self.app.read_state()['root'], self.temp.name)

    def test_cross_process_lock(self):
        script = 'import sys;sys.path.insert(0,"server");import craft_mcp as c;\nwith c.app_lock("wordcraft",timeout=.1):print("unexpected")'
        env = dict(os.environ, PICODE_CRAFT_STATE_DIR=self.temp.name)
        with cm.app_lock('wordcraft'):
            r = subprocess.run([sys.executable, '-c', script], env=env, capture_output=True, text=True, timeout=3)
        self.assertNotEqual(r.returncode, 0); self.assertIn('This app is busy', r.stderr)
        with cm.app_lock('wordcraft', timeout=.1): pass

    def test_port_collision_blocks_before_launch(self):
        app = cm.App('wordcraft'); app.spec = dict(app.spec, port=cm.APPS['designcraft']['port'])
        with self.assertRaisesRegex(cm.ToolError, 'same control port'): app.install()

    def test_wrong_windows_listener_is_not_adopted(self):
        with patch.object(cm, 'WSL', True), patch.object(cm, 'powershell', return_value='otherapp'):
            with self.assertRaisesRegex(cm.ToolError, 'another program'): self.app.verify_connection()

    def test_posix_probe_rejects_unavailable_channel(self):
        with patch.object(cm, 'WSL', False), patch.object(cm.Bridge, 'call', return_value={'result': {'isError': True}}):
            with self.assertRaisesRegex(cm.ToolError, 'connection is unavailable'): self.app.verify_connection()

    def test_paths_and_wordcraft_key(self):
        with patch.object(cm, 'WSL', True), patch.object(cm, 'to_app_path', side_effect=lambda p: 'WIN:' + p), \
             patch.object(self.app, 'install', return_value=('/tmp', '/tmp/wordcraft', '/tmp/cli')):
            self.assertEqual(self.app.path_arg('report.docx'), 'WIN:' + self.temp.name + '/report.docx')
            cmd = self.app.bridge_cmd(); self.assertEqual(cmd[2:], ['--connect', '127.0.0.1:7982'])
            self.assertNotIn('--control-token-file', cmd)

    def test_status_decision_table(self):
        cases = [('not-installed', False, False, None, False), ('ready', True, False, None, False),
                 ('connected', True, True, 'connected', False), ('connection-error', True, True, 'unavailable', False),
                 ('uncontrolled', True, False, None, True)]
        meta = cm.public_catalog()[0]
        for expected, installed, opened, connection, uncontrolled in cases:
            st = dict(installed=installed, open_with_control=opened, connection=connection, running_without_control=uncontrolled)
            with self.subTest(expected=expected), patch.object(cm.App, 'status', return_value=st), \
                 patch.object(cm.App, 'install'), patch.object(cm.App, 'read_state', return_value={}):
                self.assertEqual(page.app_row(meta)['state'], expected)
        with patch.object(cm.App, 'status', side_effect=OSError('offline')):
            self.assertEqual(page.app_row(meta)['state'], 'error')

    def test_workspace_lookup_and_file_routing(self):
        with patch.object(page, 'workspaces', return_value=[]):
            with self.assertRaisesRegex(page.PageError, 'Turn Crafting Apps on'): page.workspace_path('missing')
        for file, app in [('a.docx','wordcraft'),('a.pptx','deckcraft'),('a.xlsx','gridcraft'),('a.fcproj','filmcraft'),('a.pdf','printcraft')]:
            self.assertEqual(page.app_for(file), app)
        with patch.object(page, 'app_in', return_value=self.app):
            with self.assertRaisesRegex(page.PageError, 'in this workspace'): page.open_file('/outside/a.docx', 'workspace')
        with patch.object(cm, 'candidates', return_value=['wordcraft', 'deckcraft']):
            with self.assertRaisesRegex(page.PageError, 'Choose an app'): page.open_file('ambiguous', 'workspace')
        with self.assertRaisesRegex(page.PageError, 'does not open'): page.open_file('a.docx', 'workspace', 'gridcraft')

    def test_closed_snapshot_and_safe_grid_preview(self):
        with patch.object(cm.App, 'listening_pid', return_value=None):
            with self.assertRaisesRegex(page.PageError, 'not open'): page.snapshot('wordcraft')
        with patch.object(cm.App, 'listening_pid', return_value=42), patch.object(cm.App, 'verify_connection'), \
             patch.object(cm.Bridge, 'call', return_value={'result': cm.text_result({'values': [[1600]], 'sheet': 'Sheet1'})}):
            result = page.snapshot('gridcraft')
            self.assertEqual(result['table']['values'], [[1600]]); self.assertNotIn('image', result)


class RpcTests(unittest.TestCase):
    def test_lost_mutation_is_not_replayed_and_child_is_reaped(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(cm, 'STATE_DIR', temp):
            script = pathlib.Path(temp) / 'fake.py'
            script.write_text('''import sys,json,time
for line in sys.stdin:
 m=json.loads(line)
 if m.get('method')=='initialize':
  print(json.dumps({'id':m['id'],'result':{'serverInfo':{'name':'wordcraft'}}}),flush=True)
 elif m.get('method')=='tools/call':
  open(sys.argv[1],'a').write('mutation\\n');time.sleep(30)
''')
            marker = pathlib.Path(temp) / 'calls'
            app = cm.App('wordcraft'); app.bridge_cmd = lambda: [sys.executable, str(script), str(marker)]
            bridge = cm.Bridge(app)
            with self.assertRaisesRegex(cm.ToolError, 'did not answer in time'): bridge.call('save_document', {}, timeout=.15)
            self.assertEqual(marker.read_text(), 'mutation\n'); self.assertIsNone(bridge.proc)

    def test_bad_server_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(cm, 'STATE_DIR', temp):
            script = pathlib.Path(temp) / 'fake.py'
            script.write_text('import sys,json\nfor line in sys.stdin:\n m=json.loads(line);print(json.dumps({"id":m.get("id"),"result":{"serverInfo":{"name":"another-app"}}}),flush=True)\n')
            app = cm.App('wordcraft'); app.bridge_cmd = lambda: [sys.executable, str(script)]
            with cm.Bridge(app) as bridge:
                with self.assertRaisesRegex(cm.ToolError, 'identity did not match'): bridge.start()


class StdioCompatibilityTests(unittest.TestCase):
    def test_all_ten_servers_list_tools_without_opening_apps(self):
        for name in cm.APPS:
            with self.subTest(app=name):
                messages = [dict(jsonrpc='2.0', id=1, method='initialize', params={'protocolVersion':'2025-03-26'}),
                            dict(jsonrpc='2.0', id=2, method='tools/list'), dict(jsonrpc='2.0', id=3, method='ping')]
                r = subprocess.run([sys.executable, 'server/craft_mcp.py', name],
                                   input=''.join(json.dumps(m)+'\n' for m in messages), text=True,
                                   capture_output=True, timeout=5)
                self.assertEqual(r.returncode, 0, r.stderr)
                init, tools, ping = map(json.loads, r.stdout.splitlines())
                self.assertEqual(init['result']['protocolVersion'],'2025-03-26')
                self.assertEqual(init['result']['serverInfo']['version'],'0.6.0')
                names = [t['name'] for t in tools['result']['tools']]
                self.assertTrue({'app_status','app_open','app_path'}.issubset(names))
                self.assertEqual(len(names),len(set(names)))
                if name=='lightcraft': self.assertFalse(any(n.startswith('cmd_') for n in names))
                self.assertEqual(ping['result'],{})


if __name__ == "__main__": unittest.main()
