# 12-minute Desktop scheduling experiment

Install the skill and paste this into a new ordinary Desktop task, without Goal mode. The delay is intentional and uses little CPU. Keep the computer and app running; do not send another message for about 16 minutes.

```text
Use $low-token-process-wait to build a small project named scheduled-wake-demo.

Create a 10-row CSV of product names and prices. Write a standard-library processor that reads the CSV, waits 12 minutes locally (logging progress once per minute), then writes result.json containing count, total, average, and start/end times. Persist a trustworthy exit record. Start it exactly once in a way that survives the end of this answer; save its real PID, process identity, host, and log paths.

Create an official Desktop heartbeat attached to this same task, checking every 3 minutes. Confirm the automation tool returned success and retain its actual id. Then end this answer. Do not enable Goal, use a monitoring subagent, or poll in the foreground. If official scheduling cannot be created, report failure instead of substituting another model-access route.

On each scheduled run check once. If unfinished, end that run and await the next schedule; stay quiet while unchanged. When finished, verify the exit record and statistics, generate report.md with the count, total, average and timestamps, then pause or delete this waiting automation. Report any failure or required user action without automatically restarting the program.

I will not send another prompt during the wait. Continue through the official scheduled task.
```

## Pass conditions

- The original answer ends while the local job keeps running.
- A real same-task schedule exists, rather than only a promise to check later.
- Scheduled runs check once and return; no inner waiting loop or duplicate program launch.
- The report is generated without another user prompt after at least 720 seconds of actual processing time.
- The waiting automation is retired after completion.

Scheduling delays are possible; exact completion at minute 12 is not required. This verifies explicit scheduling. Repeat without the scheduling instructions to evaluate implicit skill selection separately. Test Goal pause/resume only as a separate experiment.

The previous `examples/long-pipeline` remains as a standalone workload; it is not automatically wired into Desktop scheduling.
