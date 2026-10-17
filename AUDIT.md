# Missing-words audit (v0.2 → v0.3)

**Trigger:** *muy* was missing from v0.2. This audit looked for every high-frequency word missing from the list, traced each gap to a pipeline cause, and fixed the pipeline rather than inserting rows by hand. Every added row was produced by the same corpus counts, Wiktionary inventories and LLM tagging as the rest of the list.

Reviewer for the hand checks: the AI agent that built the pipeline (not a native speaker), working for Luc Taylor.

## Summary

| | v0.2 | v0.3 |
|---|---|---|
| lemma\|POS keys | 2,500 | 2,642 (+146 added, −4 merged into their full forms) |
| sense rows | 6,214 | 6,553 |
| core closed-class words missing (checklist below) | **38** | **0** |
| gaps in Wiktionary Spanish 1–2000 (lemma-mapped) | 95 | 41, all explained (below) |
| gaps in hermitdave FrequencyWords es top 2000 | 167 | 112 (names, abbreviations, English tokens, below threshold) |
| gaps in Buchmeier Wiktionary list top 2000 | 180 | 122 (same categories) |
| safe cutoff, point estimate | rank 2,878 | **rank 3,089** |
| safe cutoff, lower 95% bound | rank 581 | **rank 653** |
| extra OpenAI spend | | **US$0.149** (cap $1.50) |

## Root causes

1. **spaCy merges distinct words into another lemma.** `es_core_news_md` lemmatises *muy* → *mucho* and *tan* → *tanto*. Wiktionary agrees: it lists *muy* only as an "apocopic form of mucho", so the v0.2 lookup kept the merge. It also folds pronouns together: *ella, ello, lo, la, le, les, se* → *él*; *me, mí, conmigo, nos, nosotros* → *yo*; *te, ti, contigo, os, ustedes* → *tú*. The neutral demonstratives go too (*esto* → *este*, *eso* → *ese*, *aquello* → *aquel*). As a result, `él|PRON` held 174,934 tokens in v0.2, but only 12,828 of them are really *él/ellos*. *muy* (11,958 tokens) was hidden inside `mucho|ADV`.
2. **NUM was excluded.** Step 02 kept only NOUN, VERB, ADJ, ADV, PRON, DET, ADP, CCONJ, SCONJ and INTJ. Every cardinal number was dropped: *dos* (8,621), *tres*, *cuatro*, … *mil*, *ciento*, plus *ambos*. PART (*no* in some contexts) was also dropped.
3. **Clitic verbs got spaced or invented lemmas.** Examples: *hacerlo* → "hacer él", *casarme* → "casar yo", *dímelo* → "dímelir", *muevas* → "mueir", *quieres* → "quieres", *podrías* → "podriar". That moved 45,916 tokens onto keys with spaces (e.g. "hacer él" 2,323) and about 120k more onto invented or inflected lemmas. The base verbs were undercounted: *dejar* by 30%, *escuchar* by 41%, *callar* by 73%.
4. **Archaic spellings and accent variants were split off.** *á*, *ó*, *é* and *fué* (from Gutenberg fiction), *sólo* versus *solo*, *quizás* versus *quizá*, and *éste/ése/aquél* versus *este/ese/aquel* each formed their own keys. Some were dropped (no Wiktionary entry) and the rest were counted separately.
5. **Wrong POS.** Examples: *siquiera* NOUN, *serio* NOUN, *partir* NOUN (*a partir de*), *desde* NOUN, *tan* NOUN. The inventory lookup was keyed on the wrong POS, found no senses, and dropped the key.
6. **Common words tagged PROPN.** spaCy tags sentence-initial *Hola* (3,250 tokens) as a proper noun. The same happened to many *Dios*, *Escucha*, *Buenas*, *Disculpe* and similar tokens. PROPN was never counted.
7. **Wiktionary inventory filters dropped real words.**
   - kaikki copies head-level notes onto every sense. *fin* has "archaic" on all of its senses because of a gender note, and *lindo* has "dated" (true only in Spain). The DROP-tag filter therefore removed every sense.
   - Senses tagged with a Latin-America tag **and** a Spain-area tag (e.g. *ustedes*: "Latin-America, Canary-Islands") were treated as non-Mexican regional senses and dropped.
   - Female-equivalent nouns (*novia, amiga, tía, muchacha, secretaria, compañera*) are marked `form-of` throughout and were dropped.
   - Closed-class words that Wiktionary lists only as forms (*lo, eso, ti*) had no senses.
