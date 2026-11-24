## Evaluation prompt

Build a baseline evaluation for the draft-only tree-service crew handoff. Read capstone/proposal.md, capstone/records.json, and week-06/test-cases.csv. Create week-06/evaluate.py, preserve the id,type,request,expected columns, and score every case by comparing the returned structured fields to the expected values. Write one ID plus PASS or FAIL with a reason and end with Passed: N of M in week-06/runs/eval-1.txt. Leave manual judgment for a human when exact matching is insufficient. If running the provider, use only the approved key source outside the repository, never write or print it, and do not fabricate a run.

## Guardrail prompt

Add a code-level output guard to capstone/handoff.py. Any confirmed date in a crew draft must match the current uncancelled dispatch confirmation and its source record in the retrieved job packet. Never treat a customer proposal as a booking. If that check fails, suppress the draft and return an explicit human-review state without the date. Rerun the identical CSV with week-06/evaluate.py, preserving the baseline, and save the live after-run to week-06/runs/eval-2.txt with the same case and total format. Keep only actual model receipts, and never write or display the API key.
