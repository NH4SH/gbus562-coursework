# Week 6: Test and Guard Your Capstone

The pilot evaluates a draft-only crew briefing tool against eight fictional jobs.
The MCP server only reads fixture records; the model cannot schedule or send messages.
The output guard withholds drafts when a claimed date is not backed by a current dispatch confirmation.

At the repository root, use the existing virtual environment:

```sh
.venv/bin/python -m unittest discover -s week-06 -p 'test_*.py'
.venv/bin/python week-06/evaluate.py --stage both --budget-usd 1.00
.venv/bin/python week-06/finalize.py
```

The evaluation command makes up to 16 paid model calls total, eight per stage. It uses Sonnet 5 with a 4,000-input-token preflight limit, at most 460 generated tokens, and no retries. The finalizer makes no calls. Confirm provider rates before allowing a paid run.
They use an existing key in the current environment or the parent-folder key file, or ask for it with hidden input.
Do not confuse offline tests with provider evaluations. Final results are written only when a stage completes.
