"""Stream a sample of Spanish text: ~50% subtitles, ~25% news, ~25% fiction (by word count).
Writes segments.jsonl: {"genre","src","text"}. Nothing downloaded in bulk."""
import json, random, subprocess, hashlib, re, itertools, sys
from datasets import load_dataset
random.seed(42)
TARGET={"sub":3_000_000,"news":1_500_000,"fic":1_500_000}
out=open("segments.jsonl","w"); seen=set(); words={"sub":0,"news":0,"fic":0}
def emit(g,src,text):
    h=hashlib.md5(text.encode()).hexdigest()
    if h in seen: return
    seen.add(h); words[g]+=len(text.split())
    out.write(json.dumps({"genre":g,"src":src,"text":text},ensure_ascii=False)+"\n")
# --- subtitles: OPUS OpenSubtitles v2024 mono es, sparse 4-line blocks across the whole file
URL="https://object.pouta.csc.fi/OPUS-OpenSubtitles/v2024/mono/es.txt.gz"
p=subprocess.Popen(f"curl -s {URL} | gunzip",shell=True,stdout=subprocess.PIPE,text=True,errors="replace")
EVERY=600; buf=[]
for i,line in enumerate(p.stdout):
    if i%EVERY<4:
        buf.append(line.strip())
        if i%EVERY==3:
            t=" ".join(x for x in buf if x); buf=[]
            if len(t)>30: emit("sub","OpenSubtitles v2024 (OPUS)",t)
    if words["sub"]>=TARGET["sub"]: break
p.kill(); print("sub done lines",i,words,flush=True)
# --- news: stanford-oval/ccnews, Spanish; all .mx kept, others at 40%
for cfg in ["2023","2022","2021"]:
    for r in load_dataset("stanford-oval/ccnews",cfg,split="train",streaming=True):
        if r["language"]!="es": continue
        u=r["responded_url"] or ""; host=u.split("/")[2] if u.count("/")>=2 else ""
        mx=host.endswith(".mx")
        if not mx and random.random()>0.4: continue
        t=r["plain_text"][:2500]
        emit("news",("MX " if mx else "")+host,t)
        if words["news"]>=TARGET["news"]: break
    if words["news"]>=TARGET["news"]: break
print("news done",words,flush=True)
# --- fiction: Project Gutenberg Spanish; random passages from the body of each book
SW=re.compile(r"\b(que|de|la|el|en|y|los|se|del|las|un|por|con|no|una|su|para|es|al)\b")
books=list(itertools.islice(load_dataset("manu/project_gutenberg",split="es",streaming=True),100000))
random.shuffle(books)
for b in books:
    t=b["text"]; n=len(t)
    if n<20000: continue
    body=t[int(n*0.08):int(n*0.92)]
    sample=body[:20000]
    if len(SW.findall(sample))/max(1,len(sample.split()))<0.25: continue  # not Spanish prose
    for k in range(8):
        o=random.randint(0,len(body)-3000); seg=body[o:o+3000]
        seg=seg[seg.find(" ")+1:seg.rfind(" ")]
        emit("fic","Gutenberg "+b["id"],re.sub(r"\s+"," ",seg).replace("_",""))
    if words["fic"]>=TARGET["fic"]: break
print("fic done",words,"books",len(books),flush=True)
