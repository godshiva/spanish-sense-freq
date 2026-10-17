# Spanish Sense Frequency List (v0.3)

**Author:** Luc Taylor · **Repository:** https://github.com/godshiva/spanish-sense-freq · **Data license:** CC BY-SA 4.0 · **Code license:** MIT

This list estimates how often each **meaning (sense)** of the 2,642 most frequent Spanish lemma|POS keys is used. It covers 6,553 senses, ranked by estimated frequency per million words. Most frequency lists count spellings or lemmas; this one splits a word like *quedar* into "remain", "stay", "end up", "arrange to meet", and so on, and ranks each meaning separately.

**This is an LLM-tagged, small-sample estimate. Read the caveats before using it.**

**v0.3 (missing-words fix):** v0.2 was missing *muy*. A full audit found 38 core closed-class words missing as well: pronouns *ella, me, te, se, lo, le, esto, eso…*, *tan*, and all the numerals. Further gaps came from lemmatiser and Wiktionary-lookup errors (*fin, lindo, hola, novia, siquiera…*). The pipeline was fixed and only the affected keys were re-run: 146 keys added, 203 re-tagged. See **[AUDIT.md](AUDIT.md)** for root causes and before/after cross-checks against three external lists. Ranks shifted accordingly; the point-estimate safe cutoff moved from rank 2,878 to 3,089.

## Files
| File | Contents |
|---|---|
| `data/spanish_sense_frequency.csv` / `.json` | One row per sense (columns below) |
| `data/summary.json` | Corpus size, coverage, safe-cutoff numbers |
| `data/inventories.json` | Sense inventory per lemma\|POS, derived from Wiktionary |
| `data/lemma_counts_top20k.json` | Lemma\|POS counts from the sample corpus |
| `data/lemmas_tagged.json` | The 2,642 lemma\|POS keys covered (was `lemmas_2500.json`) |
| `data/lemma_policy.json` | Headword rules applied before lemma repair (v0.3; e.g. *muy*, object pronouns, accent variants) |
| `data/manual_v03_review.json` | Hand review of new v0.3 rows (input to `10 manual`) |
| `data/v03_batch_cost_log.json` | Batch jobs and cost for the v0.3 re-run |
| `data/audit/` | v0.3 audit outputs: `audit_report.json` (09), `skipped_categories.json`, `diff_v02_v03.json`, `lemma_fixes.json`, `select_info.json`, `spotcheck_v03.json` |
| `AUDIT.md` | Missing-words audit and fix (v0.3) |
| `data/spotcheck.json` | 100-item check of the sense tags |
| `data/spotcheck_mx.json` | 50-item check of the Mexican flags |
| `data/wikt_region_hints.json` | Wiktionary senses labelled only for Spain or other non-Mexican regions, per lemma |
| `data/corpus_signal.json` | Weak corpus signal: .mx news vs other contexts |
| `data/mx_batch_cost_log.json` | Batch jobs and cost for the Mexican flags |
| `data/batch_cost_log.json` | OpenAI Batch API jobs and actual cost |
| `data/manual_corrections.csv` | Every manual change: `sense_id, field, old, new, reason` (2,111 rows) |
| `data/manual_mx_decisions.json` | Hand-review decisions for the 540 rows the LLM flagged (input to `07`) |
| `data/manual_register_overrides.json` | Hand overrides of `register` (input to `08 manual`) |
| `data/register_wiktionary_seed.json` | Register labels taken from Wiktionary sense tags |
| `data/spotcheck_register.json` | 50-item random check of `register` |
| `data/register_batch_cost_log.json` | Batch jobs and cost for the register labels |
| `scripts/` | Full pipeline, steps 01–10, plus `ssf_lex.py` (shared Wiktionary helpers) |
| `DATASHEET.md` | Datasheet for the dataset |

