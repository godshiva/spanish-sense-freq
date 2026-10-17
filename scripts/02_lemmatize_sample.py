"""spaCy es_core_news_md lemma+POS counts with Wiktionary-based repair, plus reservoir-sampled contexts.
v0.3 (missing-words audit fix). Stages, run from the work dir:
  python 02_lemmatize_sample.py tokens   # spaCy pass -> tokens.tsv.gz (seg, char idx, surface, lemma, UPOS); NUM/PART now kept
  python 02_lemmatize_sample.py resolve  # data/lemma_policy.json + kaikki checks -> lemma_fixes.json
  python 02_lemmatize_sample.py count    # lemma_counts.json + contexts_pool.json using the fixes
Repairs (see AUDIT.md): headword policy (muy, tan, object pronouns, neuter demonstratives, accent variants);
spaced clitic lemmas ('hacer él' -> hacer); lemmas that are not Wiktionary lemmas are re-resolved from the
surface form (quieres -> querer, fué -> ser, demá -> demás); POS repair (siquiera NOUN -> ADV); common words
tagged PROPN when lower-case or sentence-initial (Hola -> hola INTJ, Dios -> dios NOUN); NUM included."""
import json, gzip, random, collections, sys, os, concurrent.futures as cf
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import ssf_lex as L
HERE=os.path.dirname(os.path.abspath(__file__))
POLICY=json.load(open(os.environ.get("SSF_POLICY",os.path.join(HERE,"..","data","lemma_policy.json"))))
KEEP={"NOUN","VERB","ADJ","ADV","PRON","DET","ADP","CCONJ","SCONJ","INTJ","NUM"}
RULES={(s,p):r["key"] for r in POLICY["rules"] for s in r["surface"] for p in r["spacy_pos"]}
MIN_CHECK=20     # keys/surfaces below this count are not looked up (cannot reach the tagging threshold alone)
def base_key(s,lem,pos):
    """policy + spaced-lemma + POS map; returns key or None (not kept)."""
    if (s,pos) in RULES: return RULES[(s,pos)]   # may be None (dropped)
    pos=POLICY["pos_map"].get(pos,pos)
    if pos=="PROPN": return None
    if pos not in KEEP: return None
    lem=lem.lower().split(" ")[0]
    return lem+"|"+pos if lem.isalpha() else None
def initial(text,idx):
    j=idx-1
    while j>=0 and text[j] in " \t\n\"'«“—-¿¡(": j-=1
    return j<0 or text[j] in ".!?…:"
def tokens():
    import spacy
    nlp=spacy.load("es_core_news_md",disable=["parser","ner"])
    segs=[json.loads(l) for l in open("segments.jsonl")]
    with gzip.open("tokens.tsv.gz","wt") as out:
        for doc,i in nlp.pipe(((s["text"],i) for i,s in enumerate(segs)),as_tuples=True,batch_size=200,n_process=3):
            for t in doc:
                if t.is_alpha: out.write(f"{i}\t{t.idx}\t{t.text}\t{t.lemma_}\t{t.pos_}\n")
def table():
    tab=collections.Counter()
    for l in gzip.open("tokens.tsv.gz","rt"):
        _,_,s,lem,pos=l.rstrip("\n").split("\t"); tab[(s.lower(),lem.lower(),pos)]+=1
    return tab
def prefetch(words):
    words=sorted(set(w for w in words if w and w.isalpha()))
    with cf.ThreadPoolExecutor(8) as ex: list(ex.map(L.fetch,words))
