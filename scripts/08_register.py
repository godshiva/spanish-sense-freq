"""Register/usage columns. Seed from Wiktionary sense tags (kaikki), LLM (gpt-5.6-luna, Batch, reasoning low)
for rows without a usable tag. Usage (run in a work dir containing spanish_sense_frequency.csv + inventories.json):
  08_register.py seed | build | run CAP_USD [CHUNK [retry]] | retry | merge"""
import json, sys, os, csv, collections, importlib.util, concurrent.futures as cf
D=os.path.dirname(os.path.abspath(__file__))
def load(n,f):
    s=importlib.util.spec_from_file_location(n,os.path.join(D,f)); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); return m
b3=load("b3","03_build_inventories.py"); b4=load("b4","04_tag_batch.py")
MAP=[("offensive-slur",{"offensive","ethnic","slur","derogatory","pejorative"}),("vulgar",{"vulgar"}),
     ("archaic",{"archaic","obsolete","dated","historical"}),("literary",{"literary","poetic"}),
     ("informal-slang",{"colloquial","slang","informal"}),("formal",{"formal"})]
CATS=["neutral","informal-slang","vulgar","offensive-slur","literary","archaic","formal","technical"]
def rows(): return list(csv.DictReader(open("spanish_sense_frequency.csv")))
def seed():
    R=rows(); inv=json.load(open("inventories.json"))
    words=sorted({r["lemma"] for r in R})
    with cf.ThreadPoolExecutor(12) as ex: data=dict(zip(words,ex.map(b3.fetch,words)))
    out={}
    for r in R:
        sid=r["sense_id"].split("|")[-1]
        if sid=="other": continue
        key=r["lemma"]+"|"+r["pos"]; gl=inv[key][int(sid)-1]["gloss"]
        tags=set()
        for e in data[r["lemma"]]:
            for s in e.get("senses",[]):
                g=(s.get("glosses") or [""])[-1].strip()[:160]
                if g==gl: tags|=set(s.get("tags",[]))
        for cat,ts in MAP:
            hit=tags&ts
            if hit: out[r["sense_id"]]=(cat,"Wiktionary tag: "+", ".join(sorted(hit))); break
    json.dump(out,open("reg/seed.json","w"),ensure_ascii=False,indent=0)
    print("seeded",len(out),collections.Counter(v[0] for v in out.values()))
def parsed():
    res={}
    for fn in ("reg/outputs.jsonl","reg/retry/outputs.jsonl"):
        if not os.path.exists(fn): continue
        for line in open(fn):
            o=json.loads(line)
            try:
                for i,g,n in json.loads(o["response"]["body"]["choices"][0]["message"]["content"])["r"]: res[int(i)]=(g,n)
            except Exception as ex: print("parse fail",fn,o["custom_id"],ex)
    return res
def build(retry=False):
    """Numbered senses are judged from lemma+POS+gloss ONLY (v2; v1 showed the example's genre leaked into the label).
    'other' rows are judged from their example."""
    R=rows(); S=json.load(open("reg/seed.json")); done=parsed() if retry else {}
    todo=[(i,r) for i,r in enumerate(R) if r["sense_id"] not in S and i not in done]; reqs=[]
    for b in range(0,len(todo),25):
        part=todo[b:b+25]; lines=[]
        for i,r in part:
            if r["sense_id"].endswith("|other"):
                lines.append(f"{i}) {r['lemma']} ({r['pos']}) OTHER-USE, judge this usage: {(r['example_1'] or '')[:130]}")
            else:
                lines.append(f"{i}) {r['lemma']} ({r['pos']}): {r['gloss'][:150]}")
        prompt=("Classify the inherent REGISTER of each Spanish word SENSE in modern Mexican/Latin American Spanish, to decide whether learners can be taught it as ordinary vocabulary.\n"
            "register: neutral | informal-slang | vulgar | offensive-slur | literary | archaic | formal | technical\n"
            "Judge the SENSE itself (lemma+gloss), not any text it might appear in. Most senses are neutral: everyday words, family words (mamá), tú/usted, ordinary verbs, "
            "and words usable in both speech and writing are neutral. Use: informal-slang = colloquial/slang meanings; vulgar = obscene/sexual/scatological; "
            "offensive-slur = insults or derogatory terms for people/groups; literary = mainly poetic/bookish; archaic = old-fashioned, historical or obsolete; "
            "formal = mainly official/legal/bureaucratic writing; technical = specialist jargon (law, medicine, nautical, sports rules, computing...).\n"
            "For OTHER-USE rows judge the target word's usage in the snippet. Note <=10 words, only if not neutral.\n"
            "Return EVERY row number, including neutral ones.\n\n"+"\n".join(lines)+
            '\n\nJSON only: {"r":[[row_number,"register","note"],...]}')
        reqs.append({"custom_id":f"reg#{b}","method":"POST","url":"/v1/chat/completions",
            "body":{"model":b4.MODEL,"reasoning_effort":"low","response_format":{"type":"json_object"},"max_completion_tokens":6000,"messages":[{"role":"user","content":prompt}]}})
    out="reg/retry/requests.jsonl" if retry else "reg/requests.jsonl"; os.makedirs(os.path.dirname(out),exist_ok=True)
    with open(out,"w") as f:
        for q in reqs: f.write(json.dumps(q,ensure_ascii=False)+"\n")
    print("rows to classify",len(todo),"requests",len(reqs))
def merge():
    R=rows(); S=json.load(open("reg/seed.json")); res=parsed(); miss=0
    for i,r in enumerate(R):
        if r["sense_id"] in S: g,n=S[r["sense_id"]]; src="wiktionary"
        elif i in res: g,n=res[i]; src="llm"
        else: g,n,src="","","missing"; miss+=1
        r["register"]=g if g in CATS else ("neutral" if src=="llm" else g)
        r["register_note"]=(n or "")[:100] if r["register"]!="neutral" else ""
        r["register_source"]=src
    cols=[c for c in R[0].keys() if c not in("example_1","example_2")]+["example_1","example_2"]
    with open("spanish_sense_frequency.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(R)
    print("missing",miss,collections.Counter(r["register"] for r in R))
if __name__=="__main__":
    a=sys.argv[1]; os.makedirs("reg",exist_ok=True)
    if a=="seed": seed()
    elif a=="build": build()
    elif a=="retry": build(True)
    elif a=="merge": merge()
    elif a=="run": os.chdir("reg/retry" if len(sys.argv)>4 else "reg"); b4.run(int(sys.argv[3]) if len(sys.argv)>3 else 125,float(sys.argv[2]))

def manual(path, log_path):
    """Apply hand-review overrides {sense_id: [register, note]} and append them to manual_corrections.csv."""
    R=rows(); ov=json.load(open(path)); log=[]
    for r in R:
        if r["sense_id"] in ov:
            g,n=ov[r["sense_id"]]
            for f,new in (("register",g),("register_note",n if g!="neutral" else "")):
                if r[f]!=new: log.append({"sense_id":r["sense_id"],"field":f,"old":r[f],"new":new,"reason":"manual register review (top 2,000 / missing)"}); r[f]=new
            r["register_source"]="manual"
    with open("spanish_sense_frequency.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=list(R[0].keys())); w.writeheader(); w.writerows(R)
    with open(log_path,"a",newline="") as f: csv.DictWriter(f,fieldnames=["sense_id","field","old","new","reason"]).writerows(log)
    print("register overrides",len(log),collections.Counter(r["register"] for r in R))
if __name__=="__main__" and sys.argv[1]=="manual": manual(sys.argv[2],sys.argv[3])
