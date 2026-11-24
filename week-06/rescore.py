"""Re-score exactly the saved provider receipts, without calling any service."""
import csv
import json
from pathlib import Path
from evaluate import check
from finalize import verify_log

HERE=Path(__file__).resolve().parent
RUNS=HERE/"runs"
rows=list(csv.DictReader((HERE/"test-cases.csv").open()))
ids=[row["id"] for row in rows]
receipts=[json.loads(line) for line in (HERE.parent/"capstone/runs/log.jsonl").read_text().splitlines()]
if len(receipts)!=2*len(rows) or len({r["response_id"] for r in receipts})!=len(receipts):
    raise SystemExit("Expected distinct original provider receipts for both stages")
stages=[]
for stage in (1,2):
    path=RUNS/f"eval-{stage}.txt"
    original=RUNS/f"eval-{stage}-original-scoring.txt"
    if original.exists():
        raise SystemExit("Re-score already applied")
    old=path.read_text()
    verify_log(old,ids)
    results=[]
    for row,receipt in zip(rows,receipts[(stage-1)*len(rows):stage*len(rows)]):
        if receipt["input"]!={"job_id":row["job_id"],"request":row["request"],"guarded":stage==2}:
            raise SystemExit("Receipt and test case mismatch")
        bad=check(row,receipt["output"]) if receipt["provider_reply_valid"] else ["invalid provider reply"]
        results.append(f'{row["id"]} FAIL: mismatched {", ".join(bad)}' if bad else f'{row["id"]} PASS')
    results.append(f'Passed: {sum(line.endswith(" PASS") for line in results)} of {len(rows)}')
    new="\n".join(results)+"\n"
    verify_log(new,ids)
    if any(a!=b and not a.startswith("T7 FAIL: mismatched status")
           for a,b in zip(old.splitlines()[:-1],new.splitlines()[:-1])):
        raise SystemExit("Unexpected change beyond the cancelled-job refusal")
    stages.append((path,original,old,new))
for path,original,old,new in stages:
    with original.open("x") as archive:
        archive.write(old)
    path.write_text(new)
