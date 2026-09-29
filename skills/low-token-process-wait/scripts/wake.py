#!/usr/bin/env python3
"""Linux/tmux supervisor. All Codex writes are literal TUI text + Enter.

No queue/exec/SDK/app-server/model HTTP calls. No credential loading.
"""
import argparse
import ctypes
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import select
import sqlite3
import subprocess
import sys
import time
import uuid


class UnsafeTarget(RuntimeError):
    pass


def save(path, data):
    path = Path(path)
    tmp = path.with_suffix('.tmp')
    with open(tmp, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def proc_identity(pid):
    # starttime prevents an exited PID being mistaken for a reused PID.
    s = Path(f'/proc/{pid}/stat').read_text()
    return int(pid), s[s.rfind(')') + 2:].split()[19]


def pidfd_open(pid):
    if hasattr(os, 'pidfd_open'):
        return os.pidfd_open(pid)
    libc = ctypes.CDLL(None, use_errno=True)
    fn = libc.pidfd_open
    fn.argtypes, fn.restype = [ctypes.c_int, ctypes.c_uint], ctypes.c_int
    fd = fn(pid, 0)
    if fd < 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error))
    return fd


class TmuxInput:
    def __init__(self, socket, pane, thread, expected=None):
        self.socket, self.pane, self.thread = socket, pane, thread
        info = self.tmux('display-message', '-p', '-t', pane,
                         '#{pane_id}|#{pane_pid}|#{pane_dead}|#{pane_in_mode}')
        pane_id, pid, dead, mode = info.strip().split('|')
        if dead != '0' or mode != '0':
            raise UnsafeTarget('pane is dead or in copy mode')
        self.pane = pane_id
        self.identity = (pane_id, *proc_identity(int(pid)))
        if expected and list(self.identity) != expected:
            raise UnsafeTarget('pane identity changed')
        self.socket = self.tmux('display-message', '-p', '#{socket_path}').strip()
        self.check()

    def tmux(self, *args):
        option = '-S' if '/' in self.socket else '-L'
        return subprocess.run(['tmux', option, self.socket, *args],
                              check=True, text=True, capture_output=True,
                              timeout=5).stdout

    def check(self):
        info = self.tmux('display-message', '-p', '-t', self.pane,
                         '#{pane_id}|#{pane_pid}|#{pane_dead}|#{pane_in_mode}')
        pane_id, pid, dead, mode = info.strip().split('|')
        if dead != '0' or mode != '0' or (pane_id, *proc_identity(int(pid))) != self.identity:
            raise UnsafeTarget('pane disappeared, was replaced, or entered copy mode')
        # Verify a real Codex executable lives in this pane process tree.
        pending = [int(pid)]
        found = False
        while pending:
            child = pending.pop()
            try:
                exe = Path(f'/proc/{child}/exe').resolve().name
                if exe == 'codex':
                    found = True
                children = Path(f'/proc/{child}/task/{child}/children').read_text()
                pending.extend(map(int, children.split()))
            except (FileNotFoundError, ProcessLookupError, PermissionError):
                pass
        if not found:
            raise UnsafeTarget('no real Codex executable in target pane')

    def screen(self, history=False):
        self.check()
        args = ['capture-pane', '-p', '-t', self.pane]
        if history:
            args += ['-S', '-1000']
        return self.tmux(*args)

    @staticmethod
    def blank_composer(screen, native=False):
        lines = screen.splitlines()
        candidates = [i for i, line in enumerate(lines) if line.startswith('› ')]
        if not candidates:
            return False
        i = candidates[-1]
        if lines[i].strip() != '› Ask Codex to do anything':
            return False
        # Drafts wrapping onto subsequent rows are also rejected.
        rest = '\n'.join(lines[i+1:])
        recognized = bool(re.search(r'\? for shortcuts|esc to interrupt', rest, re.I))
        blocked = r'enter continue|select|approve|Allow once'
        if not native:
            blocked += r'|esc to interrupt'
        # The activity spinner is above the composer, not in its footer.
        if not native and re.search(r'esc to interrupt', screen, re.I):
            return False
        return recognized and not re.search(blocked, rest, re.I)

    def idle(self):
        s = self.screen()
        return self.blank_composer(s)

    def type_enter(self, text):
        if not text or any(c in text for c in '\r\n\x1b\x00'):
            raise ValueError('input must be one nonempty line without control sequences')
        self.check()
        native = text in ('/status', '/goal', '/goal pause', '/goal resume')
        if not self.blank_composer(self.screen(), native=native):
            raise UnsafeTarget('composer is busy, nonempty, or unsupported')
        self.tmux('send-keys', '-t', self.pane, '-l', '--', text)
        # Codex paste detection needs a separate, delayed Enter.
        time.sleep(0.6)
        self.check()
        s = self.screen()
        # Reassemble the visible wrapped composer and compare the entire draft.
        lines = s.splitlines()
        candidates = [i for i, line in enumerate(lines) if line.startswith('› ')]
        if not candidates:
            raise UnsafeTarget('pasted text not visible; Enter withheld')
        i = candidates[-1]
        draft = [lines[i][2:]]
        for line in lines[i+1:]:
            if not line.strip():
                break
            if not line.startswith('  '):
                raise UnsafeTarget('unsupported composer wrapping; Enter withheld')
            draft.append(line[2:])
        # Codex wraps at spaces or between wide characters; compare whitespace
        # removed text rather than accepting a prefix with a user's added draft.
        if re.sub(r'\s+', '', ''.join(draft)) != re.sub(r'\s+', '', text):
            raise UnsafeTarget('composer changed after paste; Enter withheld')
        self.tmux('send-keys', '-t', self.pane, 'Enter')

    def verify_thread(self):
        self.type_enter('/status')
        time.sleep(0.5)
        sessions = re.findall(r'Session:\s+([0-9a-f-]{36})', self.screen(history=True))
        if not sessions or sessions[-1] != self.thread:
            raise UnsafeTarget('current TUI session differs from registered thread')

    def goal_summary(self):
        self.type_enter('/goal')
        time.sleep(0.5)
        s = self.screen(history=True)
        # Native /goal summary is authoritative UI output, not model text.
        matches = list(re.finditer(r'^Status: (active|paused|stalled|usage limited|limited by budget|complete)\s*$', s, re.M))
        if not matches:
            raise UnsafeTarget('native Goal summary not recognized')
        block = s[matches[-1].start():]
        objective = re.search(r'^Objective: (.*?)\nTime used:', block, re.M | re.S)
        if not objective:
            raise UnsafeTarget('Goal objective not recognized')
        return matches[-1].group(1), ' '.join(objective.group(1).split())

    def set_goal(self, status, objective):
        current, obj = self.goal_summary()
        if obj != objective:
            raise UnsafeTarget('Goal objective changed; automatic restoration refused')
        if current == status:
            return
        if (current, status) not in [('active', 'paused'), ('paused', 'active')]:
            raise UnsafeTarget('Goal is complete, blocked, or limited; no automatic override')
        self.type_enter('/goal ' + ('pause' if status == 'paused' else 'resume'))
        time.sleep(0.5)
        # Resume can immediately start generation; read status footer without typing.
        footer = self.screen().split('› ')[-1]
        expected = 'Goal paused' if status == 'paused' else 'Pursuing goal'
        if expected not in footer:
            raise UnsafeTarget('Goal UI acknowledgement missing')

    def rollout_records(self):
        # Passive verification only: never edits Codex history or uses a model API.
        home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
        files = list((home / 'sessions').rglob(f'*{self.thread}.jsonl'))
        if len(files) != 1:
            raise UnsafeTarget('unique readable rollout missing; submission needs manual verification')
        with open(files[0], encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                except json.JSONDecodeError:
                    continue
                yield record

    def input_recorded(self, message):
        for record in self.rollout_records():
            item = record.get('payload', {})
            if record.get('type') == 'response_item' and item.get('role') == 'user':
                if any(c.get('text') == message for c in item.get('content', [])):
                    return True
        return False

    def goal_identity(self):
        # Goal tool updates need not appear in the rollout. Query the durable
        # identity read-only; all lifecycle changes still go through native TUI.
        home = Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
        database = home / 'goals_1.sqlite'
        if database.exists():
            connection = None
            try:
                connection = sqlite3.connect(database.resolve().as_uri() + '?mode=ro',
                                             uri=True, timeout=5)
                connection.execute('PRAGMA query_only = ON')
                row = connection.execute(
                    'SELECT goal_id, created_at_ms FROM thread_goals WHERE thread_id = ?',
                    (self.thread,)).fetchone()
                if not row or not isinstance(row[0], str) or not row[0] or not isinstance(row[1], int):
                    raise UnsafeTarget('current Goal identity missing or invalid in read-only state')
                return {'goal_id': row[0], 'created_at_ms': row[1]}
            except sqlite3.Error as error:
                raise UnsafeTarget(f'read-only Goal identity unavailable: {error}') from error
            finally:
                if connection is not None:
                    connection.close()
        goals = [r['payload']['goal'] for r in self.rollout_records()
                 if r.get('payload', {}).get('type') == 'thread_goal_updated'
                 and r['payload'].get('threadId') == self.thread
                 and r['payload'].get('goal') is not None]
        if not goals or 'createdAt' not in goals[-1]:
            raise UnsafeTarget('original Goal identity not verifiable')
        return goals[-1]['createdAt']


def wait_idle(ui, deadline):
    while time.monotonic() < deadline:
        if ui.idle():
            time.sleep(0.35)
            if ui.idle():
                return
        time.sleep(0.5)
    raise UnsafeTarget('delivery deadline reached; result retained')


def worker(path):
    path = Path(path)
    with open(path.parent / 'worker.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        data = json.loads(path.read_text())
        lockdir = Path('/tmp') / f'codex-input-wake-{os.getuid()}'
        lockdir.mkdir(mode=0o700, exist_ok=True)
        if lockdir.is_symlink() or lockdir.stat().st_uid != os.getuid():
            raise UnsafeTarget('unsafe pane lock directory')
        key = hashlib.sha256((data['socket'] + '|' + data['pane']).encode()).hexdigest()
        with open(lockdir / (key + '.lock'), 'a') as pane_lock:
            try:
                fcntl.flock(pane_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                data.update(phase='attention', error='another wake job owns this pane; command not started')
                save(path, data)
                return 1
            return worker_locked(path)


def worker_locked(path):
    data = json.loads(path.read_text())
    if data['phase'] != 'prepared':
        raise RuntimeError('job already started; never replay a command automatically')
    def phase(value, **extra):
        now = time.time()
        data.setdefault('transitions', []).append({'phase': value, 'time': now})
        data.update(extra, phase=value, updated_at=now)
        save(path, data)
    try:
        ui = TmuxInput(data['socket'], data['pane'], data['thread'], data['identity'])
        # Native UI Goal controls may be used during generation. Waiting for an
        # idle boundary first would race against Goal auto-continuation.
        if not data['goal']:
            wait_idle(ui, time.monotonic() + data['delivery_timeout'])
        ui.verify_thread()
        if data['goal']:
            status, objective = ui.goal_summary()
            if status != 'active':
                raise UnsafeTarget('only an active Goal can opt into temporary suspension')
            identity = ui.goal_identity()
            created_at = identity['created_at_ms'] // 1000 if isinstance(identity, dict) else identity
            phase('pausing', goal_objective=objective, goal_identity=identity, goal_created_at=created_at)
            ui.set_goal('paused', objective)
            wait_idle(ui, time.monotonic() + data['delivery_timeout'])
        phase('starting')
        started = time.monotonic()
        if data.get('attach_pid'):
            pid = data['attach_pid']
            fd = pidfd_open(pid)
            if list(proc_identity(pid)) != data['attach_identity']:
                os.close(fd)
                raise UnsafeTarget('existing process changed before attachment')
            phase('running', pid=pid)
            poll = select.poll()
            poll.register(fd, select.POLLIN)
            poll.poll()
            os.close(fd)
            rc = None  # Non-parent cannot recover the original exit status.
        else:
            with open(path.parent / 'command.log', 'ab', buffering=0) as log:
                process = subprocess.Popen(data['command'], cwd=data['cwd'],
                                           stdin=subprocess.DEVNULL, stdout=log,
                                           stderr=subprocess.STDOUT, start_new_session=True)
                phase('running', pid=process.pid, process_identity=list(proc_identity(process.pid)))
                rc = process.wait()
        phase('completed', exit_code=rc, duration_seconds=round(time.monotonic()-started, 3))
        wait_idle(ui, time.monotonic() + data['delivery_timeout'])
        ui.verify_thread()
        if data['goal']:
            status, objective = ui.goal_summary()
            if status != 'paused' or objective != data['goal_objective'] or ui.goal_identity() != data['goal_identity']:
                raise UnsafeTarget('Goal changed during wait; completion retained without auto-resume')
        log_path = data.get('attach_log') if data.get('attach_pid') else str(path.parent / 'command.log')
        message = (f"Job {data['id']} finished; exit_code={rc if rc is not None else 'unknown'}; "
                   f"result={path}; log={log_path or 'not captured for adopted process'}; "
                   'Read the result and continue the original task. This is completion, not a claim of success.')
        # Commit before Enter: an ambiguous crash is never retried automatically.
        phase('submitting', message=message)
        ui.type_enter(message)
        phase('submitted')
        deadline = time.monotonic() + data['delivery_timeout']
        while not ui.input_recorded(message):
            if time.monotonic() >= deadline:
                raise UnsafeTarget('input not recorded; will not resend automatically')
            time.sleep(0.5)
        if data['goal']:
            wait_idle(ui, time.monotonic() + data['delivery_timeout'])
            ui.verify_thread()
            if ui.goal_identity() != data['goal_identity']:
                raise UnsafeTarget('original Goal was replaced after completion input')
            ui.set_goal('active', data['goal_objective'])
        phase('delivered', goal_restored=bool(data['goal']))
    except Exception as e:
        phase('attention', error=f'{type(e).__name__}: {e}', previous_phase=data['phase'])
        return 1
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='action', required=True)
    launch = sub.add_parser('start', help='detach a job and wake this exact interactive Codex pane on exit')
    launch.add_argument('--socket', default=os.environ.get('TMUX', '').split(',')[0] or None)
    launch.add_argument('--pane', default=os.environ.get('TMUX_PANE'))
    launch.add_argument('--thread', default=os.environ.get('CODEX_THREAD_ID'))
    launch.add_argument('--goal', action='store_true', help='explicit opt-in to UI pause/resume of original active Goal')
    launch.add_argument('--attach-pid', type=int)
    launch.add_argument('--attach-log', help='existing log path for an adopted process; never modified')
    launch.add_argument('--delivery-timeout', type=float, default=3600)
    launch.add_argument('--state-dir', type=Path, default=Path(__file__).parent / 'jobs')
    launch.add_argument('command', nargs=argparse.REMAINDER)
    internal = sub.add_parser('_worker')
    internal.add_argument('path')
    status = sub.add_parser('status')
    status.add_argument('path')
    args = p.parse_args()
    if args.action == '_worker':
        return worker(args.path)
    if args.action == 'status':
        print(Path(args.path).read_text())
        return 0
    cmd = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not all((args.socket, args.pane, args.thread)):
        p.error('socket, pane, and thread are required (or TMUX, TMUX_PANE, CODEX_THREAD_ID)')
    if bool(cmd) == bool(args.attach_pid):
        p.error('supply exactly one of a command after -- or --attach-pid')
    ui = TmuxInput(args.socket, args.pane, args.thread)
    job_id = 'wake-' + uuid.uuid4().hex[:12]
    directory = args.state_dir.resolve() / job_id
    directory.mkdir(parents=True, mode=0o700)
    path = directory / 'result.json'
    data = dict(id=job_id, phase='prepared', created_at=time.time(), cwd=os.getcwd(),
                socket=ui.socket, pane=ui.pane, thread=args.thread, identity=list(ui.identity),
                goal=args.goal, command=cmd, attach_pid=args.attach_pid,
                attach_log=str(Path(args.attach_log).resolve()) if args.attach_log else None,
                delivery_timeout=args.delivery_timeout)
    if args.attach_pid:
        data['attach_identity'] = list(proc_identity(args.attach_pid))
    save(path, data)
    with open(directory / 'supervisor.log', 'ab', buffering=0) as log:
        process = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), '_worker', str(path)],
                                   stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
    print(json.dumps({'job': job_id, 'supervisor_pid': process.pid, 'result': str(path)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
