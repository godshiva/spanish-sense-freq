"""Non-Mexican flagging. Steps: (1) Wiktionary regional labels per lemma (senses tagged only for Spain/other
non-Mexican regions were excluded from the inventory; they are collected here as hints, esp. for 'other' rows);
(2) gpt-5.6-luna (Batch API, reasoning low) classifies every sense row as common/uncommon/not_used in Mexico;
(3) corpus signal: sense hits in .mx news vs other news contexts.
Usage: 06_mexico_flags.py hints | build | run CAP_USD | merge"""
import json, sys, os, csv, collections, importlib.util, re, concurrent.futures as cf
W=os.getcwd()
spec=importlib.util.spec_from_file_location("b3",os.path.join(os.path.dirname(__file__),"03_build_inventories.py")); b3=importlib.util.module_from_spec(spec); spec.loader.exec_module(b3)
spec4=importlib.util.spec_from_file_location("b4",os.path.join(os.path.dirname(__file__),"04_tag_batch.py")); b4=importlib.util.module_from_spec(spec4); spec4.loader.exec_module(b4)
MXOK={"Mexico","Latin-America","Americas","Central-America","US"}
def hints():
    keys=json.load(open("top_lemmas.json")); words=sorted({k.split("|")[0] for k in keys})
    with cf.ThreadPoolExecutor(12) as ex: data=dict(zip(words,ex.map(b3.fetch,words)))
    out={}
    for k in keys:
        w,pos=k.split("|"); hs=[]
        for e in data[w]:
            if e.get("word")!=w or e.get("pos") not in b3.POSMAP[pos]: continue
            for s in e.get("senses",[]):
                tags=set(s.get("tags",[])); regs={t for t in tags if t in b3.REGIONS}
                if regs and not (tags&MXOK):
                    hs.append(((s.get("glosses") or [""])[-1][:90],sorted(regs)))
        out[k]=hs
    json.dump(out,open("mx/wikt_region_hints.json","w"),ensure_ascii=False,indent=0)
    print("lemmas with non-MX regional senses:",sum(1 for v in out.values() if v))
def rows(): return list(csv.DictReader(open("spanish_sense_frequency.csv")))
def build():
    R=rows(); H=json.load(open("mx/wikt_region_hints.json")); reqs=[]
    for b in range(0,len(R),25):
        part=R[b:b+25]; lines=[]
        for j,r in enumerate(part):
            key=r["lemma"]+"|"+r["pos"]; h=H.get(key,[])
            hint=("; Wiktionary region-only senses of this lemma: "+" | ".join(f"{g} [{','.join(t)}]" for g,t in h[:4])) if h else ""
            gl=r["gloss"] if not r["sense_id"].endswith("|other") else "(other uses/idioms of this lemma, see example)"
            ex=(r["example_1"] or "")[:140]
            lines.append(f"{b+j}) {r['lemma']} ({r['pos']}): {gl} | e.g. {ex}{hint}")
        prompt=("You are an expert in Mexican Spanish. For each Spanish word sense below, judge how it is used by an ordinary educated speaker in Mexico today.\n"
                "status: \"common\" = normal in Mexico; \"uncommon\" = understood but rare, bookish/archaic, or marked as foreign (e.g. Spain-only like 'ordenador','zumo','vosotros'); "
                "\"not_used\" = not used, or misleading/vulgar in Mexico (e.g. coger 'to take').\n"
                "For 'other uses' rows judge the example's usage. Give the usual Mexican equivalent when status is not common (else empty), and a note of <=12 words.\n\n"
                +"\n".join(lines)+'\n\nJSON only: {"r":[[row_number,"common|uncommon|not_used","mexican equivalent","note"],...]}')
        reqs.append({"custom_id":f"mx#{b}","method":"POST","url":"/v1/chat/completions",
            "body":{"model":b4.MODEL,"reasoning_effort":"low","response_format":{"type":"json_object"},"max_completion_tokens":6000,
                    "messages":[{"role":"user","content":prompt}]}})
    with open("mx/requests.jsonl","w") as f:
        for r in reqs: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    print("requests",len(reqs),"chars",sum(len(r["body"]["messages"][0]["content"]) for r in reqs))
