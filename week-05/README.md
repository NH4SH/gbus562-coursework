# Week 5: Supplier-response specialists

The four shared specialists are supply analysis, supplier writing, customer writing and review. A fixed pipeline and a model-routed orchestrator use the same code for analysis and mandatory draft review. Neither sends messages. The two company folders are the official Canvas packets, with different CSV schemas normalized in the read-only data layer.

## Verify without an API key

Run from the Git repository root:

```sh
.venv/bin/python -B -m unittest discover -s week-05 -p 'test_*.py' -v
```

Ground truth for the Danforth message: 40 pumps are due on day 4 and the remaining 160 on day 19. Orders O-2203, O-2204 and O-2205 ship 7, 4 and 2 days late respectively; O-2203 and O-2205 have penalties and require human review. The Marlow options affect different orders and need a human decision. The Ashgrove delay is covered, and Pelham specifically says its order is unaffected.

## Run only after the API budget is approved

```sh
.venv/bin/python -B week-05/run_copperline.py --budget-usd 2
```

Enter the key at the hidden Terminal prompt. It is not transmitted anywhere except to authenticate with Anthropic and is never saved. Each genuine paid call logs its response ID and tokens. Run logs publish locally as the final file only after a successful run; a failed run leaves a separate .partial file for inspection. Do not restart a full batch if any outputs already exist.

For individual development runs, both coordinators accept --org, --email, --save, and --budget-usd. An individual run has a separate cap, so use the batch runner for the assignment. Draft JSON is ignored by Git. Do not commit the virtual environment, model credentials, or incomplete runs.