8. **Selection silently skipped keys with no senses.** The v0.2 selection took "the first 2,500 keys that have senses", so causes 3–7 removed words without any error. Of the top 2,661 v0.2 candidates, 161 were skipped (`data/audit/skipped_categories.json`):

   | Count | Skip reason | Examples |
   |---|---|---|
   | 76 | form-of only (inflected/apocopated/archaic spelling kept as lemma) | *á, sólo, fué, has, déjame, peor, dólares, órden* |
   | 38 | no Wiktionary page: spaCy-invented lemma or foreign token | *podriar, deberiar, estár, demá, in, io* |
   | 37 | POS mismatch | *siquiera* NOUN, *del* DET, *veces* NOUN, *según* SCONJ |
   | 6 | female-equivalent noun | *novia, amiga, tía, muchacha* |
   | 4 | every sense dropped by copied tags | *fin, lindo, cuidado* ADJ, *completo* NOUN |

   Causes 1, 2 and 6 never even produced a key, so they did not appear among the skips. They were found only through the closed-class checklist and the external lists.

## Fixes (pipeline, not hand inserts)

- **`scripts/02_lemmatize_sample.py`** now runs three stages: `tokens`, `resolve` and `count`. NUM is kept, and PART maps to ADV.
  - **Headword policy** (`data/lemma_policy.json`, 48 documented rules, applied first):
    - *muy*, *tan* get their own headwords (DLE practice).
    - Object and prepositional pronouns are separate: *me, te, se, nos, mí, ti, sí, conmigo, contigo, consigo, lo* (*lo/la/los/las* clitic), *le* (*le/les*).
    - *ella* (*ella/ellas*), *ello*, *nosotros*, *ustedes* are separate, as are the neutral demonstratives *esto, eso, aquello*.
    - Accent variants are merged into RAE 2010 spellings: *sólo* → *solo*, *éste* → *este*.
    - *mi/tu/su* and *mejor/peor* stay their own headwords, as in v0.2.
    - *del/al* stay under *de/a*, as in v0.2.
    - A few spaCy-specific repairs (*sé* → *saber*, *ven* → *venir*, *es* NOUN → *ser*), and drops for English/Italian noise.
    - Gender/number inflections still share a headword (*la/las* → *el*, *linda* → *lindo*). Apocopes covered by the DLE entry of the full form are merged (*buen* → *bueno*, *gran* → *grande*, *algún* → *alguno*, *tercer* → *tercero*).
  - **Wiktionary repair** (`scripts/ssf_lex.py`). Any key with ≥20 tokens whose lemma is not a Wiktionary headword is re-resolved per surface form. The steps are tried in order: spaCy lemma (first word of a spaced lemma), then the surface itself, then form-of/alt-of targets (two hops, e.g. *dímelo* → *di* → *decir*), then POS repair. Ties are broken by corpus frequency. Archaic accents reuse spaCy's analysis of the modern spelling (*fué* → *fue* → *ser*). 120,219 tokens were repaired.
  - **PROPN rescue.** Lower-case PROPN tokens, and sentence-initial ones whose capitalised form is not a Wiktionary proper name, are counted as the common word. This covers 1,686 types: *hola*, *buenas*, *escucha* → *escuchar*.
- **`scripts/03_build_inventories.py`**:
  - cached kaikki fetch with retries (a fetch failure now raises instead of returning nothing)
  - lenient retry when copied tags remove every sense (*fin, lindo*)
  - Latin-America/US-tagged senses are no longer dropped as regional (*ustedes*, *manejar* "to drive", *usted* "you")
  - female-equivalent senses are kept
  - form-of senses are allowed for pronouns
  - NUM is supported
  - an upper-case fallback (*ok* → *OK*)
- **`scripts/10_incremental.py`** re-runs only what changed:
  - new keys
  - v0.2 keys whose corrected count moved by more than 25%: 142 keys, e.g. *él, yo, tú, mucho, tanto, bueno, grande, solo, dejar, callar*
  - 20 v0.2 keys whose inventory changed under the new 03 rules (e.g. *usted, tomar, manejar, agua, acá, chica*)

  That is 203 re-tagged keys (609 Batch requests). Every other key keeps its v0.2 inventory, contexts and labels, so its sense ids are unchanged. Mexican flags and register labels were carried over by `sense_id` (with identical gloss) for 6,135 rows. The 418 new or changed rows were labelled with the same 06/08 prompts.
- **Hand review:** every new row that the LLM marked non-neutral or non-Mexican (96 rows, all ranks) was reviewed; 42 rows were changed (`data/manual_v03_review.json`, logged in `manual_corrections.csv`). Examples:
  - *fin* "archaic" → neutral (copied tag)
  - *lindo* "dated" → neutral
  - *ello*, *habitar* uncommon → common (register, not region)
  - *vos* kept non-Mexican (voseo) but not archaic
  - *lárgate* offensive-slur → informal-slang
