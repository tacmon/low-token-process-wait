---
name: low-token-process-wait
description: Reduce main-conversation token waste when running finite programs expected to take over five minutes, such as model training, repeated tests, or dataset generation. When execution yields an unfinished session, delegate monitoring to one clean-context economical subagent and wait for its completion instead of repeatedly checking the process in the main conversation.
---

# Low-token process waiting

## Trigger and intent

Apply automatically for finite computational jobs estimated to take at least five minutes, or when a job unexpectedly becomes long-running. The user wants unattended continuation with minimal repeated input from the large main conversation. Do not apply to permanent servers or interactive programs awaiting input.

Try the normal foreground execution once. If the tool yields while the job remains active, use this workflow instead of repeated main-agent status probes. If the job is already running, attach to it; never restart it to simplify monitoring.

## Prepare once

1. Identify the actual job PID, host, and PID namespace, plus the execution session ID and result/log paths. Prefer the launcher that waits for all workers for distributed jobs. A GPU worker exiting is not necessarily completion of the whole job.
2. Verify the exact PID and command once. Do not use a broad Python executable pattern or GPU power as the completion condition. If only a pattern is known, resolve it once to the intended PID; resolve ambiguous matches before waiting.
3. Use the bundled Linux detector, or adapt a detector on the execution host if necessary:

   ```bash
   python3 ~/.codex/skills/low-token-process-wait/scripts/wait_pid.py --pid PID --interval 60
   ```

   It prints the current time and `执行中` every minute, then `执行完毕` on process exit. Linux pidfd waits on the specific process; older Python versions use local `/proc` checks with process start time and zombie detection. The fallback detects exit within one interval. It does not terminate the target. An absent PID at attachment is reported distinctly; it is not evidence of successful training. The minute heartbeat is produced by the process, not by model turns.
4. Before launching a long job, validate the launcher itself. If it promises to persist the child's exit code or write a completion record, run a short smoke test and confirm that record is actually created and contains the child's exit code. A launcher-recording failure is a test/workflow failure even when the child job succeeds.

## Delegate monitoring

Spawn exactly one subagent with `fork_turns="none"`. Explicitly choose the cheapest suitable model from the actual exposed model options when pricing is known. Otherwise default to `gpt-5.6-luna` with `reasoning_effort="low"` when available, as an economical candidate, not a verified price minimum. Do not research pricing on every wait. If unavailable, use a known economical available model; do not silently select an expensive model. If no suitable model or delegation exists, explain the limitation briefly instead of reverting to repeated main-agent probes.

Pass only this compact assignment, replacing placeholders with concrete values:

```text
Your only task is waiting for a process to exit. Do not load project history,
read skills, analyze training, modify files, restart/kill jobs, or spawn agents.
Host/namespace: HOST. Exact PID: PID. Command identity: COMMAND.
Run: python3 ABSOLUTE_DETECTOR_PATH --pid PID --interval 60
If the command yields, retain its session ID and wait on that same session
using the longest permitted wait consistent with higher-priority instructions.
Do not start another detector, run nvidia-smi, or inspect training logs.
The detector emits a heartbeat every minute; this is not a request to reason
or report every minute. After each detector output/session continuation, use
the platform's documented wait operation before inspecting again. Prefer a
600-second wait window; use 120 seconds when 600 is unavailable, then 60
seconds only as a fallback. Do not immediately re-run the detector after it
returns a heartbeat. Keep tool output and reasoning minimal. Do not send
heartbeat messages to the parent. Wait until the detector exits.
Return only: PROCESS_EXITED pid=PID, ALREADY_ABSENT pid=PID, or
MONITOR_ERROR pid=PID reason=SHORT_REASON. Process exit is not job success.
```

The detector must run on the target host; local PID checks cannot monitor a remote process. Do not assume the child can access a parent's tool session. It can independently run the detector when it shares the host and namespace.

The following explicit instruction is intentional and should be included when the host is prone to resuming main-agent reasoning after delegation: "After starting the subagent, stop thinking and doing work in the main session. Wait for the subagent's explicit final report that the process has ended; only then continue." This is a behavioral prompt reinforcement, not a claim that it changes host-level scheduler limits.

## Main-agent standby

Once the subagent is spawned, enter `WAITING_FOR_SUBAGENT` state. In that state the only permitted operational action is the documented subagent wait call; do not choose a generic process/session wait API by name similarity. Keep the subagent identity and its wait cursor/target unchanged until it returns. Leave this state only when the subagent returns, the user interrupts, or a higher-priority system event requires action.

Send or retain this explicit standby contract in the main turn: **"Subagent has started. Main session: stop thinking, stop probing, and stop all other work. Remain waiting until the subagent explicitly reports PROCESS_EXITED, ALREADY_ABSENT, or MONITOR_ERROR. Do not continue before that report."** Do not interpret a tool-window timeout as permission to resume analysis; it only permits renewing the same subagent wait.

Immediately wait for the child with `wait_agent` (or the platform's explicitly documented subagent-wait equivalent). Use the longest permitted wait consistent with higher-priority instructions. If it returns a timeout, call the same subagent-wait tool again with the same target; describe this only as a "subagent wait-window timeout". It does not indicate process completion or failure. Do not use `functions.wait` for a subagent: that interface is only for a real still-running `functions.exec` cell and requires its non-empty `cell_id`. Never invent, omit, or leave `cell_id` empty. On timeout with no result, only renew the same subagent wait with minimal reasoning. Do not run process/GPU/log checks, request repeated child status, create timers, perform unrelated work, or spawn another watcher. Do not turn detector heartbeats into user-facing updates unless higher-priority instructions require them.

Maintain a minimal wait event record in the main turn: wait started, each wait-window timeout, any tool/interface error (including rejected calls), and the child's final result. Do not probe the target to explain a timeout. If a wrong wait interface was attempted, disclose it in the final report even when it had no effect on the job.

If a goal is active, leave it active and pending; monitoring is not goal completion. New user instructions can interrupt waiting. Stopping the monitor alone does not authorize killing training.

On the child result, consume the original execution session's final status once if available, and inspect final logs/results to determine success or failure. Continue the original task/goal. An exited or missing PID does not establish a successful exit code. If the detector fails, diagnose that specific error; do not silently resume main-agent polling.

## Honest limits

This skill reduces expensive main-context checks; it does not override host scheduling, tool deadlines, context inherited outside conversation history, or higher-priority progress instructions. Wait timeouts can still cause model turns in both agents. Do not promise zero tokens, indefinite synchronous blocking, a precise saving percentage, or automatic resumption after the host ends the turn. A child context also grows with repeated tool calls; keep its output terse. Do not duplicate watchers to work around lifecycle limits.

Success of the process and success of the waiting workflow are separate claims. The final report must distinguish the job's exit/result from monitor delivery, main-agent standby behavior, timeout renewals, and any rejected or misrouted tool calls. If usage data is unavailable, record it as unmeasured; do not infer savings from wait counts.
