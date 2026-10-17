# Datasheet: Spanish Sense Frequency List v0.1
(Format follows Gebru et al., "Datasheets for Datasets".)

## Motivation
- **Purpose:** to order a Spanish curriculum by the most common *meanings*, not just the most common words. Mexican Spanish is preferred.
- **Creator:** Luc Taylor. The pipeline was run with an AI agent on 2026-10-16.
- **Funding:** none. The OpenAI tagging cost was US$1.06.

## Composition
- **Instances:** 6,214 sense rows covering 2,500 Spanish lemma|POS keys.
- **Per row:** gloss, share, 95% CI, estimated frequency per million, rank band, `rank_safe` flag, Mexico flag, and up to 2 short snippets.
- **Sampling:** each lemma was tagged on 25 random contexts drawn from a 5.8M-token stratified sample: 50% subtitles, 25% news, 25% fiction. This is a sample, not exhaustive counts.
- **Excluded data:** senses with zero hits are omitted. Lemmas with no matching Wiktionary entry were skipped; these were mostly lemmatiser errors and archaic spellings.
- **Missing labels:** none of the 5,103 requests failed.
- **Personal information:** no sensitive data is included. Snippets come from public news, subtitles, and public-domain books, and may contain names of public figures or fictional characters.

## Collection process
1. Text was streamed from public sources: OPUS OpenSubtitles v2024 (es), `stanford-oval/ccnews` 2023 (es, `.mx` favoured), and Project Gutenberg es.
2. Lemmas came from spaCy `es_core_news_md`.
3. Senses came from Wiktionary via kaikki.org, with ≤8 senses per lemma.
4. `gpt-5.6-luna` (reasoning low) tagged the contexts through the OpenAI Batch API.

## Preprocessing
- Spanish detection was by language field (news) and a stopword ratio (books).
- Deduplication was by MD5 hash of each segment.
- AUX was merged into VERB, and *del/al* into *de/a*.
- Only snippets of about ±60 characters were kept for release.
- Raw corpus segments are **not** released.

## Uses
- **Intended:** vocabulary sequencing and graded-reader design; prioritising which meanings to teach; research on sense distributions.
- **Not suitable:** fine-grained ranking beyond the first few hundred senses; definitive regional (Mexican) usage claims; function-word sense analysis; anything that treats the LLM tags as gold annotation.

## Known limitations
- Wiktionary sense granularity is uneven.
- Function-word inventories are poor (e.g. *el* vs *la*; clitics lemmatised to *él*).
- Fiction is archaic and Spain-heavy. Subtitles include translated films.
- n = 25 gives wide CIs.
- The single spot-check (96/100) was done by the AI agent on high-frequency lemmas only. Pilot accuracy against agent gold labels was 86–88%.

## Distribution
- **Where:** GitHub, https://github.com/godshiva/spanish-sense-freq (not yet published).
- **License:** CC BY-SA 4.0 for the data, MIT for the code.
- **Upstream terms:** OpenSubtitles (OPUS) is research-only, so subtitle text must not be redistributed beyond short snippets. Common Crawl Terms of Use apply to news snippets.

## Maintenance
- **Maintainer:** Luc Taylor.
- **Planned:** expansion to 10,000 lemmas with a larger corpus (25–40M tokens), better function-word inventories, a human-annotated evaluation set, and a stronger Mexican subtitle slice using IMDb country metadata.
