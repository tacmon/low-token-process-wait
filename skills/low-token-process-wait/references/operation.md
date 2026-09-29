# Operation and optional CLI launcher

Resolve the installed skill directory first. The standard location is `${CODEX_HOME:-$HOME/.codex}/skills/low-token-process-wait`; custom installations should use their actual directory and a suitable Python 3 executable.

## Desktop

Use the host's official automation tool, not a hand-written automation file. Create a heartbeat attached to the current task and retain its actual automation id so it can be retired after completion. Verify the job survives the current turn. Preserve the host, PID/start identity, log paths and exit record; PID disappearance alone is not success.

Creation failure means scheduling is not active. Do not silently switch to a new task or repeated foreground checks. Follow the user's notification preference. A scheduled run can continue the original task, but paused Goal restoration is a separate, unverified Desktop integration.

## Optional zsh entry point

After installing the skill, users who want the ordinary `codex` command to prepare tmux can add this to their own `.zshrc`:

```zsh
codex() {
    local codex_wake_binary
    codex_wake_binary=$(whence -p codex) || return
    python3 "${CODEX_HOME:-$HOME/.codex}/skills/low-token-process-wait/scripts/launch_cli.py" "$codex_wake_binary" "$@"
}
```

Open a new terminal. Interactive invocations prepare a separate tmux server and use `--no-daemon` so the CLI tools can inherit pane identity, and `--no-alt-screen` for inline scrollback. Existing tmux panes are not nested. Arguments, working directory, sandbox and approval choices are preserved. Help/version, noninteractive invocations, remote endpoints, and unrecognized options conservatively pass through. This launcher does not itself monitor commands; the skill must choose the supervisor.

Direct executable paths and other shells bypass the function. Installing the skill does not automatically install this function.

## Supervisor

Use `wake.py start --state-dir PROJECT_DIRECTORY -- COMMAND ARGS`, adding `--goal` only for an authorized active Goal. Locator defaults come from TMUX, TMUX_PANE and CODEX_THREAD_ID; missing values require explicit verified socket, pane and thread parameters. For an already-running job use `--attach-pid REAL_PID --attach-log ABSOLUTE_LOG` instead of a command; the log argument is optional and the adopted process is never restarted.

Retain the job id, supervisor PID and result path. End the model answer after launch; do not wait or poll. The supervisor pauses a requested Goal through native input, waits for the answer to finish, runs/waits for the job, records exit status, submits one completion message, and restores the original Goal once input is recorded and the UI appears idle. Exact ordering relative to the completion response is not guaranteed: the live test first read the Goal after restoration had already occurred.

`wake.py status RESULT_JSON` reads state. `delivered` indicates recorded input and, if requested, verified Goal restoration; it does not mean job success. `attention` requires reviewing the actual failure and whether input was already submitted, not rerunning the command blindly. Non-child exit status is unknown.

Restricted sandboxes can hide host process identity or block tmux. Registration must fail rather than bypass these restrictions. Full-access CLI worked in isolated live tests; permissions must remain the user's choice. Default English UI is tested; narrow panes, drafts, menus and changed identities can refuse delivery. Keep the host and CLI alive. No cross-restart recovery is provided, and at-most-once conservative delivery is not an exactly-once crash guarantee.

## Remove the optional launcher

Remove only the function you added, retaining unrelated shell settings. Removing the skill/function does not stop existing background work or retire Desktop automations; manage those explicitly.


## Goal identity compatibility

Goal updates made through model tools may not emit thread_goal_updated in the rollout. The supervisor now reads goal_id and created_at_ms from goals_1.sqlite using SQLite mode=ro and query_only. Lifecycle changes still occur only through the native input box. If a database exists but is unreadable, incompatible or missing the current Goal, stale rollout events cannot override it. The legacy rollout check remains only for installations without that database.

A 180-second live CLI retest passed: exit code zero, correct statistics, one recorded completion message, unchanged Goal identity, automatic restoration and continuation to completion. Precise restoration ordering, independent UI audit and zero model activity throughout that run were not independently established.

## WezTerm-style terminal behavior

The optional launcher uses scripts/codex.tmux.conf for its dedicated server. It sources the existing user tmux config, then enables mouse support, hides the status bar, gives new panes 100000 lines of history, configures clipboard/RGB/focus support, and reduces Escape delay. Ctrl+B is passed to the application, while WezTerm handles its existing tab/pane shortcuts. A normal Codex exit returns to outer zsh instead of leaving a dead pane. Existing external tmux sessions are not reconfigured by the launcher.

Wheel-up enters history reading; Escape or q returns to input. Drag-selection release copies through the terminal clipboard mechanism. Ctrl+Shift+V still pastes in WezTerm; Shift+drag selects natively for Ctrl+Shift+C. The supervisor waits while tmux is in reading/copy mode and will not interrupt selection.

The new history length and inline mode apply only to newly launched/resumed sessions, not retroactively. Font, input method, WezTerm keys and tabs are unchanged. Dedicated-server configuration and history limits are tested without model calls; real GUI clipboard pasting and the complete Goal flow with the new inline mode remain unverified. This approximates native terminal behavior rather than promising identical behavior.

## Desktop diagnostic result

A real same-task heartbeat executed while the original Goal remained paused, with objective and creation identity unchanged. This confirms scheduled callback execution in that situation, not automatic Goal activation. The diagnostic schedule was retired. Independent scheduler-operation auditing and a complete long-workflow Desktop cleanup test remain unverified. Explicit isolated diagnostics may test callback execution without requiring a missing resume tool.
