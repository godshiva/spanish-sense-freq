# Spanish Sense Frequency List (v0.1)

**Author:** Luc Taylor · **Repository:** https://github.com/godshiva/spanish-sense-freq · **Data license:** CC BY-SA 4.0 · **Code license:** MIT

This list estimates how often each **meaning (sense)** of the 2,500 most frequent Spanish lemmas is used. It covers 6,214 senses, ranked by estimated frequency per million words. Most frequency lists count spellings or lemmas; this one splits a word like *quedar* into "remain", "stay", "end up", "arrange to meet", and so on, and ranks each meaning separately.

**This is an LLM-tagged, small-sample estimate. Read the caveats before using it.**

## Files
| File | Contents |
|---|---|
| `data/spanish_sense_frequency.csv` / `.json` | One row per sense (columns below) |
| `data/summary.json` | Corpus size, coverage, safe-cutoff numbers |
| `data/inventories.json` | Sense inventory per lemma\|POS, derived from Wiktionary |
| `data/lemma_counts_top20k.json` | Lemma\|POS counts from the sample corpus |
| `data/lemmas_2500.json` | The 2,500 lemma\|POS keys covered |
| `data/spotcheck.json` | 100-item check of the sense tags |
| `data/spotcheck_mx.json` | 50-item check of the Mexican flags |
| `data/wikt_region_hints.json` | Wiktionary senses labelled only for Spain or other non-Mexican regions, per lemma |
| `data/corpus_signal.json` | Weak corpus signal: .mx news vs other contexts |
| `data/mx_batch_cost_log.json` | Batch jobs and cost for the Mexican flags |
| `data/batch_cost_log.json` | OpenAI Batch API jobs and actual cost |
| `scripts/` | Full pipeline, steps 01–05 |
| `DATASHEET.md` | Datasheet for the dataset |

### Columns
| Column | Meaning |
|---|---|
| `rank` | Global rank by `est_per_million` |
| `lemma`, `pos` | spaCy lemma and Universal POS (AUX merged into VERB) |
| `sense_id` | `lemma\|POS\|n`, where n is the Wiktionary-derived sense number. `\|other` means an unlisted sense, idiom, or fixed expression |
| `gloss` | English gloss from Wiktionary |
| `share` | Fraction of valid sampled contexts tagged with this sense |
| `ci_low`, `ci_high` | Wilson 95% interval for `share` |
| `n_contexts` | Valid contexts for the lemma (out of 25) after removing "not this word" items |
| `est_per_million` | Estimated sense frequency: `lemma_per_million × share` |
| `est_per_million_low` / `est_per_million_high` | `est_per_million` recomputed with the CI bounds |
| `lemma_per_million` | Lemma frequency in the sample corpus, scaled by the share of contexts that really were this lemma |
| `rank_min`, `rank_max` | Plausible rank band from CI overlap |
| `rank_safe` | `true` if the sense's lower-bound frequency exceeds the highest frequency of any lemma not in the list (see "Safe cutoff") |
| `mx_status` | `common` / `uncommon` / `not_used` in Mexico (LLM judgement; see "Mexican usage flags"). Blank for 1 row (`pelear|VERB|6`, where the model returned no answer) |
| `non_mexican` | `true` if `mx_status` is `uncommon` or `not_used`: a sense an ordinary Mexican speaker would not normally use |
| `mx_equivalent` | Usual Mexican equivalent when flagged (e.g. *coger* "to take" → *tomar, agarrar*; *piso* "flat" → *departamento*) |
| `mx_note` | Short model rationale (≤12 words, Spanish or English) |
| `method` | `llm` (tagged by the model) or `single-sense` (the lemma had one usable Wiktionary sense, so share = 1 without tagging) |
| `example_1`, `example_2` | Short snippets (about ±60 characters) with the target marked `[[...]]` |

## Method
1. **Corpus.** All text was streamed and sampled; nothing was downloaded in bulk. Totals by word count (5.80M alphabetic tokens after spaCy):

   | Genre | Share | Tokens | Source |
   |---|---|---|---|
   | Subtitles | 50% | 2.87M | OPUS OpenSubtitles v2024, Spanish monolingual. Sparse 4-line blocks sampled from the first ~85M lines of the file |
   | News | 25% | 1.47M | `stanford-oval/ccnews` 2023 (CC-NEWS), Spanish. Every `.mx` article kept; other Spanish-language articles kept at 40% to favour Mexico |
   | Fiction | 25% | 1.46M | Project Gutenberg Spanish (`manu/project_gutenberg`). Random 3,000-character passages from the body of each book |

