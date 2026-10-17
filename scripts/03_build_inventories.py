"""Fetch kaikki.org Wiktionary JSONL per lemma; build <=8 senses per lemma|POS.
Rules: drop obsolete/archaic/rare/dated/form-of/abbreviation senses; drop senses tagged ONLY with
non-Mexican regions; always keep Mexico-tagged senses; then fill in Wiktionary order.
Adds 'other/idiom' and 'not this word'."""
import json, re, os, concurrent.futures as cf, sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from ssf_lex import POSMAP, FALLBACK, fetch   # v0.3: cached fetch with retries (v0.2 dropped lemmas on transient fetch errors); NUM added
DROP={"obsolete","archaic","rare","dated","form-of","misspelling"}
REGIONS={"Spain","Argentina","Rioplatense","Uruguay","Chile","Peru","Colombia","Venezuela","Cuba","Caribbean",
 "Puerto-Rico","Dominican-Republic","Bolivia","Ecuador","Paraguay","Central-America","Costa-Rica","Honduras",
 "Nicaragua","El-Salvador","Guatemala","Panama","Philippines","Andes","Canary-Islands","Equatorial-Guinea","Andalusia"}
FEM=re.compile(r"^(female|feminine) equivalent of [^,;:]+[,;:]\s*",re.I); FEM0=re.compile(r"^(female|feminine) equivalent of ",re.I)
MXOK={"Mexico","Latin-America","Americas","North-America","US"}   # v0.3: a sense tagged e.g. 'Latin-America, Canary-Islands' is NOT region-only (ustedes)
def build(key,entries,anypos=False,lenient=False,forms=False):
    w,pos=key.split("|"); cand=[]
    if pos=="PRON": forms=True   # v0.3: object/prepositional pronouns are listed by Wiktionary as forms (me = object form of yo)
    for e in entries:
        if e.get("word")!=w or (e.get("pos") not in (FALLBACK[pos] if anypos else POSMAP[pos])) or e.get("pos") in ("name","character","suffix","prefix"): continue
        for s in e.get("senses",[]):
            tags=set(s.get("tags",[])); raw=" ".join(s.get("raw_glosses") or [])
            gl=(s.get("glosses") or [""])[-1].strip()
            if FEM0.match(gl) and pos=="NOUN":   # v0.3: novia/amiga/tía are separate headwords; keep their senses
                gl=FEM.sub("",gl).strip() or gl; tags-={"form-of"}
                if not gl: continue
            elif not gl or (not forms and ((tags&(DROP if not lenient else {"form-of","misspelling"})) or s.get("form_of"))): continue
            mx="Mexico" in tags or "Mexico" in raw
            regs={t for t in tags if t in REGIONS}
            if regs and not mx and not tags&MXOK: continue
            cand.append({"gloss":gl[:160],"mexico":mx,"tags":sorted(tags)[:6]})
    if not cand and not lenient and not anypos:   # v0.3: tags copied from head-level notes can drop every sense (fin, lindo)
        return build(key,entries,anypos,lenient=True)
    mxs=[c for c in cand if c["mexico"]][:3]
    rest=[c for c in cand if not c["mexico"]]
    chosen=(rest[:8-len(mxs)]+mxs) if cand else []
    # keep Wiktionary order among chosen
    chosen=sorted(chosen,key=lambda c:cand.index(c))
    if not chosen and not anypos: chosen=build(key,entries,True,lenient,forms)
    if not chosen and lenient and not forms and not anypos:   # v0.3: closed-class words Wiktionary only lists as forms (lo, eso, ti)
        chosen=build(key,entries,False,True,True)
    return chosen
if __name__=="__main__":
    keys=json.load(open(sys.argv[1] if len(sys.argv)>1 else "top_lemmas.json"))
    words=sorted({k.split("|")[0] for k in keys})
    def fetch2(w): return fetch(w) or [dict(e,word=w) for e in fetch(w.upper()) if e.get('word')==w.upper()]   # ok -> OK
    with cf.ThreadPoolExecutor(8) as ex: data=dict(zip(words,ex.map(fetch2,words)))
    inv={}
    for k in keys:
        s=build(k,data[k.split("|")[0]])
        inv[k]=s
    json.dump(inv,open("inventories.json","w"),ensure_ascii=False,indent=0)
    print("lemmas",len(inv),"with senses",sum(1 for v in inv.values() if v),"avg",sum(len(v) for v in inv.values())/len(inv))
