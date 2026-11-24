## What I Built

At our tree service, the person handing off a job has to check what the customer accepted, where the crew can get in, and whether a date is actually booked. I made a small tool that pulls the job's records over a read-only MCP connection and drafts those details for someone in the office to check. I used eight fictional cases, including declined extra work, updated access, and a date that dispatch cancelled. The evaluation compares the reply fields with what I expected before running the tool. The first scorer was too strict about the cancelled job: it failed a clean refusal even though the test only required that the tool never use the cancelled date or its source. I kept both original reports and re-scored the same model receipts with that safe refusal allowed. After that correction the guarded run had fewer passes overall, mainly because more replies did not conform to the required structure. The guard stops unsupported dates; it does not repair malformed replies.

## Why This Approach

Tool tested: Capstone. I wanted to test the same kind of information I'd hand to a crew.
Guardrail: Output checks that the date and source match the current dispatch confirmation. If they don't, it holds back the handoff for someone in the office to review.

## Example Run

```text
T1 PASS
T2 FAIL: mismatched invalid provider reply
T3 FAIL: mismatched invalid provider reply
T4 FAIL: mismatched invalid provider reply
T5 FAIL: mismatched invalid provider reply
T6 PASS
T7 PASS
T8 PASS
Passed: 4 of 8
```

## Reflection

First evaluation: 6 of 8
After the guardrail: 4 of 8
Next fix: T2: I'd require structured output from the API and retest the declined-add-on case.
