#!/usr/bin/env python3
import hashlib, json, os, sys, time

ROOT = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(ROOT, "data.json")
PROGRESS = os.path.join(ROOT, "progress.jsonl")
CHECKPOINT = os.path.join(ROOT, "checkpoint.json")
RESULT = os.path.join(ROOT, "result.json")

def atomic_json(path, value):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(value, f, ensure_ascii=False, sort_keys=True)
        f.write("\n")
    os.replace(tmp, path)

def main():
    started = time.time()
    rows = [{"id": i, "value": i * i} for i in range(100)]
    atomic_json(DATA, rows)
    open(PROGRESS, "w", encoding="utf-8").close()
    for stage in range(1, 13):
        time.sleep(60)
        digest = hashlib.sha256(open(DATA, "rb").read()).hexdigest()
        record = {"stage": stage, "time": time.time(), "sha256": digest}
        with open(PROGRESS, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, sort_keys=True) + "\n")
        atomic_json(CHECKPOINT, record)
    ended = time.time()
    digest = hashlib.sha256(open(DATA, "rb").read()).hexdigest()
    atomic_json(RESULT, {"status": "success", "completed_stages": 12,
                         "started": started, "ended": ended,
                         "elapsed": ended - started,
                         "final_data_sha256": digest})

if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"pipeline failure: {exc}", file=sys.stderr)
        raise
