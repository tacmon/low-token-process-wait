import importlib.util
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'skills' / 'low-token-process-wait' / 'scripts'
spec = importlib.util.spec_from_file_location('launcher', ROOT / 'launch_cli.py')
launcher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(launcher)


class LauncherTests(unittest.TestCase):
    def test_passthrough_calls_preserve_arguments(self):
        for args in [['--version'], ['login'], ['--remote', 'ws://localhost:1']]:
            self.assertEqual(launcher.launch_argv('/fake/codex', args, True), ['/fake/codex', *args])
        self.assertEqual(launcher.launch_argv('/fake/codex', ['hello'], False), ['/fake/codex', 'hello'])

    def test_existing_tmux_preserves_permissions_and_literal_prompt(self):
        with patch.dict(os.environ, {'TMUX': '/existing/socket,1,0'}):
            args = ['-s', 'workspace-write', '-a', 'on-request', 'literal $() and `text`']
            actual = launcher.launch_argv('/fake/codex', args, True)
            self.assertEqual(actual, ['/fake/codex', '--no-daemon', '--no-alt-screen', *args])

    @unittest.skipUnless(shutil.which('tmux'), 'tmux required')
    def test_real_dedicated_server_history_and_options(self):
        with tempfile.TemporaryDirectory() as home, patch.dict(os.environ, {'HOME': home}):
            previous = os.environ.pop('TMUX', None)
            try:
                args = ['-s', 'workspace-write', 'literal $() and `text`']
                cmd = launcher.launch_argv('/fake/codex', args, True)
                self.assertEqual(shlex.split(cmd[-1]), ['/fake/codex', '--no-daemon', '--no-alt-screen', *args])
                socket = cmd[cmd.index('-L') + 1]
                cmd.insert(cmd.index('new-session') + 1, '-d')
                cmd[-1] = '/bin/sleep 30'  # no model invocation
                try:
                    subprocess.run(cmd, check=True, capture_output=True, timeout=5)
                    for key, expected in [('mouse', 'on'), ('status', 'off'), ('set-clipboard', 'on'), ('prefix', 'None'), ('remain-on-exit', 'off')]:
                        output = subprocess.check_output(['tmux', '-L', socket, 'show-options', '-g', key], text=True, timeout=5).strip()
                        self.assertEqual(output, f'{key} {expected}')
                    output = subprocess.check_output(['tmux', '-L', socket, 'display-message', '-p', '#{history_limit}'], text=True, timeout=5).strip()
                    self.assertEqual(output, '100000')
                finally:
                    subprocess.run(['tmux', '-L', socket, 'kill-server'], capture_output=True, timeout=5)
            finally:
                if previous is not None:
                    os.environ['TMUX'] = previous


if __name__ == '__main__':
    unittest.main()
