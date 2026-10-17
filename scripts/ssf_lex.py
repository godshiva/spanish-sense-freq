"""Shared lexicon helpers (v0.3): cached kaikki.org Wiktionary lookups with retries, and the
lemma-resolution rules used by 02_lemmatize_sample.py to repair spaCy lemma/POS errors.

v0.2 bug: a failed kaikki fetch silently returned [] and the lemma was dropped as "no senses".
Now fetches retry with backoff, 404s are cached as empty, and any other failure raises."""
import json, os, re, time, unicodedata, urllib.request, urllib.parse, urllib.error
CACHE=os.environ.get("SSF_KCACHE","kcache")
POSMAP={"NOUN":{"noun"},"VERB":{"verb"},"ADJ":{"adj"},"ADV":{"adv"},"PRON":{"pron"},"DET":{"det","article"},
        "ADP":{"prep","prep_phrase"},"CCONJ":{"conj"},"SCONJ":{"conj"},"INTJ":{"intj"},"NUM":{"num"}}
FALLBACK={"NOUN":{"noun"},"VERB":{"verb"},"ADJ":{"adj","det"},"ADV":{"adv","adj","intj","pron"},"PRON":{"pron","det","adv"},
          "DET":{"det","article","pron","adj"},"ADP":{"prep","prep_phrase","conj"},"CCONJ":{"conj","adv"},"SCONJ":{"conj","adv","pron"},
          "INTJ":{"intj","phrase","noun","verb","adv"},"NUM":{"num","adj","det","pron","noun"}}
# Wiktionary POS -> UPOS, used for POS repair (first lemma-bearing entry wins)
K2U={"noun":"NOUN","verb":"VERB","adj":"ADJ","adv":"ADV","pron":"PRON","det":"DET","article":"DET","prep":"ADP",
     "prep_phrase":"ADP","conj":"CCONJ","intj":"INTJ","num":"NUM","phrase":"INTJ"}
UA="spanish-sense-freq/0.3 (+https://github.com/godshiva/spanish-sense-freq)"
BADSENSE={"misspelling","form-of","alt-of"}   # archaic/dated tags are NOT used here: kaikki copies head-level notes onto every sense (fin: "archaic feminine"; lindo: "dated" in Spain)
def _path(w): return os.path.join(CACHE,urllib.parse.quote(w,safe="")+".jsonl")
def fetch(w):
    p=_path(w)
    if os.path.exists(p): return [json.loads(l) for l in open(p) if l.strip()]
    q=urllib.parse.quote; url=f"https://kaikki.org/dictionary/Spanish/meaning/{q(w[0])}/{q(w[:2])}/{q(w)}.jsonl"
    for a in range(6):
        try: txt=urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":UA}),timeout=20).read().decode(); break
        except urllib.error.HTTPError as e:
            if e.code==404: txt=""; break
            time.sleep(2**a)
        except Exception: time.sleep(2**a)
    else: raise RuntimeError("kaikki fetch failed: "+w)
    os.makedirs(CACHE,exist_ok=True); open(p,"w").write(txt)
    return [json.loads(l) for l in txt.splitlines() if l.strip()]
def entries(w,kpos):
    return [e for e in fetch(w) if e.get("word")==w and e.get("pos") in kpos]
FEM=re.compile(r"^(female|feminine) equivalent of ",re.I)
def lemma_senses(e):
    """senses that make the word a headword: not form-of/alt-of/obsolete; 'female equivalent of X' nouns
    (novia, amiga, tía) count as headwords, as in the Wiktionary frequency lists."""
    out=[]
    for s in e.get("senses",[]):
        g=(s.get("glosses") or [""])[-1]
        if FEM.match(g) and e.get("pos")=="noun": out.append(s); continue
        if not s.get("form_of") and not s.get("alt_of") and not set(s.get("tags",[]))&BADSENSE: out.append(s)
    return out
def is_lemma(w,upos):
    return any(lemma_senses(e) for e in entries(w,FALLBACK[upos]))
def own_pos(w):
    """UPOS values under which w itself is a Wiktionary headword, in Wiktionary order."""
    out=[]
    for e in fetch(w):
        if e.get("word")==w and e.get("pos") in K2U and lemma_senses(e) and K2U[e["pos"]] not in out: out.append(K2U[e["pos"]])
    return out
def form_targets(w,kpos):
    out=[]
    for e in fetch(w):
        if e.get("word")!=w or e.get("pos") not in kpos: continue
        for s in e.get("senses",[]):
            if FEM.match((s.get("glosses") or [""])[-1]): continue
            for x in (s.get("form_of") or [])+(s.get("alt_of") or []):
                t=x.get("word","").split(" ")[0].lower()
                if t and t!=w and (t,e["pos"]) not in out: out.append((t,e["pos"]))
    return out
def unaccent(w):
    keep={"ñ","ü"}
    return "".join(c if c in keep else unicodedata.normalize("NFD",c)[0] for c in w)
def resolve(surface,lemma,upos,score=lambda k:0):
    """(lemma,UPOS) for a token whose spaCy key is not a Wiktionary headword, or None.
    Tiers (first non-empty wins; ties broken by corpus count via score('lemma|POS')):
      0 spaCy lemma or the surface itself is a headword in the same POS family
      1 Wiktionary form-of/alt-of targets in the same POS family (two hops: dímelo -> di -> decir)
      2 POS repair (never for VERB tokens): the surface is a headword, or a form of one, under another POS"""
    l0=lemma.split(" ")[0] if lemma else surface
    t0=[(c,upos) for c in dict.fromkeys([l0,surface]) if c and is_lemma(c,upos)]
    if t0: return max(t0,key=lambda x:score(x[0]+"|"+x[1]))
    t1=[]
    for c in dict.fromkeys([l0,surface]):
        for t,kp in form_targets(c,FALLBACK[upos]):
            u="VERB" if upos in ("INTJ","NOUN") and K2U.get(kp)=="VERB" else upos   # ¡Espere! -> esperar|VERB
            if is_lemma(t,u): t1.append((t,u))
            t1+=[(t2,u) for t2,_ in form_targets(t,FALLBACK[u]) if is_lemma(t2,u)]   # habia -> había -> haber
    if t1: return max(t1,key=lambda x:score(x[0]+"|"+x[1]))
    if upos=="VERB": return None
    t2=[(surface,u) for u in own_pos(surface)]
    t2+=[(t,K2U[kp]) for t,kp in form_targets(surface,set(K2U)) if K2U.get(kp) and is_lemma(t,K2U[kp])]
    if t2: return max(t2,key=lambda x:score(x[0]+"|"+x[1]))
    return None