2. **Lemmatisation and frequency.**
   - spaCy `es_core_news_md` produced lemma + UPOS counts.
   - Up to 40 contexts per lemma|POS were kept by reservoir sampling.
   - Lemmas with no matching Wiktionary entry were skipped. These were mostly lemmatiser errors (e.g. *verar*) and archaic spellings (*fué*, *á*). The next lemma down was taken instead, so the 2,500 keys come from the top ~2,660 candidates.
3. **Sense inventory.** From kaikki.org's Wiktionary extract:
   - Up to 8 senses per lemma|POS, in Wiktionary order.
   - Dropped: obsolete, archaic, rare, dated, and form-of senses, plus senses tagged *only* with a non-Mexican region.
   - Mexico-tagged senses were always kept. (Spain-only senses were excluded here; see "Mexican usage flags".)
   - Every prompt also offered "other / idiom" and "not this word".
4. **Tagging.**
   - 25 random contexts per lemma, 10 contexts per request.
   - Model: `gpt-5.6-luna`, `reasoning_effort: low`, JSON output, via the OpenAI Batch API.
   - 1,701 lemmas needed tagging (5,103 requests, 42,525 contexts). The other 799 had a single sense.
   - Actual cost: **US$1.06** (Batch prices $0.10 per 1M input tokens, $0.60 per 1M output tokens).
5. **Statistics.**
   - Share and Wilson 95% CI per sense.
   - Senses with zero hits are omitted.
   - Estimated frequency = lemma frequency × share.
   - All senses ranked globally.

## Mexican usage flags
Most senses are shared across Spanish. The `non_mexican` flag marks senses an ordinary educated speaker in Mexico would not normally use. It replaces v0.1's sparse `mexico` column.

1. **Wiktionary regional labels.**
   - Senses labelled only for Spain or other non-Mexican regions had already been left out of the inventory in step 3.
   - Those senses are collected per lemma in `wikt_region_hints.json`; 177 lemmas have some, e.g. *piso* "flat, apartment" [Spain].
   - They were passed to the model as hints, mainly so it could judge `other` rows. A Spain-only sense used in a context gets tagged `other`, e.g. *piso* = apartment.
2. **LLM classification.**
   - Every sense row (6,214) was classified with `gpt-5.6-luna` (Batch API, reasoning low, 25 rows per request).
   - The model saw the lemma, POS, gloss, one example and any regional hints.
   - Labels: `common`, `uncommon` (understood but rare or marked as foreign/Spain-only, e.g. *vuestro*, *chico* "lad") or `not_used` (absent or misleading/vulgar, e.g. *coger* "to take").
   - Cost: US$0.17.
3. **Corpus signal** (`corpus_signal.json`).
   - Compared sense hits in .mx news contexts with all other contexts.
   - With 25 contexts per lemma this is dominated by genre differences (.mx contexts are all news). It is published for reference but **not** used in the flags.

**Results:** 5,673 common, 514 uncommon, 26 not_used, 1 missing; `non_mexican = true` for 540 rows.

**Spot-check (50 items):**
- **Who and how:** the AI agent checked the flags; it is not a native Mexican speaker. The sample was 14 known cases (*coger*, *piso*, *coche*, *carro*, *conducir*, *tío*, *vuestro*, *usted*, …), 18 random flagged rows and 18 random unflagged rows.
- **Agreement:** **48/50 (96%).**
- **Misses:** *cañón* "projector" was marked not_used, but it is common in Mexico. *conducir* "to drive" was marked common, but *manejar* is the everyday word; this one is borderline because *licencia de conducir* is standard.

**Caveats:**
- `uncommon` mixes truly regional (Spain-only) senses with merely literary or archaic ones (*hallar*, *rostro*, *tras*). Read `mx_note` to tell them apart.
- Some judgements follow the example snippet rather than the gloss.
- Senses Wiktionary marks only for Spain (*piso* = flat, *móvil* = phone) are not separate rows; they sit inside `other`.
- Spain-only lemmas with no general sense (*ordenador*, *zumo*, *vosotros*) are absent from the list entirely.

## Safe cutoff (how far the ranking is provably complete)
No sense can be more frequent than its lemma. The most frequent lemma **not** included (with Wiktionary senses) is *campana / oponer / docena* at **24.8 per million**. A sense whose estimated frequency exceeds that cannot be outranked by any sense left out of the list.

