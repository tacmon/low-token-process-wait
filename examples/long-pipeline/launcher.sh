#!/usr/bin/env bash
set -u
cd "$(dirname "$0")"
log=pipeline.log
python3 pipeline.py >"$log" 2>&1 &
pid=$!
printf '%s\n' "$pid" > pipeline.pid
wait "$pid"
status=$?
python3 - "$status" <<'PY'
import json, sys, time
with open("launcher-record.json", "w", encoding="utf-8") as f:
    json.dump({"exit_code": int(sys.argv[1]), "recorded_at": time.time()}, f)
    f.write("\n")
PY
exit "$status"