def merge():
    R=rows(); res={}
    for line in open("mx/outputs.jsonl"):
        o=json.loads(line)
        try:
            for i,s,e,n in json.loads(o["response"]["body"]["choices"][0]["message"]["content"])["r"]: res[int(i)]=(s,e,n)
        except Exception as ex: print("parse fail",o["custom_id"],ex)
    # corpus signal from tagged contexts
    S=json.load(open("samples.json")); lab=collections.defaultdict(dict)
    for line in open("outputs.jsonl"):
        o=json.loads(line); key=o["custom_id"].split("#")[0]
        try:
            for i,s in json.loads(o["response"]["body"]["choices"][0]["message"]["content"])["l"]: lab[key][int(i)-1]=int(s)
        except Exception: pass
    sig={}
    for key,L in lab.items():
        mxn=[s for i,s in L.items() if S[key][i]["g"]=="news" and S[key][i]["src"].startswith("MX ")]
        oth=[s for i,s in L.items() if not (S[key][i]["g"]=="news" and S[key][i]["src"].startswith("MX "))]
        sig[key]=(collections.Counter(mxn),len(mxn),collections.Counter(oth),len(oth))
    out=[]; missing=0
    for idx,r in enumerate(R):
        s,e,n=res.get(idx,("","",""))
        if not s: missing+=1
        r.pop("mexico",None)
        r["mx_status"]=s if s in ("common","uncommon","not_used") else ""
        r["non_mexican"]=r["mx_status"] in ("uncommon","not_used")
        r["mx_equivalent"]=(e or "")[:60] if r["non_mexican"] else ""
        r["mx_note"]=(n or "")[:120]
        key=r["lemma"]+"|"+r["pos"]; sid=r["sense_id"].split("|")[-1]
        if key in sig and r["method"]=="llm":
            inv=json.load(open("inventories.json")) if idx==0 else None
        out.append(r)
    # corpus signal summary: senses never seen in MX news though lemma had >=4 MX-news contexts and >=3 hits elsewhere
    inv=json.load(open("inventories.json")); flagged=[]
    for r in out:
        key=r["lemma"]+"|"+r["pos"]
        if r["method"]!="llm" or key not in sig: continue
        k=len(inv[key]); sid=r["sense_id"].split("|")[-1]; sn=k+1 if sid=="other" else int(sid)
        cm,nm,co,no=sig[key]
        if nm>=4 and co[sn]>=3 and cm[sn]==0: flagged.append((r["rank"],r["sense_id"],r["gloss"][:50],r["mx_status"],nm,co[sn]))
    json.dump({"note":"senses with 0 hits among >=4 .mx-news contexts but >=3 hits in other contexts (weak signal, n small)","items":flagged},open("mx/corpus_signal.json","w"),ensure_ascii=False,indent=1)
    cols=[c for c in out[0].keys() if c not in("example_1","example_2")]+["example_1","example_2"]
    with open("spanish_sense_frequency.csv","w",newline="") as f:
        w=csv.DictWriter(f,fieldnames=cols); w.writeheader(); w.writerows(out)
    J=json.load(open("spanish_sense_frequency.json")); J["senses"]=out; json.dump(J,open("spanish_sense_frequency.json","w"),ensure_ascii=False,indent=1)
    print("missing",missing,collections.Counter(r["mx_status"] for r in out),"corpus-signal senses",len(flagged))
if __name__=="__main__":
    a=sys.argv[1]
    if a=="hints": hints()
    elif a=="build": build()
    elif a=="merge": merge()
    elif a=="run":
        os.chdir("mx"); b4.run(int(sys.argv[3]) if len(sys.argv)>3 else 300,float(sys.argv[2]))
