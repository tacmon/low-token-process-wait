# Optional persistent routing

Add the following to your user-level or project AGENTS.md, adjusting the skill path if needed:

When a finite noninteractive job is expected to run for several minutes, or remains running after a few checks, read and apply the installed `low-token-process-wait/SKILL.md`. In Desktop prefer an official heartbeat attached to this same task: confirm creation, end the answer, check once per scheduled run, stay quiet while unchanged, verify completion and continue the original work, then retire the waiting automation. Do not keep polling or delegate a monitoring subagent. In a supported local interactive CLI, use the skill's process-exit supervisor. Preserve current execution permissions and already-running jobs. Obtain user authorization before changing Goal lifecycle; do not assume scheduled input resumes a paused Goal. Never substitute noninteractive Codex commands, SDKs or direct model clients for this workflow.
