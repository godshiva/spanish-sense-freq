"""Fetch kaikki.org Wiktionary JSONL per lemma; build <=8 senses per lemma|POS.
Rules: drop obsolete/archaic/rare/dated/form-of/abbreviation senses; drop senses tagged ONLY with
non-Mexican regions; always keep Mexico-tagged senses; then fill in Wiktionary order.
Adds 'other/idiom' and 'not this word'."""
import json, urllib.request, urllib.parse, concurrent.futures as cf, sys
POSMAP={"NOUN":{"noun"},"VERB":{"verb"},"ADJ":{"adj"},"ADV":{"adv"},"PRON":{"pron"},"DET":{"det","article"},
        "ADP":{"prep","prep_phrase"},"CCONJ":{"conj"},"SCONJ":{"conj"},"INTJ":{"intj"}}
FALLBACK={"NOUN":{"noun"},"VERB":{"verb"},"ADJ":{"adj","det"},"ADV":{"adv","adj","intj","pron"},"PRON":{"pron","det","adv"},"DET":{"det","article","pron","adj"},"ADP":{"prep","prep_phrase","conj"},"CCONJ":{"conj","adv"},"SCONJ":{"conj","adv","pron"},"INTJ":{"intj","phrase","noun","verb","adv"}}
DROP={"obsolete","archaic","rare","dated","form-of","misspelling"}
REGIONS={"Spain","Argentina","Rioplatense","Uruguay","Chile","Peru","Colombia","Venezuela","Cuba","Caribbean",
 "Puerto-Rico","Dominican-Republic","Bolivia","Ecuador","Paraguay","Central-America","Costa-Rica","Honduras",
 "Nicaragua","El-Salvador","Guatemala","Panama","Philippines","Andes","Canary-Islands","Equatorial-Guinea","Andalusia"}
def fetch(w):
    q=urllib.parse.quote
    url=f"https://kaikki.org/dictionary/Spanish/meaning/{q(w[0])}/{q(w[:2])}/{q(w)}.jsonl"
    try: return [json.loads(l) for l in urllib.request.urlopen(url,timeout=60).read().decode().splitlines()]
    except Exception: return []
def build(key,entries,anypos=False):
    w,pos=key.split("|"); cand=[]
    for e in entries:
        if e.get("word")!=w or (e.get("pos") not in (FALLBACK[pos] if anypos else POSMAP[pos])) or e.get("pos") in ("name","character","suffix","prefix"): continue
        for s in e.get("senses",[]):
            tags=set(s.get("tags",[])); raw=" ".join(s.get("raw_glosses") or [])
            gl=(s.get("glosses") or [""])[-1].strip()
            if not gl or tags&DROP or s.get("form_of"): continue
            mx="Mexico" in tags or "Mexico" in raw
            regs={t for t in tags if t in REGIONS}
            if regs and not mx: continue
            cand.append({"gloss":gl[:160],"mexico":mx,"tags":sorted(tags)[:6]})
    mxs=[c for c in cand if c["mexico"]][:3]
    rest=[c for c in cand if not c["mexico"]]
    chosen=(rest[:8-len(mxs)]+mxs) if cand else []
    # keep Wiktionary order among chosen
    chosen=sorted(chosen,key=lambda c:cand.index(c))
    if not chosen and not anypos: return build(key,entries,True)
    return chosen
if __name__=="__main__":
    keys=json.load(open(sys.argv[1] if len(sys.argv)>1 else "top_lemmas.json"))
    words=sorted({k.split("|")[0] for k in keys})
    with cf.ThreadPoolExecutor(12) as ex: data=dict(zip(words,ex.map(fetch,words)))
    inv={}
    for k in keys:
        s=build(k,data[k.split("|")[0]])
        inv[k]=s
    json.dump(inv,open("inventories.json","w"),ensure_ascii=False,indent=0)
    print("lemmas",len(inv),"with senses",sum(1 for v in inv.values() if v),"avg",sum(len(v) for v in inv.values())/len(inv))
