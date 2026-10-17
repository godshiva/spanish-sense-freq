"""v0.3 incremental re-run after the lemmatisation fix (02 resolve/count). Re-tags ONLY new keys and keys whose
corrected count changed by more than CHANGE (default 25%); every other key keeps its v0.2 inventory, samples and
LLM labels, so sense ids stay stable. Run in the new work dir (with the new lemma_counts.json/contexts_pool.json):
  python 10_incremental.py select OLD_WORK_DIR   # -> top_lemmas.json, inventories.json, samples.json, outputs.jsonl (kept), tag/requests.jsonl
  (cd tag && python ../04_tag_batch.py run CHUNK CAP)  then  python 10_incremental.py collect
  python 05_analyze.py
  python 10_incremental.py carry OLD_CSV          # carry MX/register/manual values by sense_id; writes inc/ with rows needing labels
  (06/08 in inc/)  then  python 10_incremental.py fold"""
import json, sys, os, random, csv, collections, importlib.util
D=os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0,D)
def load(n,f):
    s=importlib.util.spec_from_file_location(n,os.path.join(D,f)); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
MIN_COUNT=144          # v0.2 tagging threshold (count of the last tagged key, detective|NOUN)
CHANGE=0.25
SPAIN_ONLY={"os|PRON","vosotros|PRON"}
# v0.2 keys whose Wiktionary inventory changes under the v0.3 03 rules (Latin-America-tagged senses no longer dropped,
# female-equivalent senses kept); rebuilt and re-tagged. Excluded: carga, cura, rata, carretera (only gain a
# 'female equivalent of <unrelated word>' sense).
REBUILD={"usted|PRON","tomar|VERB","dónde|PRON","agua|NOUN","chica|NOUN","música|NOUN","política|NOUN","acá|ADV","video|NOUN",
 "alcalde|NOUN","manejar|VERB","arrojar|VERB","pájaro|NOUN","fútbol|NOUN","pata|NOUN","nena|NOUN","crítica|NOUN","presidenta|NOUN",
 "directora|NOUN","prima|NOUN"}   # kept as separate keys so they do not inflate tú, but not added to the list
def select(old):
    b3=load("b3","03_build_inventories.py"); b4=load("b4","04_tag_batch.py")
    lc=json.load(open("lemma_counts.json")); cnt=dict(lc["counts"]); order=[k for k,_ in lc["counts"]]
    oc=dict(json.load(open(os.path.join(old,"lemma_counts.json")))["counts"])
    oinv=json.load(open(os.path.join(old,"inventories.json"))); otop=json.load(open(os.path.join(old,"top_lemmas.json")))
    osamp=json.load(open(os.path.join(old,"samples.json"))); pool=json.load(open("contexts_pool.json"))
    cands=order[:3400]; json.dump(cands,open("candidates_3400.json","w"),ensure_ascii=False)
    oinv={k:v for k,v in oinv.items() if v or k in otop}   # empty v0.2 inventories (fetch failures etc.) are rebuilt
    newkeys=[k for k in order if cnt[k]>=MIN_COUNT and k not in oinv and k not in SPAIN_ONLY]
    words=sorted({k.split("|")[0] for k in newkeys+list(REBUILD)+[k for k in cands if k not in oinv]})
    import concurrent.futures as cf
    def f2(w): return b3.fetch(w) or [dict(e,word=w) for e in b3.fetch(w.upper()) if e.get("word")==w.upper()]
    with cf.ThreadPoolExecutor(8) as ex: data=dict(zip(words,ex.map(f2,words)))
    inv={}
    for k in cands:     # inventories for every candidate (05 uses them for the safe cutoff)
        inv[k]=oinv[k] if k in oinv and k not in REBUILD else b3.build(k,data[k.split("|")[0]])
    for k in otop: inv.setdefault(k,oinv[k])
    for k in SPAIN_ONLY: inv[k]=[]   # excluded on purpose: must not count as 'unsampled' in the safe cutoff
    top=[k for k in order if cnt[k]>=MIN_COUNT and inv.get(k) and k not in SPAIN_ONLY]
    changed=[k for k in top if k in oc and k in otop and abs(cnt[k]-oc[k])/oc[k]>CHANGE]
    new=[k for k in top if k not in otop]
    retag=[k for k in changed+new+[k for k in top if k in REBUILD and k not in changed] if len(inv[k])>=2]
    dropped=[k for k in otop if k not in top]
    random.seed(11); samples={}; reqs=[]
    fixed=json.load(open("samples_fixed.json")) if os.path.exists("samples_fixed.json") else {}
    for k in top:
        if len(inv[k])<2: continue
        if k not in retag: samples[k]=osamp[k]; continue
        ctx=pool[k][:]; random.shuffle(ctx); ctx=ctx[:25]
        if k in fixed: samples[k]=fixed[k]; continue   # already submitted in an earlier batch: keep its contexts, no new request
        samples[k]=ctx
        w,pos=k.split("|"); senses=inv[k]; n=len(senses)
        slist="\n".join(f"{i+1}. {s['gloss']}" for i,s in enumerate(senses))+f"\n{n+1}. other sense / idiom / fixed expression not listed\n0. not this word (target is a different lemma/POS, a name, or a tagging error)"
        for b in range(0,len(ctx),10):
            c="\n".join(f"{b+j+1}) {b4.trim(x['s'])}" for j,x in enumerate(ctx[b:b+10]))
            prompt=(f"Spanish word-sense tagging. Lemma: {w} ({pos}). Senses:\n{slist}\n\nFor each context choose the sense number of the [[target]].\n{c}\n\n"
                    'JSON only: {"l":[[context_number,sense_number],...]}')
            reqs.append({"custom_id":f"{k}#{b}","method":"POST","url":"/v1/chat/completions",
              "body":{"model":b4.MODEL,"reasoning_effort":"low","response_format":{"type":"json_object"},"max_completion_tokens":2000,"messages":[{"role":"user","content":prompt}]}})
    keep=set(samples)-set(retag)
    with open("outputs.jsonl","w") as fo:
        for line in open(os.path.join(old,"outputs.jsonl")):
            if json.loads(line)["custom_id"].split("#")[0] in keep: fo.write(line)
    tdir=os.environ.get("TAG_DIR","tag"); os.makedirs(tdir,exist_ok=True)
    with open(tdir+"/requests.jsonl","w") as f:
        for r in reqs: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    json.dump(top,open("top_lemmas.json","w"),ensure_ascii=False); json.dump(inv,open("inventories.json","w"),ensure_ascii=False,indent=0)
    json.dump(samples,open("samples.json","w"),ensure_ascii=False)
    chars=sum(len(r["body"]["messages"][0]["content"]) for r in reqs)
    info=dict(top=len(top),new_keys=new,changed_keys=changed,retag=len(retag),dropped=dropped,requests=len(reqs),est_input_tokens=int(chars/3.5),
              excluded_spain_only=sorted(SPAIN_ONLY),new_without_senses=[k for k in newkeys if not inv.get(k)])
    json.dump(info,open("select_info.json","w"),ensure_ascii=False,indent=1)
    print({k:(v if not isinstance(v,list) else len(v)) for k,v in info.items()})
