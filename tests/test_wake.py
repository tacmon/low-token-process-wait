import importlib.util
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1] / 'skills' / 'low-token-process-wait' / 'scripts'
spec = importlib.util.spec_from_file_location('wake', ROOT / 'wake.py')
wake = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wake)


class FakeUI:
    events = []
    status = 'active'
    objective = 'Original goal with nontrivial context'
    changed = False
    busy = False
    fail_send = False
    def __init__(self, *args):
        pass
    def idle(self):
        return not self.busy
    def verify_thread(self):
        self.events.append(('verify', time.monotonic()))
        if self.changed:
            raise wake.UnsafeTarget('thread changed')
    def goal_summary(self):
        return self.status, self.objective
    def set_goal(self, status, objective):
        if objective != self.objective:
            raise wake.UnsafeTarget('Goal changed')
        self.status = status
        self.events.append((status, time.monotonic()))
    def type_enter(self, text):
        self.events.append(('input', time.monotonic(), text))
        if self.fail_send:
            raise wake.UnsafeTarget('ambiguous send')
    def input_recorded(self, message):
        return True
    def goal_identity(self):
        return 123


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.directory = Path(self.temp.name)
        self.path = self.directory / 'result.json'
        FakeUI.events = []
        FakeUI.status = 'active'
        FakeUI.objective = 'Original goal with nontrivial context'
        FakeUI.changed = FakeUI.busy = FakeUI.fail_send = False
        self.data = dict(id='test-job', phase='prepared', socket='test', pane='%0',
                         thread='session', identity=['%0', 1, '0'], goal=False,
                         command=['/usr/bin/python3', '-c', 'print("ok")'],
                         attach_pid=None, cwd=self.temp.name, delivery_timeout=2)
    def tearDown(self):
        self.temp.cleanup()
    def run_worker(self):
        wake.save(self.path, self.data)
        with patch.object(wake, 'TmuxInput', FakeUI):
            rc = wake.worker(self.path)
        return rc, json.loads(self.path.read_text())
    def test_success_only_after_actual_exit(self):
        self.data['command'] = ['/usr/bin/python3', '-c', 'import time; time.sleep(.3); print("done")']
        before = time.monotonic()
        rc, result = self.run_worker()
        self.assertEqual(rc, 0)
        self.assertEqual(result['phase'], 'delivered')
        self.assertEqual(result['exit_code'], 0)
        input_event = next(e for e in FakeUI.events if e[0] == 'input')
        self.assertGreaterEqual(input_event[1] - before, .3)
        self.assertEqual((self.directory / 'command.log').read_text().strip(), 'done')
    def test_failure_is_reported_not_success(self):
        self.data['command'] = ['/usr/bin/python3', '-c', 'raise SystemExit(7)']
        rc, result = self.run_worker()
        self.assertEqual(result['exit_code'], 7)
        self.assertIn('exit_code=7', result['message'])
        self.assertEqual(rc, 0)
    def test_signal_exit(self):
        self.data['command'] = ['/usr/bin/python3', '-c', 'import os,signal; os.kill(os.getpid(),signal.SIGTERM)']
        _, result = self.run_worker()
        self.assertEqual(result['exit_code'], -15)
    def test_goal_preserved_pause_then_input_then_resume(self):
        self.data['goal'] = True
        rc, result = self.run_worker()
        self.assertEqual(rc, 0)
        self.assertTrue(result['goal_restored'])
        self.assertEqual(result['goal_objective'], FakeUI.objective)
        kinds = [e[0] for e in FakeUI.events]
        self.assertLess(kinds.index('paused'), kinds.index('input'))
        self.assertLess(kinds.index('input'), kinds.index('active'))
    def test_changed_thread_never_runs_command(self):
        FakeUI.changed = True
        _, result = self.run_worker()
        self.assertEqual(result['phase'], 'attention')
        self.assertFalse((self.directory / 'command.log').exists())
        self.assertFalse(any(e[0] == 'input' for e in FakeUI.events))
    def test_completed_result_survives_delivery_failure(self):
        FakeUI.fail_send = True
        _, result = self.run_worker()
        self.assertEqual(result['phase'], 'attention')
        self.assertEqual(result['previous_phase'], 'submitting')
        self.assertEqual(result['exit_code'], 0)
        with patch.object(wake, 'TmuxInput', FakeUI):
            with self.assertRaises(RuntimeError):
                wake.worker(self.path)
        self.assertEqual(len([e for e in FakeUI.events if e[0]=='input']), 1)
    def test_nonparent_exit_status_is_unknown(self):
        launcher = subprocess.Popen(['/usr/bin/python3', '-c',
            'import subprocess; p=subprocess.Popen(["/usr/bin/python3","-c","import time;time.sleep(1.5)"],stdout=subprocess.DEVNULL); print(p.pid,flush=True);p.wait()'],
            stdout=subprocess.PIPE, text=True)
        pid = int(launcher.stdout.readline())
        stat = Path(f'/proc/{pid}/stat').read_text()
        parent_pid = int(stat[stat.rfind(')')+2:].split()[1])
        self.assertEqual(parent_pid, launcher.pid)
        self.assertNotEqual(parent_pid, os.getpid())
        self.data.update(command=[], attach_pid=pid, attach_identity=list(wake.proc_identity(pid)))
        try:
            rc, result = self.run_worker()
            self.assertEqual(rc, 0)
            self.assertIsNone(result['exit_code'])
            self.assertIn('exit_code=unknown', result['message'])
        finally:
            launcher.wait()
            launcher.stdout.close()
    def test_busy_target_times_out_without_typing(self):
        FakeUI.busy = True
        self.data['delivery_timeout'] = .1
        _, result = self.run_worker()
        self.assertEqual(result['phase'], 'attention')
        self.assertFalse(any(e[0] == 'input' for e in FakeUI.events))
    def test_changed_goal_during_job_is_not_resumed(self):
        self.data['goal'] = True
        self.data['command'] = ['/usr/bin/python3', '-c', 'import time;time.sleep(.3)']
        def change():
            time.sleep(.1)
            FakeUI.objective = 'New user goal'
        t = threading.Thread(target=change)
        t.start()
        _, result = self.run_worker()
        t.join()
        self.assertEqual(result['phase'], 'attention')
        self.assertEqual(result['exit_code'], 0)
        self.assertFalse(any(e[0] in ('active', 'input') for e in FakeUI.events))
    def test_same_pane_second_job_refused_while_first_is_live(self):
        self.data['command'] = ['/usr/bin/python3', '-c', 'import time;time.sleep(.8)']
        wake.save(self.path, self.data)
        second_dir = self.directory/'second'
        second_dir.mkdir()
        second = second_dir/'result.json'
        wake.save(second, dict(self.data, id='second'))
        with patch.object(wake, 'TmuxInput', FakeUI):
            t = threading.Thread(target=wake.worker, args=(self.path,))
            t.start()
            deadline = time.monotonic()+2
            while json.loads(self.path.read_text())['phase']!='running' and time.monotonic()<deadline:
                time.sleep(.01)
            self.assertEqual(json.loads(self.path.read_text())['phase'], 'running')
            self.assertEqual(wake.worker(second), 1)
            t.join()
        self.assertFalse((second_dir/'command.log').exists())
        self.assertIn('another wake job', json.loads(second.read_text())['error'])


