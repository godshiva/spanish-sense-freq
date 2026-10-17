# Datasheet: Spanish Sense Frequency List v0.3
(Format follows Gebru et al., "Datasheets for Datasets".)

## Motivation
- **Purpose:** to order a Spanish curriculum by the most common *meanings*, not just the most common words. Mexican Spanish is preferred.
- **Creator:** Luc Taylor. The pipeline was run with an AI agent on 2026-10-16. The v0.3 missing-words fix was made on 2026-10-17 (see AUDIT.md).
- **Funding:** none. OpenAI cost was US$1.06 for sense tags, US$0.17 for Mexican-usage flags and US$0.25 for register labels (US$1.49 total). The v0.3 re-run cost US$0.149.

## Composition
- **Instances:** 6,553 sense rows covering 2,642 Spanish lemma|POS keys.
- **Per row:** gloss, share, 95% CI, estimated frequency per million, rank band, `rank_safe` flag, Mexican-usage fields (`non_mexican`, `mx_status`, `mx_equivalent`, `mx_note`), register fields (`register`, `register_note`, `register_source`), and up to 2 short snippets (≤142 characters).
- **Sampling:** each lemma was tagged on 25 random contexts drawn from a 5.8M-token stratified sample: 50% subtitles, 25% news, 25% fiction. This is a sample, not exhaustive counts.
- **Excluded data:** senses with zero hits are omitted. Keys below 144 tokens (24.8/M) are not covered. Spain-only *os* and *vosotros* are excluded on purpose. Since v0.3, lemmatiser errors are repaired rather than skipped. In v0.2 such skips (and spaCy merges such as *muy* → *mucho*) silently removed core words; see AUDIT.md.
- **Missing labels:** none of the 5,103 (v0.2) + 609 (v0.3) tagging requests failed.
- **Personal information:** no sensitive data is included. Snippets come from public news, subtitles, and public-domain books, and may contain names of public figures or fictional characters.

## Collection process
1. Text was streamed from public sources: OPUS OpenSubtitles v2024 (es), `stanford-oval/ccnews` 2023 (es, `.mx` favoured), and Project Gutenberg es.
2. Lemmas came from spaCy `es_core_news_md`, repaired against Wiktionary and a documented headword policy (`data/lemma_policy.json`, v0.3).
3. Senses came from Wiktionary via kaikki.org, with ≤8 senses per lemma.
4. `gpt-5.6-luna` (reasoning low) tagged the contexts through the OpenAI Batch API.
5. The same model classified each sense as common, uncommon or not_used in Mexico, with Wiktionary regional labels as hints. A 50-item agent spot-check agreed 96%.
6. All 540 flagged rows were then hand-reviewed by the agent. 67 are kept as regional; 473 were literary, archaic or formal rather than regional and were unflagged. Every change is logged in `data/manual_corrections.csv`.
7. Register labels were seeded from Wiktionary sense tags; the rest were classified by `gpt-5.6-luna` (Batch API, gloss only). Non-neutral rows in the top 2,000 were hand-reviewed. A 50-row random spot-check agreed 96%.
8. v0.3: only new and changed keys were re-tagged and re-labelled. Every new non-neutral or non-Mexican row was hand-reviewed (42 changes, logged).

## Preprocessing
- Spanish detection was by language field (news) and a stopword ratio (books).
- Deduplication was by MD5 hash of each segment.
- AUX was merged into VERB, and *del/al* into *de/a*. NUM is kept (v0.3).
- Only snippets of about ±60 characters were kept for release.
- Raw corpus segments are **not** released.

## Uses
- **Intended:** vocabulary sequencing and graded-reader design; prioritising which meanings to teach; research on sense distributions.
- **Not suitable:** fine-grained ranking beyond the first few hundred senses; definitive regional (Mexican) usage claims; function-word sense analysis; anything that treats the LLM tags as gold annotation.

## Known limitations
- Wiktionary sense granularity is uneven.
- Function-word inventories are coarse (e.g. *el* vs *la*). Clitic pronouns are separate headwords since v0.3, but their Wiktionary glosses are terse.
- Mexican flags are LLM judgements, hand-corrected by the AI agent (not a native speaker). Spain-only lemmas such as *ordenador*, *os* and *vosotros* are absent, and Spain-only senses sit inside `other`.
- Register labels beyond rank 2,000 are unreviewed LLM output; `technical`/`formal` are generous.
- Fiction is archaic and Spain-heavy. Subtitles include translated films.
- n = 25 gives wide CIs.
- The single spot-check (96/100) was done by the AI agent on high-frequency lemmas only. Pilot accuracy against agent gold labels was 86–88%.

## Distribution
- **Where:** GitHub, https://github.com/godshiva/spanish-sense-freq .
- **License:** CC BY-SA 4.0 for the data, MIT for the code.
- **Upstream terms:** OpenSubtitles (OPUS) is research-only, so subtitle text must not be redistributed beyond short snippets. Common Crawl Terms of Use apply to news snippets.

## Maintenance
- **Maintainer:** Luc Taylor.
- **Planned:** expansion to 10,000 lemmas with a larger corpus (25–40M tokens), better function-word inventories, a human-annotated evaluation set, and a stronger Mexican subtitle slice using IMDb country metadata.
