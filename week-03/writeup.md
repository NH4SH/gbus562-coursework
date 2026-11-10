## What I Built

I built ask.py, a Python command-line RAG tool for the supplied Copperline and Larkfield documents. It reads HTML and PDF files, creates labeled chunks, and retrieves the four closest passages using Chroma's built-in local embedding model. Copperline is the default; --docs selects another folder, with a separate database for each collection. Claude Sonnet 5 answers from those passages and cites the source filenames. Seven genuine runs are saved in runs/, including Question 1 before and after fixing the source collection. Each text export preserves the complete retrieved chunks and unedited model answer. Its audit file records the response, usage, and export hash.

## Why This Approach

Chunking method: structure

Makes sense on its own: Yes. Each supplied document section keeps its heading, complete policy statements, and relevant exceptions together with enough context to interpret the passage.

Label and source: Both. Every chunk starts with its document title and section heading, identifies the source filename, and retains available version and owner information.

Short enough: Yes. The complete chunk, including its label, is checked against the embedding model's 256-token limit and the approximately 190-word guideline.

Copperline produced 35 chunks, with a maximum of 208 embedding tokens and 144 words. The original Larkfield collection produced 39 chunks; the corrected collection has 30. Both Larkfield versions stayed within 176 tokens and 127 words per chunk. Whole sections stay together where possible. Longer sections split at paragraph or sentence boundaries, and an oversized sentence produces an error rather than being silently cut off. PDF chunks also retain their page number.

## Example Run

I chose Question 4 because it requires combining the wire-transfer fee from one document with approval limits from another. The complete saved output follows unchanged.

````text
QUESTION: Can I refund the outgoing international wire transfer fee for a member without approval from a manager?

RETRIEVED CHUNKS (cosine similarity; higher is closer)

Rank: 1 | Similarity: 0.611848 | Source: consumer-fee-schedule.html
Consumer Fee Schedule | Wire transfers
Source: consumer-fee-schedule.html
Version 8 (current). Replaces Version 7. Owner: Member Services.

Incoming domestic wire transfer: $10.
Incoming international wire transfer: $15.
Outgoing domestic wire transfer: $25.
Outgoing international wire transfer: $45. The receiving bank or an intermediary bank may deduct its own fees from the amount sent.

Rank: 2 | Similarity: 0.570936 | Source: fee-refund-guide.html
Fee Refund Guide for Member Service Staff | Refunds that need a branch manager
Source: fee-refund-guide.html
Version 2 (current). Owner: Member Services.

A refund needs the branch manager's approval when the fee is more than $30, when the member has already had a refund in the last 90 days, or when the member asks for several fees to be refunded at once. A branch manager may approve refunds of up to $150 in total for one member in any 90-day period.

Rank: 3 | Similarity: 0.541576 | Source: fee-refund-guide.html
Fee Refund Guide for Member Service Staff | What a member service representative can approve
Source: fee-refund-guide.html
Version 2 (current). Owner: Member Services.

A member service representative may approve a refund of a single fee of $30 or less without anyone else's approval. A representative may approve only one refund for the same member in any 90-day period.

Rank: 4 | Similarity: 0.506650 | Source: fee-refund-guide.html
Fee Refund Guide for Member Service Staff | Refunds that need the Member Services Director
Source: fee-refund-guide.html
Version 2 (current). Owner: Member Services.

Refunds of more than $150 in total for one member in any 90-day period need the Member Services Director's approval. So does any refund for a business account.

ANSWER
Based on the sources: the outgoing international wire transfer fee is $45 [consumer-fee-schedule.html].

Per the refund approval rules, a member service representative may only approve a refund without anyone else's approval if it is a single fee of $30 or less, and only one such refund per member in any 90-day period [fee-refund-guide.html]. Since $45 exceeds the $30 threshold, this refund does **not** qualify for representative-level approval and requires branch manager approval, as refunds exceeding $30 explicitly need the branch manager's sign-off [fee-refund-guide.html].

So no, you cannot refund this fee without manager approval — it must go to the branch manager (or higher, if other conditions apply, such as the member having had a refund in the last 90 days, multiple fees being refunded at once, the cumulative 90-day total exceeding $150, or the account being a business account, which would require the Member Services Director instead) [fee-refund-guide.html].
````

## Reflection

What was wrong: consumer-fee-schedule-v7.html was still searchable even though consumer-fee-schedule.html says Version 8 replaces Version 7. Question 1 retrieved the Version 8 overdraft section first at 0.731797 similarity and Version 7 second at 0.710238. The model reported the conflict between $29 and $35 fees and between three and four daily fees. Both files called themselves current, so that label alone did not resolve the source problem.

How I fixed it: Moved consumer-fee-schedule-v7.html into the sibling larkfield-docs-archive folder, preserving its original contents, and rebuilt the Larkfield database. I then reran the identical question with the same prompt and retrieval settings. The new top four chunks came only from the current fee schedule. The answer gave $29 per paid item, the three-fee daily cap, the $10-or-less exception, and free transfers from linked savings.

Prevention: Archive process. When Member Services approves a new fee schedule, the previous version should be moved out of the searchable collection, marked as superseded, and kept only in an archive. Rebuilding and testing the collection should be part of that release process. An old document's unchanged current label is not enough to establish that it remains valid.

Question 6: Declined. The retrieved chunks covered stop-payment fees, share-certificate dividend rates, checking account fees, and wire-transfer fees. None contained a 30-year fixed mortgage rate, and the model explicitly said it could not find that information in these sources.

The results still need human review. Question 2 correctly gives $30 for rush delivery, but its extra fraud-waiver discussion includes qualified speculation about whether rush delivery is waived. Question 4 correctly requires manager approval for the $45 fee, but its last parenthetical groups several escalation conditions together too loosely. The source requires the Director specifically for cumulative refunds over $150 or business accounts; a prior refund or multiple fees calls for a branch manager. I preserved both responses unchanged instead of cleaning up their wording in the exports.
