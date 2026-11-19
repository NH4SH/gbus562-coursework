# Week 4: draft-only HR agent

Built with assistance from OpenAI Codex. No email is sent. Employee identity is bound when each MCP subprocess starts; the model cannot select another employee. HR staff mode is for trusted local use only and is never exposed to the email agent. The fictional `.example` From headers are not real authentication and this demo is not production HR software.

## Setup and offline checks

From the repository root:

```sh
.venv/bin/python -m pip install -r week-04/requirements.txt
.venv/bin/python -m unittest discover -s week-04 -p 'test_offline.py' -v
```

The official `mcp` Python SDK 2.3 uses `MCPServer` (formerly `FastMCP`). Policy retrieval reuses the Week 3 section-aware chunking and four-result Chroma search. Databases are organization-path-specific under ignored `week-04/.chroma/`. Only HR policy documents are indexed, never employee records or emails. Each organization's input dataset is preserved unchanged.

To connect trusted HR staff tools to Claude Code from this repository:

```sh
claude mcp add hartwell-hr -- .venv/bin/python week-04/hr_mcp_server.py
```

For employee-only tools use `--as-employee address`. For another organization use `--org ridgeline-hotels`. To refresh changed documents start the server with `--rebuild`; rebuilding happens on its first search.

## Genuine paid runs

The authorized seven-run launcher asks for an API key with hidden Terminal input, holds it only in memory, and runs the seven emails sequentially:

```sh
.venv/bin/python week-04/run_ridgeline.py
```

The batch has a persistent shared **$2.00** ledger, locks against concurrent batch launches, and reserves $0.052 before each model request. A failed or interrupted request retains its full reservation. At most 38 requests fit within the cap; there are no automatic retries. Each email also stops after ten tool calls or ten model requests. Input JSON bytes plus framing allowance must stay below 20,000, and model output is capped at 1,200 tokens. The reservation uses Sonnet 5's published $2/million input and $10/million output rates (checked November 18, 2026). This deliberately over-reserves rather than refunding unused allowance. Do not delete the ledger to evade the cap. If it stops early, review before approving more usage.

For a separately authorized individual run:

```sh
.venv/bin/python week-04/agent.py --org ridgeline-hotels --email week-04/ridgeline-hotels/sample-emails/01-jenna-pto.eml --save week-04/runs/ridgeline-01.txt --budget-usd 0.52
```

Individual CLI calls have their own cap, not the batch's shared ledger; use the batch launcher for this assignment's $2 authorization. The agent reads an existing `API-Key.txt` one folder above this repository or the process's `ANTHROPIC_API_KEY`. Never place a key in the repository or command line.

Saved transcripts are UTF-8, refuse overwrites, and contain sender, subject, steps, draft, review flag, stopping reason, and token usage. Draft JSON files are local and ignored. Failed transcripts are not successful model evidence; never edit them into successes. Review all seven actual outputs against the dataset before finalizing the writeup or submission.

## Sources

- Course Week 4 slides and supplied fictional Hartwell/Ridgeline datasets.
- [Official MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk).
- [Claude Sonnet 5 overview and pricing](https://platform.claude.com/docs/en/models/sonnet-5/overview).
