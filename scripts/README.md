Run in order from a scratch `work/` directory:

| Step | Script | What it does |
|---|---|---|
| 01 | `01_collect_corpus.py` | Streams the subtitles/news/fiction sample into segments.jsonl (never committed) |
| 02 | `02_lemmatize_sample.py` | Runs spaCy lemma counts and builds the context pool |
| 03 | `03_build_inventories.py [keys.json]` | Builds Wiktionary (kaikki.org) sense inventories |
| 04 | `04_tag_batch.py build` | Writes requests.jsonl |
| 04 | `04_tag_batch.py run CHUNK CAP_USD [MAX_CHUNKS]` | Runs OpenAI Batch API jobs under a hard cost cap; resumable via state.json |
| 05 | `05_analyze.py` | Computes shares, CIs, ranks, and safe cutoff, and writes the CSV/JSON |
| 06 | `06_mexico_flags.py hints \| build \| run CAP_USD [CHUNK] \| merge` | Adds the Mexican-usage flags |

The selection step between 03 and 04 (first N candidate keys that have senses) was done inline; see the main README.