EN_STOP=set("the to of and you it is on by all any that for or with this be are was were he she they we his her not but at from as have has had do did what which who will would can could there their an if my me your so no yes oh hey okay ok et miss mr mrs full so".split())
def resolve():
    tab=table(); fixes={}; log=collections.Counter()
    kc=collections.Counter(); surf=collections.defaultdict(collections.Counter); propn=collections.Counter()
    spa=collections.defaultdict(collections.Counter)   # spaCy analyses per surface (for archaic accents: fué -> fue)
    for (s,lem,pos),n in tab.items():
        if pos=="PROPN" and (s,pos) not in RULES: propn[s]+=n; continue
        k=base_key(s,lem,pos)
        if k: kc[k]+=n; surf[k][(s,lem,pos)]+=n; spa[s][k]+=n
    policy=set(v for v in RULES.values() if v); score=lambda k:kc.get(k,0)
    big=[k for k,n in kc.items() if n>=MIN_CHECK and k not in policy]
    prefetch([k.split("|")[0] for k in big]+[s for s,n in propn.items() if n>=MIN_CHECK])
    jobs=[]
    for k in big:
        w,pos=k.split("|")
        if L.is_lemma(w,pos): continue
        jobs+=[(t,n,w,pos) for t,n in surf[k].items() if n>=3 and (t[0],t[2]) not in RULES]
    print("invalid keys",len({(j[2],j[3]) for j in jobs}),"surface jobs",len(jobs),flush=True)
    def one(j):
        (s,lem,p),n,w,pos=j; ua=L.unaccent(s)
        if ua!=s and spa.get(ua):      # archaic/over-accented spelling: reuse spaCy's analysis of the modern spelling
            k2=spa[ua].most_common(1)[0][0]; w2,p2=k2.split("|")
            if p2==pos and L.is_lemma(w2,p2): return (w2,p2)
        return L.resolve(s,w,pos,score)
    with cf.ThreadPoolExecutor(8) as ex: res=list(ex.map(one,jobs))
    for (t,n,w,pos),r in zip(jobs,res):
        if r: fixes["\t".join(t)]=r[0]+"|"+r[1]; log["repaired_tokens"]+=n
        else: log["unresolved_tokens"]+=n
    # common words tagged PROPN: lower-case tokens always; sentence-initial capitalised tokens only if
    # Wiktionary has no capitalised proper-name entry (Hola yes; León, Roma, Argentina no)
    cands=[s for s,n in propn.items() if n>=MIN_CHECK and s not in EN_STOP]
    prefetch([s[:1].upper()+s[1:] for s in cands])
    for s in cands:
        own=[s+"|"+u for u in L.own_pos(s)]
        forms=[x+"|"+L.K2U[kp] for x,kp in L.form_targets(s,set(L.K2U)) if L.is_lemma(x,L.K2U[kp])]
        if not own and not forms: continue
        key=own[0] if own else max(forms,key=score)
        alt=max(own+forms,key=score)   # Escucha -> escuchar|VERB, Cuidado -> cuidado|NOUN; Hola stays hola|INTJ
        if score(alt)>=max(100,10*score(key)): key=alt
        cap=s[:1].upper()+s[1:]
        name=any(e.get("word")==cap and e.get("pos") in ("name","proper noun") for e in L.fetch(cap))
        fixes["PROPN\t"+s]={"key":key,"initial_ok":not name}; log["propn_types"]+=1; log["propn_initial_ok"]+=not name
    json.dump(fixes,open("lemma_fixes.json","w"),ensure_ascii=False,indent=0); print(dict(log),len(fixes))
def count():
    random.seed(7); R=40
    fixes=json.load(open("lemma_fixes.json"))
    segs=[json.loads(l) for l in open("segments.jsonl")]
    cnt=collections.Counter(); gcnt=collections.Counter(); seen=collections.Counter(); pool={}; srcmap=collections.defaultdict(collections.Counter)
    for l in gzip.open("tokens.tsv.gz","rt"):
        i,idx,t,lem,pos=l.rstrip("\n").split("\t"); i=int(i); idx=int(idx); s=t.lower(); seg=segs[i]; g=seg["genre"]
        gcnt[g]+=1
        if (s,pos) in RULES:
            k=RULES[(s,pos)]
            if not k: continue
        elif pos=="PROPN":
            f=fixes.get("PROPN\t"+s)
            if not f or not (t==s or (f["initial_ok"] and initial(seg["text"],idx))): continue
            k=f["key"]
        else:
            k=fixes.get("\t".join((s,lem.lower(),pos))) or base_key(s,lem.lower(),pos)
            if not k: continue
        cnt[k]+=1; seen[k]+=1; n=seen[k]; srcmap[k][s]+=1
        if n<=R or random.random()<R/n:
            txt=seg["text"]; a=max(0,idx-160); b=min(len(txt),idx+len(t)+160)
            item={"g":g,"src":seg["src"],"s":txt[a:idx]+"[["+t+"]]"+txt[idx+len(t):b]}
            if n<=R: pool.setdefault(k,[]).append(item)
            else: pool[k][random.randrange(R)]=item
    total=sum(gcnt.values())
    json.dump({"total_tokens":total,"genre_tokens":gcnt,"counts":cnt.most_common()},open("lemma_counts.json","w"),ensure_ascii=False)
    top=[k for k,_ in cnt.most_common(8000)]
    json.dump({k:pool[k] for k in top},open("contexts_pool.json","w"),ensure_ascii=False)
    json.dump({k:srcmap[k].most_common(8) for k in top},open("surface_forms.json","w"),ensure_ascii=False)
    inv=collections.defaultdict(collections.Counter)
    for k,c in srcmap.items():
        for sf,n in c.items(): inv[sf][k]+=n
    json.dump({sf:c.most_common(1)[0][0] for sf,c in inv.items() if sum(c.values())>=3},open("surface_lemma.json","w"),ensure_ascii=False)   # used by 09_audit
    print(total,cnt.most_common(30))
if __name__=="__main__":
    {"tokens":tokens,"resolve":resolve,"count":count}[sys.argv[1]]()