### Columns
| Column | Meaning |
|---|---|
| `rank` | Global rank by `est_per_million` |
| `lemma`, `pos` | Headword and Universal POS: the spaCy lemma, repaired against Wiktionary and `data/lemma_policy.json` (AUX merged into VERB; NUM included since v0.3) |
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
| `mx_status` | `common` / `uncommon` / `not_used` in Mexico (LLM judgement, then hand-reviewed; see "Mexican usage flags") |
| `non_mexican` | `true` if the sense is **regional**: not used, or uncommon, in Mexico specifically (Spain-only, South American, or misleading in Mexico like *coger*). It does **not** mark register; literary/archaic/formal senses are `false` and are labelled in `register` |
| `mx_equivalent` | Usual Mexican equivalent when flagged (e.g. *coger* "to take" → *tomar, agarrar*; *piso* "flat" → *departamento*) |
| `mx_note` | Short rationale (model, or manual for corrected rows) |
| `register` | `neutral` / `informal-slang` / `vulgar` / `offensive-slur` / `literary` / `archaic` / `formal` / `technical`: reasons a sense may be unsuitable to teach as ordinary vocabulary |
| `register_note` | Short reason (blank when neutral) |
| `register_source` | `wiktionary` (sense tag), `llm` or `manual` |
| `method` | `llm` (tagged by the model) or `single-sense` (the lemma had one usable Wiktionary sense, so share = 1 without tagging) |
| `example_1`, `example_2` | Short snippets (about ±60 characters) with the target marked `[[...]]` |

## Method
1. **Corpus.** All text was streamed and sampled; nothing was downloaded in bulk. Totals by word count (5.80M alphabetic tokens after spaCy):

   | Genre | Share | Tokens | Source |
   |---|---|---|---|
   | Subtitles | 50% | 2.87M | OPUS OpenSubtitles v2024, Spanish monolingual. Sparse 4-line blocks sampled from the first ~85M lines of the file |
   | News | 25% | 1.47M | `stanford-oval/ccnews` 2023 (CC-NEWS), Spanish. Every `.mx` article kept; other Spanish-language articles kept at 40% to favour Mexico |
   | Fiction | 25% | 1.46M | Project Gutenberg Spanish (`manu/project_gutenberg`). Random 3,000-character passages from the body of each book |

2. **Lemmatisation and frequency** (rewritten in v0.3; see AUDIT.md).
   - spaCy `es_core_news_md` gives lemma + UPOS. NUM is included.
   - Rules from `data/lemma_policy.json` come first:
     - *muy* and *tan* get their own headwords.
     - Object and prepositional pronouns, *ella*, *ello* and the neutral demonstratives are separate headwords.
     - Accent variants are merged (*sólo* → *solo*).
   - Then any lemma that is not a Wiktionary headword is re-resolved from its surface form. This fixes spaced clitic lemmas (*hacer él* → *hacer*), invented lemmas (*podriar* → *poder*), archaic spellings (*fué* → *ser*, *á* → *a*) and wrong POS (*siquiera* NOUN → ADV).
   - Common words tagged PROPN are rescued (*Hola* → *hola*).
   - Up to 40 contexts per lemma|POS are kept by reservoir sampling.
   - Every key with ≥144 tokens (24.8 per million) and usable Wiktionary senses is included. *os* and *vosotros* are excluded as Spain-only.
3. **Sense inventory.** From kaikki.org's Wiktionary extract:
   - Up to 8 senses per lemma|POS, in Wiktionary order.
   - Dropped: obsolete, archaic, rare, dated, and form-of senses, plus senses tagged *only* with a non-Mexican region.
   - v0.3 changes:
     - If tag filtering removes every sense, the filter is retried leniently (kaikki copies head-level notes onto all senses, e.g. *fin* "archaic").
     - Latin-America-tagged senses are kept (*manejar* "to drive").
     - Female-equivalent nouns keep their senses (*novia*).
     - Pronouns may use form-of glosses (*me* "accusative of yo").
   - Mexico-tagged senses were always kept. (Spain-only senses were excluded here; see "Mexican usage flags".)
   - Every prompt also offered "other / idiom" and "not this word".
4. **Tagging.**
   - 25 random contexts per lemma, 10 contexts per request.
   - Model: `gpt-5.6-luna`, `reasoning_effort: low`, JSON output, via the OpenAI Batch API.
   - 1,701 lemmas needed tagging (5,103 requests, 42,525 contexts). The other 799 had a single sense.
   - Actual cost: **US$1.06** (Batch prices $0.10 per 1M input tokens, $0.60 per 1M output tokens).
   - v0.3 re-tagged only the 203 new or changed keys (609 requests, US$0.129) with the same prompt and model. All other keys keep their v0.2 contexts and labels.
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