def collect():
    n=0
    with open("outputs.jsonl","a") as fo:
        for d in sys.argv[2:] or ["tag"]:
            for line in open(d+"/outputs.jsonl"): fo.write(line); n+=1
    print("appended",n)
CARRY=["mx_status","non_mexican","mx_equivalent","mx_note","register","register_note","register_source"]
def carry(old_csv):
    R=list(csv.DictReader(open("spanish_sense_frequency.csv"))); O={r["sense_id"]:r for r in csv.DictReader(open(old_csv))}
    todo=[]
    for r in R:
        o=O.get(r["sense_id"])
        if o and o["gloss"]==r["gloss"]:
            for c in CARRY: r[c]=o[c]
        else:
            for c in CARRY: r[c]=""
            todo.append(r)
    cols=list(R[0].keys()); cols=[c for c in cols if c not in("example_1","example_2")]+["example_1","example_2"]
    with open("spanish_sense_frequency.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(R)
    os.makedirs("inc/mx",exist_ok=True); os.makedirs("inc/reg",exist_ok=True)
    base=[c for c in cols if c not in CARRY]
    with open("inc/spanish_sense_frequency.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=base+["mexico"],extrasaction="ignore"); w.writeheader()
        for r in todo: w.writerow(dict(r,mexico=""))
    json.dump(sorted({r["lemma"]+"|"+r["pos"] for r in todo}),open("inc/top_lemmas.json","w"),ensure_ascii=False)
    for f in ("inventories.json","samples.json","outputs.jsonl"):
        if not os.path.exists("inc/"+f): os.symlink(os.path.abspath(f),"inc/"+f)
    json.dump({"summary":{},"senses":[]},open("inc/spanish_sense_frequency.json","w"))
    print("rows",len(R),"carried",len(R)-len(todo),"need labels",len(todo))
def fold():
    R=list(csv.DictReader(open("spanish_sense_frequency.csv"))); N={r["sense_id"]:r for r in csv.DictReader(open("inc/spanish_sense_frequency.csv"))}
    for r in R:
        if r["sense_id"] in N:
            for c in CARRY: r[c]=N[r["sense_id"]].get(c,"")
    with open("spanish_sense_frequency.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(R[0].keys())); w.writeheader(); w.writerows(R)
    print("folded",len(N),"missing labels",sum(1 for r in R if not r["mx_status"] or not r["register"]))
if __name__=="__main__":
    a=sys.argv[1]
    if a=="select": select(sys.argv[2])
    elif a=="collect": collect()
    elif a=="carry": carry(sys.argv[2])
    elif a=="fold": fold()

def manual(path, log_path):
    """Apply {sense_id: {field: value, "_why": reason}} overrides and log them to manual_corrections.csv."""
    R=list(csv.DictReader(open("spanish_sense_frequency.csv"))); ov=json.load(open(path))["overrides"]; log=[]
    for r in R:
        o=ov.get(r["sense_id"])
        if not o: continue
        for f,v in o.items():
            if f.startswith("_"): continue
            if str(r[f])!=str(v): log.append({"sense_id":r["sense_id"],"field":f,"old":r[f],"new":v,"reason":o["_why"]}); r[f]=v
        if "register" in o: r["register_source"]="manual"
    with open("spanish_sense_frequency.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(R[0].keys())); w.writeheader(); w.writerows(R)
    with open(log_path,"a",newline="") as f: csv.DictWriter(f,fieldnames=["sense_id","field","old","new","reason"]).writerows(log)
    print("manual changes",len(log),"rows",len({l["sense_id"] for l in log}),"missing ids",[k for k in ov if k not in {r["sense_id"] for r in R}])
if __name__=="__main__" and sys.argv[1]=="manual": manual(sys.argv[2],sys.argv[3])