class InputTests(unittest.TestCase):
    def test_only_known_empty_idle_composer_accepted(self):
        self.assertTrue(wake.TmuxInput.blank_composer('› Ask Codex to do anything\n? for shortcuts'))
        for s in ['› my draft\n? for shortcuts', '› Ask Codex to do anything\nesc to interrupt',
                  '◦ Working (2s • esc to interrupt)\n› Ask Codex to do anything\n? for shortcuts',
                  '› Ask Codex to do anything\nenter continue', '› 1. Allow once\n? for shortcuts',
                  'unknown screen', 'a quoted › Ask Codex to do anything\n? for shortcuts']:
            self.assertFalse(wake.TmuxInput.blank_composer(s), s)
    def test_native_controls_can_pause_busy_goal(self):
        self.assertTrue(wake.TmuxInput.blank_composer('› Ask Codex to do anything\nesc to interrupt', native=True))
    def test_control_sequences_rejected_before_any_side_effect(self):
        ui = object.__new__(wake.TmuxInput)
        for text in ['', 'a\nb', '\x1b[2J', 'a\rb', 'a\x00b']:
            with self.assertRaises(ValueError):
                ui.type_enter(text)
    def test_user_changes_draft_after_paste_enter_is_withheld(self):
        ui = object.__new__(wake.TmuxInput)
        ui.pane = '%0'
        ui.check = lambda: None
        screens = iter(['› Ask Codex to do anything\n? for shortcuts',
                        '› completion USER_DRAFT\n\n? for shortcuts'])
        ui.screen = lambda: next(screens)
        sent = []
        ui.tmux = lambda *args: sent.append(args)
        with patch.object(wake.time, 'sleep'):
            with self.assertRaises(wake.UnsafeTarget):
                ui.type_enter('completion')
        self.assertEqual(len(sent), 1)
        self.assertNotEqual(sent[-1][-1], 'Enter')
    def test_real_shell_pane_refused(self):
        socket = 'wake-unit-' + str(os.getpid())
        subprocess.run(['tmux', '-L', socket, '-f', '/dev/null', 'new-session', '-d', '-s', 'test', 'sleep 10'], check=True)
        try:
            with self.assertRaises(wake.UnsafeTarget):
                wake.TmuxInput(socket, '%0', 'fake')
        finally:
            subprocess.run(['tmux', '-L', socket, 'kill-server'], check=True)


if __name__ == '__main__':
    unittest.main(verbosity=2)
