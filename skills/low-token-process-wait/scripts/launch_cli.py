#!/usr/bin/python3
"""Prepare a local interactive TUI without changing its execution permissions."""
import os
from pathlib import Path
import shlex
import shutil
import sys
import uuid

COMMANDS = set('agents exec e review login logout mcp plugin app-server remote-control completion update doctor sandbox debug apply a queue archive delete migrate-rollouts unarchive cloud exec-server features help'.split())
VALUES = set('-c --config --enable --disable -m --model -p --profile -s --sandbox -C --cd --add-dir -a --ask-for-approval --local-provider'.split())
BOOLS = set('--strict-config --oss --approve-for-me --dangerously-bypass-approvals-and-sandbox --dangerously-bypass-hook-trust --worktree --search --no-alt-screen --no-daemon'.split())


def interactive(args):
    if any(a in ('-h', '--help', '-V', '--version', '--remote') or a.startswith('--remote=') for a in args):
        return False
    i = 0
    while i < len(args):
        a = args[i]
        if a == '--':
            return True
        if a in VALUES:
            i += 2
            continue
        if a in BOOLS or any(a.startswith(v + '=') for v in VALUES if v.startswith('--')):
            i += 1
            continue
        if a.startswith('-'):
            # Unknown/multivalue options: preserve upstream behavior without guessing.
            return False
        return a not in COMMANDS
    return True


def launch_argv(binary, args, tty):
    if not tty or not interactive(args):
        return [binary, *args]
    defaults = [flag for flag in ('--no-daemon', '--no-alt-screen') if flag not in args]
    cmd = [binary, *defaults, *args]
    if os.environ.get('TMUX'):
        return cmd
    if not shutil.which('tmux'):
        raise RuntimeError('tmux unavailable; automatic completion wakeup cannot be prepared')
    # One server per launch inherits this invocation's environment, avoiding stale
    # PATH/profile variables from an older server. No credentials are inspected.
    socket = 'codex-wake-' + uuid.uuid4().hex[:12]
    config = str(Path(__file__).with_name('codex.tmux.conf'))
    return ['tmux', '-L', socket, '-f', config, 'new-session', '-s', 'codex',
            '-c', os.getcwd(), shlex.join(cmd)]


def main():
    binary, *args = sys.argv[1:]
    cmd = launch_argv(binary, args, sys.stdin.isatty() and sys.stdout.isatty())
    os.execvp(cmd[0], cmd)


if __name__ == '__main__':
    main()