- **Spot-check of new tags:** 30 random new labels, 29/30 agree (1 borderline: *¡Perdón!* tagged `other`).

## Spain-only words: noted, not added
- **`os|PRON` (1,628 tokens) and `vosotros|PRON` (481):** now counted separately, so they no longer inflate *tú*. They are excluded from the list (`SPAIN_ONLY` in `10_incremental.py`) and left out of the safe-cutoff calculation.
- **`vuestro`:** already in v0.2, unchanged and flagged non-Mexican.
- **Spain-only senses** of added words (*joder* as an exclamation, *perras* "money", *de media* "on average", *teniente de alcalde*) are rows flagged `non_mexican = true`, as in v0.2.

## Closed-class checklist (all present in v0.3)
determiners *el uno este ese aquel mi tu su nuestro mucho poco todo otro alguno ninguno cualquiera cada varios demasiado bastante tanto mismo propio cierto tal ambos* · pronouns *yo tú usted él ella ello nosotros ustedes me te se lo le nos mí ti sí conmigo contigo consigo esto eso aquello algo nada alguien nadie quien que cual cuyo mío tuyo suyo* · prepositions *a ante bajo con contra de desde durante en entre hacia hasta mediante para por según sin sobre tras* · conjunctions *y e o u ni pero sino que porque aunque si como cuando mientras pues* · adverbs *muy más menos ya también tampoco siempre nunca jamás aún todavía casi solo bien mal ahora hoy ayer mañana aquí allí allá acá ahí entonces luego después antes tan así sí no quizá donde* · numerals *dos … diez once doce veinte treinta cien ciento mil millón primero segundo tercero* · question words *qué quién cuál cuánto dónde cuándo cómo adónde porqué*.

v0.2 was missing 38 of these: *muy, tan, ella, ello, nosotros, ustedes, me, te, se, lo, le, nos, mí, ti, conmigo, contigo, consigo, esto, eso, aquello, ambos, porqué* and every numeral from *dos* to *mil*.

## External cross-checks
`scripts/09_audit.py` maps each external surface form to our lemma (via `surface_lemma.json` from 02, or the list's own lemma column) and reports every gap with a reason. The lists used:
- [hermitdave FrequencyWords](https://github.com/hermitdave/FrequencyWords) `es_50k` (2018, OpenSubtitles)
- [Wiktionary:Frequency lists/Spanish1000](https://en.wiktionary.org/wiki/Wiktionary:Frequency_lists/Spanish1000) and 1001–2000, which have a lemma column
- [User:Matthias Buchmeier's Spanish frequency list](https://en.wiktionary.org/wiki/User:Matthias_Buchmeier/Spanish_frequency_list-1-5000) (1–10000)

RAE CREA/CORPES lists were not reachable from the build machine (corpus.rae.es timed out), and the Davies list is not freely downloadable, so neither was used. The external lists are not redistributed; `09_audit.py` documents where to fetch them.

The 41 Wiktionary-2000 gaps remaining in v0.3:
- **30 below the tagging threshold** (24.8 per million in this corpus), mostly subtitle-specific words: *papi, mami, grandioso, definitivamente, majestad, caray, gratis, virus, sospechoso, bastardo, robot*. *lana* "money" is also here, at 7.9/M. *navidad* is mostly capitalised mid-sentence (*Feliz Navidad*) and counted as a proper name.
- **5 proper names** absent from the counts (*Londres, París, México, Europa, EEUU*).
- **4 abbreviations** (*Dra., Mr., km, TV*).
- **2 Spain-only** (*os, vosotros*).

No gap above the threshold remains in any of the three lists. The threshold is the same one the safe cutoff is built on, so it is not a silent omission: any lemma below 24.8/M sits beyond the point-estimate safe cutoff (rank 3,089).

## Re-running the audit
```bash
cd work   # after 02 count and 05 (and 06–08)
mkdir -p audit   # es_50k.txt (hermitdave), wikt2000.json, buchmeier10k.json (see docstring)
python ../scripts/09_audit.py --csv spanish_sense_frequency.csv --top 2000
```
The exit code is 1 if a core closed-class word (other than the Spain-only exclusions) is missing. The full report is written to `audit_report.json` (v0.3 copy in `data/audit/`).

## Known limits
- Ranks of v0.2 keys whose counts changed by ≤25% were not re-tagged. Their shares are unchanged, but their lemma frequency was updated.
- **PROPN rescue** is heuristic. Sentence-initial names that are also common nouns (*Rosa*, *Sol*) can add a few tokens to the common noun.
- **`me|PRON`** keeps the Wiktionary gloss structure (accusative/dative/reflexive). **`lo|PRON`** has one long form-of gloss.
- **`medio|NUM`** (*media hora*) is now separate from `medio|NOUN/ADJ`.
