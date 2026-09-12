# low-token-process-wait

**English** | [简体中文](README.zh-CN.md)

A Codex skill for finite jobs that take more than a few minutes. It delegates exact-PID waiting to one clean-context subagent so a large main conversation does not repeatedly probe the process.

The skill does not change Codex host scheduling or promise infinite synchronous blocking. It makes the waiting contract explicit:

> After starting the subagent, stop thinking and doing work in the main session. Wait for the subagent's explicit final report that the process has ended; only then continue.

## Install

```bash
cp -r skills/low-token-process-wait ~/.codex/skills/
```

Then use `$low-token-process-wait`, or let Codex select it for a finite long-running computation.

The detector monitors one exact PID and prints a heartbeat every minute:

```bash
python3 ~/.codex/skills/low-token-process-wait/scripts/wait_pid.py \
  --pid 12345 --interval 60
```

It prints `执行中` while the process is alive and `执行完毕` after exit. It never kills the target. A PID absent at attachment is reported as `ALREADY_ABSENT`, not success.

## Included test

See [prompts/12-minute-test.md](prompts/12-minute-test.md) for a prompt that creates a low-resource, no-GPU, 12-stage test pipeline. The reference implementation is in [examples/long-pipeline](examples/long-pipeline).

The test should separately report pipeline success, subagent delivery, main-session standby, timeout renewals, rejected tool calls, and token usage. Do not infer token savings when usage data is unavailable.
