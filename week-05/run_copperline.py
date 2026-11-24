"""One hidden key prompt; one shared spending limit across eight genuine runs."""
import argparse
from decimal import Decimal
from getpass import getpass
from pathlib import Path
import re
from uuid import uuid4
from pipeline import Budget,pipeline,run
from orchestrator import orchestrator

HERE=Path(__file__).resolve().parent
ORG=HERE/"copperline-coffee"
RECEIPT=re.compile(r"^MODEL .+ (msg_[A-Za-z0-9]+) tokens in=(\d+) out=(\d+)$", re.M)

def received_cost(files):
    usage={}
    for f in files:
        for rid,inp,out in RECEIPT.findall(f.read_text(encoding="utf-8")):
            cost=Decimal(2*int(inp)+10*int(out))/1000000
            if rid in usage and usage[rid]!=cost:
                raise ValueError("Conflicting token receipts")
            usage[rid]=cost
    return sum(usage.values(),Decimal(0))

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--budget-usd",required=True,type=Decimal)
    p.add_argument("--resume",action="store_true",help="Resume only after the earlier batch has stopped")
    args=p.parse_args()
    budget=Budget(args.budget_usd)
    cases=sorted((ORG/"supplier-emails").glob("*.eml"))
    if len(cases)!=4: raise SystemExit("Expected the four Canvas cases")
    jobs=[(f,fn,HERE/"runs"/f"copperline-{f.name[:2]}-{fn.__name__}.txt")
          for f in cases for fn in (pipeline,orchestrator)]
    complete=[path for _,_,path in jobs if path.exists()]
    partials=[path.with_name(path.name+".partial") for _,_,path in jobs if path.with_name(path.name+".partial").exists()]
    archive=HERE/"runs"/"_diagnostics"
    previous_partials=sorted(archive.glob("*.partial"))
    if (complete or partials or previous_partials) and not args.resume:
        raise SystemExit("Existing output found. Do not restart the full batch.")
    if args.resume:
        if any(not RECEIPT.search(f.read_text(encoding="utf-8")) or "\nBatch API usage estimated so far:" not in f.read_text(encoding="utf-8") for f in complete):
            raise SystemExit("A completed log is missing its verification markers; inspect it before resuming.")
        if len(partials)>1 or any(f.with_suffix("").exists() for f in partials):
            raise SystemExit("Unexpected overlapping output; stop and inspect before resuming.")
        if len(complete)==len(jobs):
            print("All eight logs already exist; no calls made.")
            return
        budget.spent=received_cost(complete+partials+previous_partials)
        # Preserve room for one potentially charged but unreported request per stopped run.
        budget.limit-=Decimal("0.15")*len(partials+previous_partials)
        if budget.spent>=budget.limit:
            raise SystemExit("Prior usage and reserves leave no safe remaining budget.")
        print(f"Resuming only {len(jobs)-len(complete)} unfinished runs; verified prior API cost USD {budget.spent:.6f}.")
    print("Eight live Claude Sonnet 5 runs; shared API spending cap: USD "+str(budget.limit))
    key=getpass("Anthropic API key (hidden; never saved): ").strip()
    if not key: raise SystemExit("No key supplied; no calls made.")
    try:
        if partials:
            archive.mkdir(parents=True,exist_ok=True)
            for f in partials:
                f.rename(archive/f"{uuid4().hex}-{f.name}")
        for f,fn,output in jobs:
            if output in complete:
                continue
            print(f"\n=== {output.name} ===",flush=True)
            run(fn,ORG,f,output,key,budget)
    except Exception as e:
        # No raw SDK exception, request or credentials are printed.
        raise SystemExit(f"Stopped: {type(e).__name__}. Check partial output and do not rerun automatically.")
    print(f"Saved all eight run logs. Estimated API cost: USD {budget.spent:.6f}")

if __name__=="__main__":
    main()