**LLM results (before manual review):** 5,673 common, 514 uncommon, 26 not_used, 1 missing; 540 flagged. See "Manual review of the flags" below for the corrected counts.

**Spot-check (50 items):**
- **Who and how:** the AI agent checked the flags; it is not a native Mexican speaker. The sample was 14 known cases (*coger*, *piso*, *coche*, *carro*, *conducir*, *tío*, *vuestro*, *usted*, …), 18 random flagged rows and 18 random unflagged rows.
- **Agreement:** **48/50 (96%).**
- **Misses:** *cañón* "projector" was marked not_used, but it is common in Mexico. *conducir* "to drive" was marked common, but *manejar* is the everyday word; this one is borderline because *licencia de conducir* is standard.

**Caveats:**
- The LLM's `uncommon` mixed regional senses with literary/archaic ones. Fixed by hand in v0.2 (below).
- Unflagged rows were not all re-reviewed. A few regional senses may still be marked common (e.g. *conducir* "to drive", borderline).
- Senses Wiktionary marks only for Spain (*piso* = flat, *móvil* = phone) are not separate rows; they sit inside `other`.
- Spain-only lemmas with no general sense (*ordenador*, *zumo*, *vosotros*) are absent from the list entirely.

### Manual review of the flags (v0.2)
The LLM flags mixed register with region: about 9 in 10 flagged rows were literary, archaic, formal or technical senses, or artefacts of the example snippet, not regional usage. All 540 flagged rows were reviewed by hand. The reviewer was the AI agent, not a native speaker.
- **Kept as regional: 67.** Examples: *coger* "to take/catch" (not_used: vulgar in Mexico), *piso* "flat" (→ *departamento*), *vuestro*, *planta* "floor of a building" (→ *piso*), *ingresar* "to deposit", *luna* "windshield" (→ *parabrisas*), *suspender* "to fail an exam" (→ *reprobar*), *baja* "sick leave" (→ *incapacidad*), *americana* "jacket" (→ *saco*), *estancia* "ranch" (South America), *policial* (→ *policiaco*).
- **Unflagged: 473.** These were set to `common`, with `mx_equivalent` cleared. Examples: *hallar*, *rostro*, *cañón* "projector" (common in Mexico), *tomar el pelo* (common), *culo* (vulgar but not regional), *legua*, *ama* "wet nurse".
- **Filled:** *pelear|VERB|6* "fall out with someone" → `common`.
- **Not added:** no new words or senses were added in v0.2. Spain-only senses still sit inside `other`, and Spain-only lemmas remain absent.
- **v0.3:** the 418 new or changed rows were labelled with the same prompts (US$0.013). All 96 rows the LLM marked non-neutral or non-Mexican were hand-reviewed and 42 were changed (`manual_v03_review.json`). Regional rows that were kept: *vos* (voseo), *joder* exclamation (Spain), *perras* "money", *de media*, *biblioteca* "bookcase". Current counts: see `data/summary.json`. **`non_mexican = true` for 79 rows.**
- **Final counts:** 6,147 common, 57 uncommon, 10 not_used; **`non_mexican = true` for 67 rows.** Every change is logged in `manual_corrections.csv`.

## Register / usage labels (v0.2)
1. **Wiktionary seed.** Sense tags from kaikki.org were mapped as follows: vulgar → `vulgar`; offensive/derogatory/pejorative/slur → `offensive-slur`; archaic/obsolete/dated/historical → `archaic`; literary/poetic → `literary`; colloquial/slang/informal → `informal-slang`; formal → `formal`. This covered 117 numbered senses.
2. **LLM for the rest.** `gpt-5.6-luna`, Batch API, reasoning low, 25 rows per request.
   - Numbered senses were judged from lemma + POS + gloss only. `other` rows were judged from their example.
   - A first pass that also showed examples was discarded: the genre of the snippet leaked into the label (e.g. *verde* "green" marked literary because the example was a poem).
   - Cost: **US$0.25** in total, including the discarded pass. The cap was $0.50.
