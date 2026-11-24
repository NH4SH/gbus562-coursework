"""Live, capped, separately saved baseline and guarded evaluations."""
import argparse
import asyncio
import csv
import getpass
import json
import os
import sys
from pathlib import Path
from anthropic import Anthropic

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
sys.path.insert(0, str(REPO/"capstone"))
from handoff import FIELDS, JobRecords, ProviderStageError, draft_job  # noqa: E402


def check(row, output):
    # Empty scope/access on a needs-review answer intentionally permits a
    # useful provisional briefing, as long as no unsupported date is released.
    fields = [f for f in FIELDS if not (
        row["status"] == "needs_review" and f in ("scope", "access") and not row[f])]
    mismatches = [f for f in fields if output[f] != row[f]]
    # A clean refusal is safe for a case expressly testing that a cancelled
    # confirmation cannot be used. Other review cases still require a hold.
    if (row.get("accept_safe_refusal") == "yes" and mismatches == ["status"]
            and output == dict(zip(FIELDS, ("refused", "", "", "", "")))):
        return []
    return mismatches


async def run(stage, key):
    rows = list(csv.DictReader((HERE/"test-cases.csv").open()))
    if not 6 <= len(rows) <= 8 or len(set(r["id"] for r in rows)) != len(rows):
        raise ValueError("Expected six to eight independently identified cases")
    path = HERE/f"runs/eval-{stage}.txt"
    partial = path.with_suffix(".partial")
    if path.exists() or partial.exists():
        raise SystemExit(f"{path.name} or its partial already exists; inspect the receipts before retrying")
    if stage == 2 and not (HERE/"runs/eval-1.txt").is_file():
        raise SystemExit("Complete and inspect the baseline first")
    model = Anthropic(api_key=key, timeout=35, max_retries=0)
    passed = 0
    async with JobRecords() as records, asyncio.timeout(600):
        with partial.open("x") as out:
            for row in rows:
                packet = await records.get(row["job_id"])
                answer, receipt = draft_job(model,row["job_id"],row["request"],packet,stage==2,
                                      REPO/"capstone/runs/log.jsonl")
                bad = check(row,answer) if receipt["provider_reply_valid"] else ["invalid provider reply"]
                line = f'{row["id"]} FAIL: mismatched {", ".join(bad)}' if bad else f'{row["id"]} PASS'
                passed += not bad
                print(line, file=out, flush=True)
            print(f"Passed: {passed} of {len(rows)}",file=out)
    partial.replace(path)
    print(path.read_text(),end="")


def error_label(exc):
    if isinstance(exc, BaseExceptionGroup):
        return "; ".join(error_label(e) for e in exc.exceptions)
    if isinstance(exc, ProviderStageError):
        status = f" (HTTP {exc.status_code})" if isinstance(exc.status_code, int) else ""
        return f"{exc.stage}: {exc.kind}{status}"
    return type(exc).__name__


if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage",choices=("1","2","both"),required=True)
    parser.add_argument("--budget-usd",choices=("1.00",),required=True,
                        help="Acknowledge the single USD 1 ceiling covering both stages")
    args=parser.parse_args()
    path = REPO.parent/"API-Key.txt"
    key = os.environ.get("ANTHROPIC_API_KEY") or (
        path.read_text().strip() if path.is_file() else getpass.getpass("Anthropic API key (hidden): "))
    key = key.strip()
    if not key:
        raise SystemExit("No key supplied")
    stages = (1,2) if args.stage == "both" else (int(args.stage),)
    try:
        for stage in stages:
            asyncio.run(run(stage,key))
    except Exception as exc:
        raise SystemExit(f"Stopped: {error_label(exc)}. Preserve and inspect partial logs; do not rerun automatically.")
