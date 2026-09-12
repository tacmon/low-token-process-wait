# 12-minute stability test prompt

Paste this into a new Codex session after installing the skill:

```text
Use $low-token-process-wait to run the reference test in examples/long-pipeline. Execute it directly.

Run `python3 -m py_compile` first, then launch `./launcher.sh` exactly once. It must run 12 stages, each sleeping 60 seconds, and use only one standard-library process. Do not use GPU, network, extra dependencies, threads, process pools, or busy waiting. Preserve the PID, log path, and real child exit code.

When the launch tool yields before completion, create exactly one clean-context subagent with fork_turns="none" and an economical low-reasoning model. Pass only the exact PID, command identity, host/namespace, detector path, and terse return contract.

After starting the subagent, stop thinking and doing work in the main session. Wait for the subagent's explicit final report that the process has ended; only then continue. Do not probe the PID, GPU, logs, progress files, or result files during the wait. If a subagent wait window times out, renew the same subagent wait; call no generic exec-cell wait API.

After the subagent returns, verify the actual exit code, 12 ordered progress records, checkpoint/result stage 12, final SHA-256, and elapsed time of at least 720 seconds. Write test-report.md. Distinguish pipeline success from monitor delivery and waiting-workflow compliance. Record token usage as unmeasured if the platform does not expose attributable data. Do not rerun automatically after a failure.
```