3. **Hand review.** Every non-neutral row in the top 2,000 ranks was reviewed (150 in pass 1, 112 in pass 2), covering all vulgar, offensive, archaic and literary rows. 30 rows were overridden. Examples:
   - over-broad Wiktionary "informal/colloquial" tags reset to neutral: *tú*, *mamá*, *papá*, *regresar*, *agregar*, *tomar* "to drink"
   - *amar* and *bello* literary → neutral
   - *hallar* → formal
   - mild insults (*tonto*, *idiota*, *estúpido*) → `informal-slang`, not `offensive-slur`
   - *indio* (as an insult) kept as `offensive-slur`
4. **Counts (all 6,553, v0.3):** neutral 5,622 · technical 341 · formal 183 · informal-slang 169 · literary 115 · archaic 69 · vulgar 29 · offensive-slur 25. v0.3 rows were labelled the same way (US$0.007), with hand review of every non-neutral new row.
5. **Spot-check:** 50 random rows, checked by the agent. Agreement **48/50 (96%)**. The two misses were fixed: *entero* "intact" was wrongly marked informal from a Wiktionary tag, and *mal ninguno* is archaic.
6. **Caveats:**
   - `technical` and `formal` beyond rank 2,000 are unreviewed LLM labels. They are generous; e.g. legal senses such as *causa* "lawsuit" are labelled technical.
   - `register` is one label per sense. A word that is neutral in one sense can be vulgar in another (*huevo*, *polvo*), so filter by `sense_id`, not by lemma.

