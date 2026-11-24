"""Generate the reflection and exact example from verified genuine runs only."""
import csv
import json
from pathlib import Path
import re

HERE = Path(__file__).resolve().parent
REPO = HERE.parent

def verify_log(text, ids):
    rows = text.splitlines()
    parsed = [re.fullmatch(r"(\S+) (PASS|FAIL)(?:: .+)?", row) for row in rows[:-1]]
    if not all(parsed) or [m[1] for m in parsed] != ids:
        raise ValueError("Case IDs or results do not match")
    n = sum(m[2]=="PASS" for m in parsed)
    if rows[-1] != f"Passed: {n} of {len(ids)}":
        raise ValueError("Incorrect total")
    return n, [m[1] for m in parsed if m[2]=="FAIL"]

def main():
    with (HERE/"test-cases.csv").open() as f:
        rows = list(csv.DictReader(f))
    ids = [r["id"] for r in rows]
    first, second = [(HERE/f"runs/eval-{n}.txt").read_text() for n in (1,2)]
    a,_ = verify_log(first,ids)
    b,bad = verify_log(second,ids)
    packets = [json.loads(line) for line in (REPO/"capstone/runs/log.jsonl").read_text().splitlines()]
    required = ("timestamp","model","input","output","input_tokens","output_tokens","seconds")
    if (len(packets)!=len(rows)*2 or not all(all(k in p for k in required) for p in packets)
            or len({p["response_id"] for p in packets})!=len(packets)
            or not all(p["response_id"].startswith("msg_") and p["input_tokens"]>0 and
                       p["output_tokens"]>0 for p in packets)):
        raise ValueError("Genuine request receipts could not be verified")
    for i,p in enumerate(packets):
        row = rows[i%len(rows)]
        if p["input"] != {"job_id":row["job_id"],"request":row["request"],"guarded":i>=len(rows)}:
            raise ValueError("Receipt inputs do not match the test cases and stage")
    fixes={
        "T1":"separate scope, access, and schedule into individually cited fields",
        "T2":"require structured output from the API and retest the declined-add-on case",
        "T3":"make the record precedence explicit and validate scope against the latest approval",
        "T4":"make the newest access note the only eligible source for that field",
        "T5":"add an input release check for requests to send information or take outside action",
        "T6":"return a consistent hold whenever the only date is a customer proposal",
        "T7":"test cancellation precedence at the handoff rather than relying just on the draft",
        "T8":"recover the current valid dispatch confirmation when a newer proposal conflicts"
    }
    nxt = (f"{bad[0]}: I'd {fixes[bad[0]]}." if bad else
           "None. I'd add a cancelled job that was later rebooked, to check that a new approval overrides the cancellation.")
    text = f"""## What I Built

At our tree service, the person handing off a job has to check what the customer accepted, where the crew can get in, and whether a date is actually booked. I made a small tool that pulls the job's records over a read-only MCP connection and drafts those details for someone in the office to check. I used eight fictional cases, including declined extra work, updated access, and a date that dispatch cancelled. The evaluation compares the reply fields with what I expected before running the tool. The first scorer was too strict about the cancelled job: it failed a clean refusal even though the test only required that the tool never use the cancelled date or its source. I kept both original reports and re-scored the same model receipts with that safe refusal allowed. After that correction the guarded run had fewer passes overall, mainly because more replies did not conform to the required structure. The guard stops unsupported dates; it does not repair malformed replies.

## Why This Approach

Tool tested: Capstone. I wanted to test the same kind of information I'd hand to a crew.
Guardrail: Output checks that the date and source match the current dispatch confirmation. If they don't, it holds back the handoff for someone in the office to review.

## Example Run

```text
{second}```

## Reflection

First evaluation: {a} of {len(ids)}
After the guardrail: {b} of {len(ids)}
Next fix: {nxt}
"""
    (HERE/"writeup.md").write_text(text)
    print(f"Verified {len(packets)} distinct model receipts; baseline {a}/{len(ids)}; guarded {b}/{len(ids)}.")
    guard_fails = {row["id"] for row in rows if row["type"]=="Guardrail"}.intersection(bad)
    if guard_fails:
        print("Review before publishing: guarded cases failed:", ", ".join(sorted(guard_fails)))
        return 1
    return 0

if __name__=="__main__":
    raise SystemExit(main())
