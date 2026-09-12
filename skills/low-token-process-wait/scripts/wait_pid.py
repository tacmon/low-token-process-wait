#!/usr/bin/env python3
"""Wait for an exact Linux process without polling through the language model."""

import argparse
import math
import os
import select
import sys
import time


def identity(pid):
    try:
        with open(f'/proc/{pid}/stat') as stream:
            fields = stream.read().rsplit(')', 1)[1].split()
        return None if fields[0] in ('Z', 'X') else fields[19]
    except FileNotFoundError:
        return None


def fallback(pid, interval):
    initial = identity(pid)
    if initial is None:
        print(f'ALREADY_ABSENT pid={pid}', flush=True)
        return 3
    while identity(pid) == initial:
        print(time.strftime('%Y-%m-%d %H:%M:%S') + ' 执行中', flush=True)
        time.sleep(interval)
    print(time.strftime('%Y-%m-%d %H:%M:%S') + ' 执行完毕', flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--interval', type=float, default=60)
    args = parser.parse_args()
    if args.pid <= 0 or not math.isfinite(args.interval) or args.interval <= 0:
        parser.error('pid and interval must be positive; interval must be finite')
    if not hasattr(os, 'pidfd_open'):
        try:
            if not os.path.isdir('/proc/self'):
                raise OSError('Linux /proc is required')
            return fallback(args.pid, args.interval)
        except (OSError, IndexError) as exc:
            print(f'MONITOR_ERROR: {exc}', file=sys.stderr)
            return 2
    try:
        fd = os.pidfd_open(args.pid)
    except ProcessLookupError:
        print(f'ALREADY_ABSENT pid={args.pid}', flush=True)
        return 3
    except OSError as exc:
        print(f'MONITOR_ERROR: {exc}', file=sys.stderr)
        return 2

    try:
        while True:
            if select.select([fd], [], [], 0)[0]:
                break
            print(time.strftime('%Y-%m-%d %H:%M:%S') + ' 执行中', flush=True)
            if select.select([fd], [], [], args.interval)[0]:
                break
        print(time.strftime('%Y-%m-%d %H:%M:%S') + ' 执行完毕', flush=True)
        return 0
    finally:
        os.close(fd)


if __name__ == '__main__':
    sys.exit(main())
