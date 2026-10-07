# Desktop validation and demonstration

## Verified on 2026-10-07

Codex Desktop Linux 26.917.71314, build 10954, prod; ordinary task with no Goal.

- The foreground answer ended after a 2-minute same-task heartbeat was created.
- A 90-second worker in a retained execution session started at 12:48:02 UTC and wrote its result at 12:49:32 UTC.
- The scheduler delivered a heartbeat to the original task at 12:49:29 UTC. By the single result check at 12:49:48 UTC, the worker had completed. This is periodic scheduling, not a process-exit-triggered callback.
- The callback checked the worker's recorded zero status and expected output, wrote verification evidence, then paused the heartbeat through the official tool.
- A first detached Popen launch produced no startup record. The retained execution session did. Do not assume detachment alone survives the sandbox/tool lifecycle; never duplicate an already-started job.

This establishes a same-task scheduled continuation across turns and completed result handling. It does not establish paused Goal activation, OS wake-from-sleep, exact timing, crash recovery, or zero model usage across the waiting interval.

## Five-minute demonstration

Use an isolated project subdirectory and a finite worker that runs for 300 seconds. Record a stable run id, host, namespace-scoped PID, UTC and monotonic start/end times, logs, expected output and exit status. Prefer a wrapper that records the actual child return code. Start through an execution facility that has demonstrated cross-turn survival; retain its session handle separately from the PID.

Create a heartbeat on the current task, normally every minute for this explicitly requested short demonstration. Include the result paths, expected output, deadline (for example ten minutes), and next action. End the answer once creation is confirmed. Each callback reads once, records its timestamp and state, then ends if work is incomplete. Do not poll or sleep inside model turns. Respect notification preferences.

After completion, verify the actual exit status, at least 300 seconds of monotonic elapsed work, and the output. Perform a small follow-up action, such as producing a summary artifact from the output, to demonstrate continuation. Pause or delete the heartbeat via the official tool and record confirmation. On timeout/failure, report the specific failed stage and retire the demo schedule without restarting the job.

No Goal is required. If Goal lifecycle testing is explicitly requested, treat callback execution and Goal restoration as separate checks and use only supported lifecycle controls.

## Sources

- [Official scheduled tasks](https://learn.chatgpt.com/docs/automations?surface=app)
- [Official long-running work](https://learn.chatgpt.com/docs/long-running-work)
