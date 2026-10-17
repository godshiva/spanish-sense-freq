Run in order from a scratch `work/` directory:

| Step | Script | What it does |
|---|---|---|
| 01 | `01_collect_corpus.py` | Streams the subtitles/news/fiction sample into segments.jsonl (never committed) |
| 02 | `02_lemmatize_sample.py tokens \| resolve \| count` | spaCy pass, then Wiktionary/headword-policy lemma repair, then counts and the context pool |
| 03 | `03_build_inventories.py [keys.json]` | Builds Wiktionary (kaikki.org) sense inventories |
| 04 | `04_tag_batch.py build` | Writes requests.jsonl |
| 04 | `04_tag_batch.py run CHUNK CAP_USD [MAX_CHUNKS]` | Runs OpenAI Batch API jobs under a hard cost cap; resumable via state.json |
| 05 | `05_analyze.py` | Computes shares, CIs, ranks, and safe cutoff, and writes the CSV/JSON |
| 06 | `06_mexico_flags.py hints \| build \| run CAP_USD [CHUNK] \| merge` | Adds the Mexican-usage flags |
| 07 | `07_manual_mx_review.py manual_mx_decisions.json` | Applies the hand review of the Mexican flags and logs changes to `manual_corrections.csv` |
| 09 | `09_audit.py [--csv F] [--top N]` | Missing-words audit: closed-class checklist and gaps against external frequency lists |
| 10 | `10_incremental.py select OLD \| collect [DIRS] \| carry OLD_CSV \| fold \| manual F LOG` | Incremental update (v0.3): re-tag only new/changed keys, carry labels by sense_id |
| – | `ssf_lex.py` | Shared helpers: cached kaikki fetch with retries, headword checks, lemma resolution |
| 08 | `08_register.py seed \| build \| run CAP_USD [CHUNK [retry]] \| retry \| merge \| manual OVERRIDES.json LOG.csv` | Register labels: Wiktionary seed, then LLM, then manual overrides |

In v0.2 the selection step between 03 and 04 (first N candidate keys that have senses) was done inline. Since v0.3, `10_incremental.py select` does it: every key with at least 144 tokens and senses.