## Safe cutoff (how far the ranking is provably complete)
No sense can be more frequent than its lemma. The most frequent lemma\|POS **not** included (with Wiktionary senses) occurs **24.6 per million**. A sense whose estimated frequency exceeds that cannot be outranked by any sense left out of the list. The calculation excludes *os*/*vosotros*, which are left out on purpose.

| Criterion | v0.3: complete through rank | v0.2 | Meaning |
|---|---|---|---|
| Point estimate (`est_per_million` > 24.6) | **3,089** | 2,878 | Using point estimates, no omitted sense could rank higher |
| Lower 95% bound (`est_per_million_low` > 24.6) | **653** | 581 | Holds even at the low end of the interval. Column `rank_safe` is `true` for these |

v0.2's cutoff assumed the lemmatiser was right. It was not: *muy*, the clitic pronouns and the numerals were hidden inside other keys or dropped entirely, so v0.2's "safe" ranks were not actually complete. See AUDIT.md.

**Ordering reliability:** the CIs of neighbouring senses overlap heavily. The median rank band (`rank_max − rank_min`) is about **66 places for the top 100** and about **3,100 for the whole list**. Treat ranks beyond the first few hundred as coarse tiers, not an exact order.

## Quality check
- **Spot-check:** I hand-checked 100 random tagged items and agreed with the model on **96/100**. Five more were borderline because the inventory itself was weak.
- **Who checked:** the checker was the AI agent that built the pipeline, not a human expert.
- **What was sampled:** the spot-check drew only from the first 1,900 of 5,103 requests, i.e. the most frequent lemmas.
- **Earlier pilot:** a 100-item pilot gave 86–88% agreement before the spaCy lemma filter was added.

## Caveats
- **LLM-tagged, 25 samples per lemma.** At n = 25 a 50% share has a CI of roughly 31–69%. Minor senses are noisy, and senses with 0 hits may still exist.
- **The sense inventory comes from Wiktionary.** Its granularity is uneven. Some lemmas have near-duplicate senses, e.g. *y* "and" appears twice and *resto* has "rest, remainder" / "remainder". Some meanings are missing and fall into `other`.
- **Function words are still coarse.** `el|DET` includes the feminine article *la*, which Wiktionary lists under a separate entry, so most *el* tokens land in `other`. Since v0.3 the clitics (*lo, le, se, me, te, nos*) and *ella/ello* are separate headwords. Their Wiktionary glosses are terse (*lo* "accusative of él…"), and `lo|PRON` covers *lo/la/los/las* as object clitics. Use content-word rows with more confidence.
- **Lemmatiser errors.** v0.3 repairs systematic errors (AUDIT.md). Rare tokens (<20 per key) are still occasionally mis-lemmatised; "not this word" removes some of them. Single-sense lemmas (`method=single-sense`) were not checked by the model.
- **Corpus bias.**
  - Fiction is public-domain, mostly 19th–early 20th century and often from Spain, with archaic spelling.
  - Subtitles come only from the earlier part of the OPUS file and include translated dialogue.
  - News is from 2023 only. It is weighted toward Mexico but is pan-Hispanic.
  - Mexican-usage flags are LLM judgements (see "Mexican usage flags").
- **Example snippets** are kept very short. See Licenses.

## Licenses and sources
- **Dataset:** CC BY-SA 4.0, because the glosses and sense inventory derive from Wiktionary (CC BY-SA). Attribution: Wiktionary contributors, via kaikki.org / wiktextract (Tatu Ylonen).
- **OpenSubtitles (OPUS):** provided for research. **No subtitle text is redistributed beyond short (≤142-character) example snippets**; only derived counts are released. Do not add longer subtitle excerpts.
- **CC-NEWS / Common Crawl:** subject to the Common Crawl Terms of Use. Only counts and short snippets are included.
- **Project Gutenberg:** public domain in the US.
- **Tags, Mexican flags and register labels:** generated with OpenAI `gpt-5.6-luna`. Total cost US$1.64:
  - v0.2: $1.06 for sense tags, $0.17 for Mexican flags, $0.25 for register labels
  - v0.3 re-run: $0.149
- **External lists used only for the audit (not redistributed):** hermitdave FrequencyWords (CC BY-SA 4.0), Wiktionary frequency lists (CC BY-SA).
- **Code** (`scripts/`): MIT.

## Reproducing and scaling
```bash
pip install -r requirements.txt && python -m spacy download es_core_news_md
cd work
python ../scripts/01_collect_corpus.py
python ../scripts/02_lemmatize_sample.py tokens && python ../scripts/02_lemmatize_sample.py resolve && python ../scripts/02_lemmatize_sample.py count
# write the top-N candidate keys to candidates.json, then:
python ../scripts/03_build_inventories.py candidates.json
# select keys with >=144 tokens and senses into top_lemmas.json (10_incremental.py select does this for an update run)
python ../scripts/04_tag_batch.py build
OPENAI_API_KEY=... python ../scripts/04_tag_batch.py run 1600 <CAP_USD>
python ../scripts/05_analyze.py
python ../scripts/06_mexico_flags.py build && python ../scripts/06_mexico_flags.py run <CAP_USD> && python ../scripts/06_mexico_flags.py merge
python ../scripts/07_manual_mx_review.py ../data/manual_mx_decisions.json   # run in a dir holding the CSV
python ../scripts/08_register.py seed && python ../scripts/08_register.py build
python ../scripts/08_register.py run <CAP_USD> && python ../scripts/08_register.py merge
python ../scripts/08_register.py manual ../data/manual_register_overrides.json manual_corrections.csv
python ../scripts/09_audit.py --top 2000      # missing-words audit (closed-class checklist + external lists)
```
**Updating an existing release** (what v0.3 did): re-run 02 in a new work dir. Then run `10_incremental.py select OLD_DIR`, tag `tag/` with 04, then `collect`, then 05. Next, `carry OLD_CSV`, run 06/08 in `inc/`, then `fold`, then `manual ../data/manual_v03_review.json manual_corrections.csv`.

**Scaling to 10,000 lemmas:**
- A lemma at rank 10,000 occurs only a few times per million words, so the corpus must grow to about **25–40M tokens**. Raise `TARGET` in `01_collect_corpus.py`.
- Expected tagging cost is about **US$5–8**: roughly 4–6× the current run, since later lemmas have fewer senses and more of them have a single sense.
- `04_tag_batch.py` enforces a hard spending cap. It submits in frequency order and projects the cost of each chunk before submitting it.
- `05_analyze.py` recomputes the safe cutoff automatically.

## Citation
```
Taylor, Luc (2026). Spanish Sense Frequency List v0.3. https://github.com/godshiva/spanish-sense-freq
```
