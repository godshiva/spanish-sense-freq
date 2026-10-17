"""Build OpenAI Batch API requests (gpt-5.6-luna, reasoning low, 10 contexts/request) and run them in
frequency-ordered chunks under a HARD cost cap. Usage: python 04_tag_batch.py build | run CHUNK_SIZE CAP_USD"""
import json, os, random, sys, time, urllib.request
MODEL="gpt-5.6-luna"; PIN,PCACHE,POUT=0.10,0.01,0.60   # Batch prices $/1M, platform.openai.com/docs/pricing (2026-10-16)
API="https://api.openai.com/v1"; H={"Authorization":"Bearer "+os.environ.get("OPENAI_API_KEY","")}
def trim(s,n=110):
    i=s.find("[["); j=s.find("]]")+2
    a=s[max(0,i-n):i]; b=s[j:j+n]
    a=a[a.find(" ")+1:] if i-n>0 else a; b=b[:b.rfind(" ")] if len(s)>j+n else b
    return (a+s[i:j]+b).replace("\n"," ")
def build():
    random.seed(11)
    inv=json.load(open("inventories.json")); pool=json.load(open("contexts_pool.json")); keys=json.load(open("top_lemmas.json"))
    reqs=[]; samples={}
    for key in keys:
        senses=inv.get(key) or []
        if len(senses)<2: continue           # 0/1 sense: no tagging needed
        ctx=pool[key][:]; random.shuffle(ctx); ctx=ctx[:25]
        samples[key]=ctx
        w,pos=key.split("|"); k=len(senses)
        slist="\n".join(f"{i+1}. {s['gloss']}" for i,s in enumerate(senses))+f"\n{k+1}. other sense / idiom / fixed expression not listed\n0. not this word (target is a different lemma/POS, a name, or a tagging error)"
        for b in range(0,len(ctx),10):
            part=ctx[b:b+10]
            c="\n".join(f"{b+j+1}) {trim(x['s'])}" for j,x in enumerate(part))
            prompt=(f"Spanish word-sense tagging. Lemma: {w} ({pos}). Senses:\n{slist}\n\nFor each context choose the sense number of the [[target]].\n{c}\n\n"
                    'JSON only: {"l":[[context_number,sense_number],...]}')
            reqs.append({"custom_id":f"{key}#{b}","method":"POST","url":"/v1/chat/completions",
              "body":{"model":MODEL,"reasoning_effort":"low","response_format":{"type":"json_object"},"max_completion_tokens":2000,
                      "messages":[{"role":"user","content":prompt}]}})
    json.dump(samples,open("samples.json","w"),ensure_ascii=False)
    with open("requests.jsonl","w") as f:
        for r in reqs: f.write(json.dumps(r,ensure_ascii=False)+"\n")
    chars=sum(len(r["body"]["messages"][0]["content"]) for r in reqs)
    print("lemmas tagged",len(samples),"requests",len(reqs),"prompt chars",chars,"~input tok",chars//3.5)
def api(method,path,data=None,files=None):
    if files:
        import uuid; bd=uuid.uuid4().hex; body=b""
        for k,v in data.items(): body+=f'--{bd}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode()
        body+=f'--{bd}\r\nContent-Disposition: form-data; name="file"; filename="b.jsonl"\r\nContent-Type: application/jsonl\r\n\r\n'.encode()+files+f"\r\n--{bd}--\r\n".encode()
        req=urllib.request.Request(API+path,data=body,headers={**H,"Content-Type":f"multipart/form-data; boundary={bd}"},method=method)
    else:
        req=urllib.request.Request(API+path,data=json.dumps(data).encode() if data else None,headers={**H,"Content-Type":"application/json"},method=method)
    r=urllib.request.urlopen(req,timeout=300).read()
    return r if path.endswith("/content") else json.loads(r)
def cost(u): 
    c=(u.get("prompt_tokens_details") or {}).get("cached_tokens",0)
    return ((u["prompt_tokens"]-c)*PIN+c*PCACHE+u["completion_tokens"]*POUT)/1e6
def run(chunk,cap,max_chunks=999):
    reqs=[l for l in open("requests.jsonl")]
    state=json.load(open("state.json")) if os.path.exists("state.json") else {"done":0,"spent":0.0,"chunks":[]}
    nchunks=0
    while state["done"]<len(reqs) and nchunks<max_chunks:
        nchunks+=1
        n_done=state["done"]
        if n_done>0:
            per=state["spent"]/n_done; proj=per*min(chunk,len(reqs)-n_done)*1.15  # 15% safety margin
            if state["spent"]+proj>cap:
                # shrink chunk to fit
                fit=int((cap-state["spent"])/(per*1.15))
                if fit<20: print("STOP: cap reached; spent",state["spent"]); break
                chunk=fit
        part=reqs[n_done:n_done+chunk]
        f=api("POST","/files",{"purpose":"batch"},"".join(part).encode())
        b=api("POST","/batches",{"input_file_id":f["id"],"endpoint":"/v1/chat/completions","completion_window":"24h"})
        print(time.strftime("%H:%M"),"submitted",b["id"],len(part),flush=True)
        while True:
            time.sleep(30); b=api("GET","/batches/"+b["id"])
            if b["status"] in ("completed","failed","expired","cancelled"): break
        print("status",b["status"],b.get("request_counts"),flush=True)
        spent=0.0; outs=[]
        if b.get("output_file_id"):
            for line in api("GET",f"/files/{b['output_file_id']}/content").decode().splitlines():
                o=json.loads(line); outs.append(o)
                if o.get("response") and o["response"].get("body",{}).get("usage"): spent+=cost(o["response"]["body"]["usage"])
        with open("outputs.jsonl","a") as fo:
            for o in outs: fo.write(json.dumps(o)+"\n")
        state["done"]+=len(part); state["spent"]+=spent; state["chunks"].append({"batch":b["id"],"n":len(part),"cost":spent,"status":b["status"]})
        json.dump(state,open("state.json","w"),indent=1)
        print("chunk cost",round(spent,4),"total",round(state["spent"],4),"done",state["done"],"/",len(reqs),flush=True)
        if b["status"]!="completed": print("batch not completed; stopping"); break
if __name__=="__main__":
    if sys.argv[1]=="build": build()
    else: run(int(sys.argv[2]),float(sys.argv[3]),int(sys.argv[4]) if len(sys.argv)>4 else 999)
