"""Claude chooses the next specialist but all permission checks live in code."""
from pipeline import main
from specialists import STR, MAX_TOOLS, j, tool

TOOLS=[
    tool("run_supply_analyst","Run the read-only supply analysis, required before any draft."),
    tool("draft_supplier_reply","Draft a supplier reply from the brief; always reviewed, never sent."),
    tool("draft_customer_notice","Draft a notice only for an order identified as at risk.",order_id=STR),
    tool("finish","End the workflow with a summary for a human.",summary=STR,needs_person={"type":"boolean"}),
]

def orchestrator(team,email):
    spec=team.prompt("orchestrator")+"\nIf a supplier proposes mutually exclusive options, don't contact customers before a person chooses. Do not accept or decline an option. Call finish once complete. For a confirmed delay, draft for each order at risk."
    messages=[{"role":"user","content":email}]
    calls=0
    for _ in range(MAX_TOOLS+1):
        r=team.ask("orchestrator",spec,messages,TOOLS)
        blocks=[b for b in r.content if b.type=="tool_use"]
        if not blocks or calls+len(blocks)>MAX_TOOLS:
            break
        messages.append({"role":"assistant","content":team.blocks(r)})
        results=[]
        for t in blocks:
            calls+=1
            print("ROUTE",t.name,j(t.input),flush=True)
            try:
                if t.name=="run_supply_analyst":
                    result=team.run_analyst(email)
                elif t.name=="draft_supplier_reply":
                    result=team.draft("supplier",email)
                elif t.name=="draft_customer_notice":
                    if not team.brief:
                        raise ValueError("Run analysis first")
                    order=next((o for o in team.brief["orders_at_risk"] if o["order_id"]==t.input["order_id"]),None)
                    if order is None:
                        raise ValueError("This order is not verified at risk")
                    result=team.draft("customer",email,order)
                elif t.name=="finish":
                    team.summary(t.input)
                    return
                else:
                    raise ValueError("Unknown tool")
                results.append({"type":"tool_result","tool_use_id":t.id,"content":j(result)})
            except ValueError as e:
                results.append({"type":"tool_result","tool_use_id":t.id,"content":str(e),"is_error":True})
        messages.append({"role":"user","content":results})
    raise RuntimeError("Orchestrator did not finish inside the authorized tool limit")

if __name__=="__main__":
    main(orchestrator)
