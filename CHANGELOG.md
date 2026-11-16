# Changelog

## v0.6.1

- Remove the 30-minute cap for credible ETA; check at estimated completion and re-estimate if unfinished.
- Keep 30-minute recurring checks only for unknown-time backoff.
- Preserve early CLI exit wakeups and document delayed failure detection for scheduled waits.
- Synchronize bilingual documentation; long-duration adaptive scheduling remains unverified.

## v0.6.0

- Prefer credible remaining-time estimates, capped at 30 minutes, over fixed polling.
- Fall back to 30 seconds, 1/2/5/10/30 minutes, then repeat 30 minutes when ETA is unknown.
- Re-estimate each check, persist waiting state and verify actual schedule updates.
- Respect current host scheduling restrictions; retain CLI process-exit supervision.
- Refresh English/Chinese documentation; adaptive live timing remains unverified.

## v0.3.0

- Read durable Goal identity through read-only SQLite when tool updates omit rollout events; refuse stale log fallback when a database exists.
- Add five identity regression cases and three launcher tests (23 automated tests total), and document the successful 180-second same-Goal CLI retest.
- Include dedicated tmux configuration: mouse/clipboard, hidden status, 100000-line history, application Ctrl+B and normal CLI exit behavior.
- Default optional launch to inline scrollback; document new-session requirements and unverified full Goal flow under that display mode.
- Record actual Desktop heartbeat execution with Goal still paused, and permit scoped diagnostics without claiming automatic restoration.
- Correct completion-response ordering claims and retain privacy-safe, portable instructions.

## v0.2.0

- Prefer official Desktop heartbeat follow-ups attached to the original task.
- Replace the subagent-monitoring workflow with one check per scheduled run and quiet waiting.
- Continue the original work after verified completion and retire its waiting automation.
- Add Linux/tmux CLI process-exit supervision, same-input-box completion delivery and authorized original Goal pause/resume.
- Add an optional zsh launcher, 15 automated supervisor tests and a 12-minute Desktop experiment.
- Document sandbox/layout/crash boundaries and distinguish Desktop schedule creation from unverified end-to-end cleanup and Goal lifecycle support.
- Use portable installation paths; no user project data or screenshots are included.
