# low-token-process-wait

**English** | [简体中文](README.zh-CN.md)

A Codex skill for finite jobs that run for minutes or hours. **Desktop prefers official scheduled follow-ups in the same task.** Linux interactive CLI can use a local process-exit supervisor that submits a completion message through the original input box.

This version replaces the previous subagent-monitoring workflow. No monitoring subagent is required.

## Install

Copy `skills/low-token-process-wait` into `${CODEX_HOME:-$HOME/.codex}/skills/`, then start a new Codex task. You can invoke `$low-token-process-wait` explicitly. For persistent automatic routing, add the instructions in [AGENTS.integration.md](AGENTS.integration.md) to your user-level or project-level AGENTS.md.

Installation does not automatically change your shell, permissions, providers, or authentication.

## Desktop: scheduled follow-ups

When a finite job will take several minutes, Codex should:

1. Make sure the job survives the end of the current answer; record its identity, host, logs, and exit/result records.
2. Use the available official automation tool to create or update a **heartbeat attached to the current task**. Typically check every 30 minutes for multi-hour work, or every 5–10 minutes for shorter work.
3. End the current answer after creation is confirmed.
4. Check once per scheduled run. Remain quiet when nothing needs attention. Verify completion, continue the original work, then pause/delete the waiting automation.

Keep the computer and Desktop app running. Scheduled checks run the model and can be delayed; they do not promise zero tokens or immediate process-exit detection. Available tooling depends on the host. See [official scheduled-task documentation](https://learn.chatgpt.com/docs/automations).

**Goals have a separate lifecycle:** scheduled input is not proof that a paused Goal resumes. Do not promise Desktop Goal pause/resume unless the host's actual behavior is verified.

## CLI: process-exit wakeup

Requires Linux, Python 3, tmux, the default English interactive CLI layout, and permission to access the target pane/processes. In an appropriately configured pane, `TMUX`, `TMUX_PANE`, and `CODEX_THREAD_ID` bind the supervisor to the original task:

```bash
python3 "${CODEX_HOME:-$HOME/.codex}/skills/low-token-process-wait/scripts/wake.py" start \
  --state-dir "$PWD/.codex-wake-jobs" -- python3 your_job.py
```

Add `--goal` before `--` only when the user authorizes temporary pause/resume of the original active Goal. Adopt existing work with `--attach-pid REAL_PID`; never restart it merely to monitor it. Adopted non-child exit codes are reported as unknown.

The supervisor waits locally for actual exit, then types a result message and sends Enter into the original CLI. It uses no noninteractive Codex commands, SDK, app-server client, or model HTTP requests. Goal restoration is supported in the tested CLI environment.

See [operation and optional launcher setup](skills/low-token-process-wait/references/operation.md). Restricted sandbox environments may hide host PIDs or block tmux; registration then fails without changing permissions. Tested full-access CLI worked; this is not a requirement to silently elevate access.

## Evidence and limits

- CLI: 15 automated tests; a 65-second live run recorded zero model turn starts during execution and one completion input, preserving the original Goal. A separate live run verified a job launched by the agent itself.
- Desktop: the user reported successful activation in real work; the supplied UI showed a same-task 30-minute schedule. This establishes creation, not completed end-to-end execution or automatic cleanup.
- No automatic recovery across host/supervisor crashes. Ambiguous submissions are not blindly retried. Drafts, changed task/Goal identities, and unrecognized UI layouts can prevent delivery.

Run automated tests without model calls:

```bash
python3 -m unittest discover -s tests -v
```

Try [the 12-minute Desktop experiment](prompts/12-minute-test.md) to verify scheduled continuation on your own installation.
