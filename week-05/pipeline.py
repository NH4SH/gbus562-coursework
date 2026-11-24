"""Fixed analyst -> affected customers -> supplier, with mandatory review."""
import argparse
from contextlib import redirect_stdout
from decimal import Decimal
from getpass import getpass
import json
import os
from pathlib import Path
import sys
from uuid import uuid4
from specialists import Team,email_body,j
from supply_mcp_server import DEFAULT_ORG,HERE

class Budget:
    def __init__(self, usd):
        self.limit=Decimal(str(usd))
        self.spent=Decimal(0)
        self.hold=Decimal(0)
        if not self.limit.is_finite() or not 0<self.limit<=Decimal("2"):
            raise ValueError("Set a positive total budget no greater than $2.00")

    def __call__(self,kwargs):
        if self.hold:
            raise RuntimeError("Previous request did not settle; stopped rather than retrying")
        in_bound=len(json.dumps(kwargs,ensure_ascii=True).encode())+4000
        if in_bound>60000:
            raise ValueError("Input exceeded conservative size limit")
        self.hold=Decimal(2*in_bound+10*kwargs["max_tokens"])/1000000
        if self.spent+self.hold>self.limit:
            raise RuntimeError("The balance cannot safely cover another call")

    def settle(self,usage):
        cost=Decimal(2*usage.input_tokens+10*usage.output_tokens)/1000000
        self.spent+=cost
        if cost>self.hold:
            raise RuntimeError("Actual cost exceeded the request reserve; stopped")
        self.hold=Decimal(0)

class Tee:
    def __init__(self, *targets):
        self.targets=targets
    def write(self, value):
        for t in self.targets:
            t.write(value); t.flush()
        return len(value)
    def flush(self):
        for t in self.targets: t.flush()

def pipeline(team,email):
    brief=team.run_analyst(email)
    for order in brief["orders_at_risk"]:
        team.draft("customer",email,order)
    team.draft("supplier",email)
    team.summary()

def run(coordinator, org, source, save, key, budget):
    email=email_body(source)
    team=Team(org,key,budget)
    def work():
        print("COORDINATOR",coordinator.__name__)
        print("SOURCE EMAIL\n"+email)
        coordinator(team,email)
        if team.saved:
            d=HERE/"drafts"/team.supply.org.name
            d.mkdir(parents=True,exist_ok=True)
            with (d/f"{Path(source).stem}-{coordinator.__name__}-{uuid4().hex}.json").open("x",encoding="utf-8") as f:
                f.write(j(team.saved)+"\n")
        print(f"Batch API usage estimated so far: USD {budget.spent:.6f}")
    if save is None:
        work()
    else:
        save=Path(save)
        save.parent.mkdir(parents=True,exist_ok=True)
        working=save.parent/(save.name+".partial")
        if save.exists() or working.exists():
            raise FileExistsError(f"Refusing to overwrite {save} or partial output")
        with working.open("x",encoding="utf-8") as f, redirect_stdout(Tee(sys.stdout,f)):
            work()
        if save.exists():
            raise FileExistsError(save)
        working.rename(save)

def main(coordinator):
    p=argparse.ArgumentParser()
    p.add_argument("--org",default=str(DEFAULT_ORG))
    p.add_argument("--email",type=Path,required=True)
    p.add_argument("--save",type=Path)
    p.add_argument("--budget-usd",type=Decimal,required=True)
    a=p.parse_args()
    budget=Budget(a.budget_usd)
    key=os.environ.get("ANTHROPIC_API_KEY") or getpass("Anthropic API key (hidden): ")
    if not key.strip(): raise SystemExit("No key supplied; no calls made.")
    run(coordinator,a.org,a.email,a.save,key.strip(),budget)

if __name__=="__main__":
    main(pipeline)
