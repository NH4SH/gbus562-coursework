"""Read-only MCP tools and deterministic, complete-order FIFO supply coverage."""
import argparse
import csv
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_ORG = HERE / "brookfield-bikes"

def org_path(org):
    p = Path(org).expanduser()
    if not p.is_absolute():
        p = p.resolve() if p.is_dir() else HERE / p
    if not p.is_dir():
        raise ValueError(f"Company folder not found: {p}")
    return p.resolve()

def read_csv(p):
    with p.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def field(row, *names):
    for n in names:
        if n in row and row[n] != "":
            return row[n]
    raise ValueError(f"Missing column: {names}")

class Supply:
    def __init__(self, company):
        self.org = org_path(company)
        for attr, fname in {
            "inventory":"parts.csv", "bom":"bill-of-materials.csv",
            "inbound":"inbound.csv", "orders":"orders.csv", "suppliers":"suppliers.csv",
        }.items():
            setattr(self, attr, read_csv(self.org / fname))

    def models(self, part_id):
        return {field(r,"product","model"):int(field(r,"per_unit","qty_per_bike"))
                for r in self.bom if r["part_id"] == part_id}

    def get_part(self, part_id):
        part=next((r for r in self.inventory if r["part_id"]==part_id),None)
        if part is None:
            raise ValueError(f"Unknown part: {part_id}")
        return {**part, "on_hand":int(part["on_hand"]), "scheduled_shipments":[
            {**r,"qty":int(r["qty"]),"arrives_in_days":int(r["arrives_in_days"])}
            for r in self.inbound if r["part_id"]==part_id], "models":self.models(part_id)}

    def get_orders_for_part(self, part_id):
        models=self.models(part_id)
        rows=[]
        for r in self.orders:
            product=field(r,"product","model")
            if product not in models:
                continue
            qty=int(field(r,"units","qty"))
            rows.append({"order_id":r["order_id"],"customer":r["customer"],"product":product,
                         "qty":qty,"units_needed":qty*models[product],
                         "ship_day":int(field(r,"ship_by_day","ship_in_days")),
                         "late_penalty":r["late_penalty"].lower() in {"yes","true","1"}})
        return sorted(rows,key=lambda r:(r["ship_day"],r["order_id"]))

    def check_coverage(self, part_id, arrivals):
        stock=self.get_part(part_id)["on_hand"]
        dates=[]
        for a in arrivals:
            if set(a)!={"day","qty"} or any(type(v) is not int or v<0 for v in a.values()):
                raise ValueError("Arrivals require nonnegative integer day and qty")
            dates.append((a["day"],a["qty"]))
        dates.sort()
        i, prior_ready = 0, 0
        out=[]
        for order in self.get_orders_for_part(part_id):
            need,due=order["units_needed"],order["ship_day"]
            # Receipts at/before the deadline count, but older orders take priority.
            while i<len(dates) and dates[i][0]<=due:
                stock+=dates[i][1]; i+=1
            # Track available-to-order units on its due date without letting a
            # later order use stock that is reserved by a delayed earlier order.
            due_supply=self.get_part(part_id)["on_hand"]+sum(q for d,q in dates if d<=due)
            units_short=min(need,max(0,sum(r["units_needed"] for r in out)+need-due_supply))
            ready=max(prior_ready,due)
            while stock<need and i<len(dates):
                day,added=dates[i]; stock+=added; ready=max(ready,day); i+=1
            if stock>=need and prior_ready!=float("inf"):
                stock-=need; prior_ready=ready
            else:
                ready=None; prior_ready=float("inf")
            out.append({**order,"units_short":units_short,"ready_day":ready,
                        "covered":ready is not None and ready<=due,
                        "days_late":None if ready is None else ready-due})
        return out

def main():
    from mcp.server.fastmcp import FastMCP
    p=argparse.ArgumentParser()
    p.add_argument("--org",default=str(DEFAULT_ORG))
    args=p.parse_args()
    data=Supply(args.org)
    server=FastMCP("GBUS562 supply coverage")
    @server.tool()
    def get_part(part_id: str) -> dict:
        """Find on-hand units, scheduled receipts, and products using a part."""
        return data.get_part(part_id)
    @server.tool()
    def get_orders_for_part(part_id: str) -> list[dict]:
        """Find the relevant open orders in order of deadline."""
        return data.get_orders_for_part(part_id)
    @server.tool()
    def check_coverage(part_id: str, arrivals: list[dict[str,int]]) -> list[dict]:
        """Replace the part's receipts with {day,qty} and calculate FIFO coverage."""
        return data.check_coverage(part_id,arrivals)
    server.run(transport="stdio")
if __name__=="__main__":
    main()
