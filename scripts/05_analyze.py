"""Parse batch outputs -> per-sense shares, Wilson 95% CI, est. per-million freq, global ranks,
rank bands, and the 'safe cutoff' (ranks provably complete given unsampled lemmas)."""
import json, math, csv, collections, re
Z=1.96
def wilson(k,n):
    if n==0: return (0.0,1.0)
    p=k/n; d=1+Z*Z/n; c=(p+Z*Z/(2*n))/d; h=Z*math.sqrt(p*(1-p)/n+Z*Z/(4*n*n))/d
    return (max(0.0,c-h),min(1.0,c+h))
lc=json.load(open("lemma_counts.json")); total=lc["total_tokens"]
fpm={k:c*1e6/total for k,c in lc["counts"]}
keys=json.load(open("top_lemmas.json")); inv=json.load(open("inventories.json")); samples=json.load(open("samples.json"))
pool=json.load(open("contexts_pool.json"))
labels=collections.defaultdict(dict)
for line in open("outputs.jsonl"):
    o=json.loads(line); key,b=o["custom_id"].split("#")
    try:
        content=o["response"]["body"]["choices"][0]["message"]["content"]
        for i,s in json.loads(content)["l"]: labels[key][int(i)-1]=int(s)
    except Exception: pass
def short(s,n=60):
    i=s.find("[["); j=s.find("]]")+2; a=s[max(0,i-n):i]; b=s[j:j+n]
    return ("…" if i>n else "")+a+s[i:j]+b+("…" if len(s)>j+n else "")
rows=[]; tagged=set(); untagged=[]
for key in keys:
    w,pos=key.split("|"); senses=inv.get(key) or []
    if len(senses)==1:   # single sense: share = 1 by construction (not LLM-verified)
        tagged.add(key)
        rows.append(dict(lemma=w,pos=pos,sense_id=f"{w}|{pos}|1",gloss=senses[0]["gloss"],mexico=senses[0]["mexico"],n=0,k=0,share=1.0,
             lo=1.0,hi=1.0,lemma_fpm=fpm[key],method="single-sense",ex=[short(x["s"]) for x in pool.get(key,[])[:2]]))
        continue
    if key not in labels or len(labels[key])<0.8*len(samples.get(key,[])) or not samples.get(key): untagged.append(key); continue
    tagged.add(key); L=labels[key]; kk=len(senses)
    valid={i:s for i,s in L.items() if s!=0}; n=len(valid); notw=len(L)-n
    cnt=collections.Counter(valid.values())
    adj=fpm[key]*(n/len(L)) if L else 0
    for sid in sorted(cnt):
        if sid<1 or sid>kk+1: continue
        k=cnt[sid]; lo,hi=wilson(k,n)
        gl=senses[sid-1]["gloss"] if sid<=kk else "(other sense / idiom / fixed expression)"
        mx=senses[sid-1]["mexico"] if sid<=kk else False
        ex=[short(samples[key][i]["s"]) for i,s in sorted(valid.items()) if s==sid][:2]
        rows.append(dict(lemma=w,pos=pos,sense_id=f"{w}|{pos}|{sid if sid<=kk else 'other'}",gloss=gl,mexico=mx,n=n,k=k,share=k/n,lo=lo,hi=hi,
                         lemma_fpm=adj,method="llm",not_this_word=notw,ex=ex))
for r in rows:
    r["fpm"]=r["lemma_fpm"]*r["share"]; r["fpm_lo"]=r["lemma_fpm"]*r["lo"]; r["fpm_hi"]=r["lemma_fpm"]*r["hi"]
rows.sort(key=lambda r:-r["fpm"])
# safe cutoff: highest frequency of any lemma|POS NOT tagged (beyond top list, or skipped/unfinished)
import re as _re
cands=json.load(open("candidates_3400.json")); cset=set(cands)
pool_un=[fpm[k] for k in cands if inv.get(k) and k not in tagged]
outside=[fpm[k] for k,_ in lc["counts"] if k not in cset and _re.fullmatch(r"[a-záéíóúüñ]+",k.split("|")[0])][:1]
F_un=max(pool_un+outside+[0])
his=sorted(r["fpm_hi"] for r in rows); los=sorted(r["fpm_lo"] for r in rows)
import bisect
for i,r in enumerate(rows):
    r["rank"]=i+1
    r["rank_safe"]=r["fpm_lo"]>F_un
    r["rank_min"]=1+(len(los)-bisect.bisect_right(los,r["fpm_hi"]))   # senses certainly above
    r["rank_max"]=len(his)-bisect.bisect_left(his,r["fpm_lo"])          # senses possibly above (incl. self)
point_safe=sum(1 for r in rows if r["fpm"]>F_un)
first_unsafe=next((r["rank"] for r in rows if not r["rank_safe"]),len(rows)+1)
widths=[r["rank_max"]-r["rank_min"] for r in rows]
summary=dict(total_tokens=total,lemmas_requested=len(keys),lemmas_tagged=len(tagged),lemmas_untagged=len(untagged),senses=len(rows),
  highest_unsampled_fpm=F_un,safe_cutoff_point=point_safe,safe_cutoff_lower_ci=first_unsafe-1,
  median_rank_band_top100=sorted(widths[:100])[len(widths[:100])//2] if rows else None,
  median_rank_band_all=sorted(widths)[len(widths)//2] if rows else None)
json.dump(summary,open("summary.json","w"),indent=1); print(summary)
cols=["rank","lemma","pos","sense_id","gloss","share","ci_low","ci_high","n_contexts","est_per_million","est_per_million_low","est_per_million_high",
      "lemma_per_million","rank_min","rank_max","rank_safe","mexico","method","example_1","example_2"]
out=[]
for r in rows:
    out.append({"rank":r["rank"],"lemma":r["lemma"],"pos":r["pos"],"sense_id":r["sense_id"],"gloss":r["gloss"],"share":round(r["share"],3),
      "ci_low":round(r["lo"],3),"ci_high":round(r["hi"],3),"n_contexts":r["n"],"est_per_million":round(r["fpm"],2),
      "est_per_million_low":round(r["fpm_lo"],2),"est_per_million_high":round(r["fpm_hi"],2),"lemma_per_million":round(r["lemma_fpm"],2),
      "rank_min":r["rank_min"],"rank_max":r["rank_max"],"rank_safe":r["rank_safe"],"mexico":r["mexico"],"method":r["method"],
      "example_1":(r["ex"]+["",""])[0],"example_2":(r["ex"]+["",""])[1]})
with open("spanish_sense_frequency.csv","w",newline="") as f:
    wr=csv.DictWriter(f,fieldnames=cols); wr.writeheader(); wr.writerows(out)
json.dump({"summary":summary,"senses":out},open("spanish_sense_frequency.json","w"),ensure_ascii=False,indent=1)