| Criterion | List is complete through rank | Meaning |
|---|---|---|
| Point estimate (`est_per_million` > 24.8) | **2,878** | Using point estimates, no omitted sense could rank higher |
| Lower 95% bound (`est_per_million_low` > 24.8) | **581** | Holds even at the low end of the interval. Column `rank_safe` is `true` for these |

**Ordering reliability:** the CIs of neighbouring senses overlap heavily. The median rank band (`rank_max − rank_min`) is about **60 places for the top 100** and about **3,000 for the whole list**. Treat ranks beyond the first few hundred as coarse tiers, not an exact order.

## Quality check
- **Spot-check:** I hand-checked 100 random tagged items and agreed with the model on **96/100**. Five more were borderline because the inventory itself was weak.
- **Who checked:** the checker was the AI agent that built the pipeline, not a human expert.
- **What was sampled:** the spot-check drew only from the first 1,900 of 5,103 requests, i.e. the most frequent lemmas.
- **Earlier pilot:** a 100-item pilot gave 86–88% agreement before the spaCy lemma filter was added.

## Caveats
- **LLM-tagged, 25 samples per lemma.** At n = 25 a 50% share has a CI of roughly 31–69%. Minor senses are noisy, and senses with 0 hits may still exist.
- **The sense inventory comes from Wiktionary.** Its granularity is uneven. Some lemmas have near-duplicate senses, e.g. *y* "and" appears twice and *resto* has "rest, remainder" / "remainder". Some meanings are missing and fall into `other`.
- **Function words are poorly modelled.** For example, `el|DET` includes the feminine article *la*, which Wiktionary lists under a separate entry, so most *el* tokens land in `other`. `él|PRON` absorbs the clitics *lo/la/le/se* via spaCy lemmatisation. Use content-word rows with more confidence.
- **Lemmatiser errors.** Rare tokens are mis-lemmatised; "not this word" removes some of them. Single-sense lemmas (`method=single-sense`) were not checked by the model.
- **Corpus bias.**
  - Fiction is public-domain, mostly 19th–early 20th century and often from Spain, with archaic spelling.
  - Subtitles come only from the earlier part of the OPUS file and include translated dialogue.
  - News is from 2023 only. It is weighted toward Mexico but is pan-Hispanic.
  - Mexican-usage flags are LLM judgements (see "Mexican usage flags").
- **Example snippets** are kept very short. See Licenses.

## Licenses and sources
- **Dataset:** CC BY-SA 4.0, because the glosses and sense inventory derive from Wiktionary (CC BY-SA). Attribution: Wiktionary contributors, via kaikki.org / wiktextract (Tatu Ylonen).
- **OpenSubtitles (OPUS):** provided for research. **No subtitle text is redistributed beyond short (~120-character) example snippets**; only derived counts are released. Do not add longer subtitle excerpts.
- **CC-NEWS / Common Crawl:** subject to the Common Crawl Terms of Use. Only counts and short snippets are included.
- **Project Gutenberg:** public domain in the US.
- **Tags and Mexican flags:** generated with OpenAI `gpt-5.6-luna`. Total cost US$1.24: $1.06 for sense tags, $0.17 for Mexican flags.
- **Code** (`scripts/`): MIT.

## Reproducing and scaling
```bash
pip install -r requirements.txt && python -m spacy download es_core_news_md
cd work
python ../scripts/01_collect_corpus.py
python ../scripts/02_lemmatize_sample.py
# write the top-N candidate keys to candidates.json, then:
python ../scripts/03_build_inventories.py candidates.json
# select the first N keys with senses into top_lemmas.json
python ../scripts/04_tag_batch.py build
OPENAI_API_KEY=... python ../scripts/04_tag_batch.py run 1600 <CAP_USD>
python ../scripts/05_analyze.py
```

**Scaling to 10,000 lemmas:**
- A lemma at rank 10,000 occurs only a few times per million words, so the corpus must grow to about **25–40M tokens**. Raise `TARGET` in `01_collect_corpus.py`.
- Expected tagging cost is about **US$5–8**: roughly 4–6× the current run, since later lemmas have fewer senses and more of them have a single sense.
- `04_tag_batch.py` enforces a hard spending cap. It submits in frequency order and projects the cost of each chunk before submitting it.
- `05_analyze.py` recomputes the safe cutoff automatically.

## Citation
```
Taylor, Luc (2026). Spanish Sense Frequency List v0.1. https://github.com/godshiva/spanish-sense-freq
```
