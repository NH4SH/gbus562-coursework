# Week 3: Document-grounded RAG

## Results

The seven genuine Claude Sonnet 5 runs are in [`runs/`](runs/), and the required
four-section analysis is in [`writeup.md`](writeup.md). Question 1 demonstrates the
conflicting fee schedules before correction and the current policy afterward.
Question 6 declines because the retrieved documents contain no mortgage rate.
All response text is unchanged; each export has an audit sidecar with its hash.

## Setup

From the repository root, use Python 3.12 or 3.13:

```sh
python3.13 -m venv .venv
.venv/bin/python -m pip install -r week-03/requirements.txt
.venv/bin/python -m unittest discover -s week-03 -p 'test_*.py' -v
```

On Windows use `.venv\Scripts\python.exe` instead of `.venv/bin/python`.
The requirements file pins the versions used for validation. The first local index
build downloads Chroma's built-in approximately 80 MB embedding model. Embeddings
run locally and require no paid embedding API.

## Source structure and chunking

HTML documents use their main content, document title, metadata, and section
headings. Paragraphs and list items stay with their section. Table rows repeat their
column headings. PDF extraction uses font sizes to identify section headings and
keeps the source filename and page number. The included PDF's seven sections are
covered by an extraction regression test. Markdown and plain text are also supported.
Unsupported formats and image-only PDFs fail with an explanatory error instead of
being silently omitted.

Each chunk begins with the document title and section heading, identifies its source,
and retains version/owner information when available. Sections stay whole whenever
they fit. Longer sections split at paragraph or sentence boundaries. Every complete
chunk, including its label, is checked with the embedding model's untruncated
tokenizer: at most 256 tokens and 190 words. Oversized single sentences cause an
explicit error instead of silent truncation.

## Local checks without paid calls

```sh
.venv/bin/python week-03/ask.py --index-only --rebuild
.venv/bin/python week-03/ask.py --retrieve-only 'A vendor emailed asking us to send payment to a new bank account. What should I do?'
.venv/bin/python week-03/ask.py --docs larkfield-docs --retrieve-only 'How much is the fee when a member overdraws their checking account?'
```

`--docs` defaults to `copperline-docs`. Relative document paths are resolved inside
`week-03`; absolute paths are also accepted. Only files directly inside that folder
are indexed. Archive folders are not recursed. Every source folder has a separate
ignored `.chroma` database keyed by its full path. A source fingerprint rejects a
changed corpus until `--rebuild` is used, preventing stale data after a correction.

## Authorized model runs

Supply `ANTHROPIC_API_KEY` in the current process using a secure local entry flow, or
let the tool read an already-existing `API-Key.txt` one folder above the repository.
Do not paste a key into a command, chat, source file, or this repository. The tool
never writes the key. Do not run paid calls without a spending authorization.

```sh
.venv/bin/python week-03/ask.py --docs larkfield-docs --save week-03/example-new.txt 'How much is the fee when a member overdraws their checking account?'
```

The model is exactly `claude-sonnet-5`, with thinking disabled and a 1,200-token
answer limit. Unsupported sampling parameters are omitted. Retrieval returns four
chunks ranked by cosine
similarity. The console prints the required 150-character previews. `--save` writes
the complete retrieved chunks, each rank, score and source, then a standalone
`ANSWER` line and the exact model text. A neighboring audit JSON preserves the
response ID, model, usage, raw response content, question, source fingerprint and
export hash without credentials. Existing exports cannot be overwritten. API errors
are not replaced with invented answers, and automatic retries are disabled.

The completed source correction moved `consumer-fee-schedule-v7.html` from
`larkfield-docs` into the sibling `larkfield-docs-archive` folder after saving
`q1-before.txt`. The index was rebuilt before `q1-after.txt`. Source contents,
question, retrieval settings, and grounding prompt stayed unchanged. Q2 through
Q6 then used the corrected collection. See `questions.json` for exact wording.

To reproduce the before experiment, copy the five current Larkfield files and the
archived v7 file into a new temporary document folder. Build that folder's separate
index, save a new before export, then move v7 out, rebuild, and save the after export.
Do not overwrite the seven submitted exports or modify the original source bytes.

## Limits

A similarity score measures semantic closeness, not factual correctness. Retrieval
can still return unrelated sources for a question the collection cannot answer.
The model must decline unsupported answers. Source ownership and removal of
superseded files are still required; a document's own “current” label is not proof
that it is the latest version. The PDF reader handles the supplied text PDF but does
not perform OCR or guarantee correct extraction of every complex PDF layout.

## Publication

Keep `.venv`, `.chroma`, local caches and API keys out of Git. Confirm the final
writeup against all seven genuine exports and inspect the credential scan before
publication or submission. The included offline tests use clearly labeled mock
responses only in temporary test directories; those are never assignment exports.
