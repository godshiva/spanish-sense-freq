"""spaCy es_core_news_md: count lemma+POS over segments.jsonl and reservoir-sample contexts.
Outputs lemma_counts.json and contexts_pool.json (up to 40 contexts per lemma|POS)."""
import json, random, collections, spacy
random.seed(7)
KEEP={"NOUN","VERB","ADJ","ADV","PRON","DET","ADP","CCONJ","SCONJ","INTJ"}
nlp=spacy.load("es_core_news_md",disable=["parser","ner"])
segs=[json.loads(l) for l in open("segments.jsonl")]
cnt=collections.Counter(); gcnt=collections.Counter(); seen=collections.Counter(); pool={}
R=40
def texts():
    for i,s in enumerate(segs): yield (s["text"],i)
for doc,i in nlp.pipe(texts(),as_tuples=True,batch_size=200,n_process=3):
    g=segs[i]["genre"]
    for t in doc:
        if not t.is_alpha: continue
        gcnt[g]+=1
        pos="VERB" if t.pos_=="AUX" else t.pos_
        if pos not in KEEP: continue
        key=t.lemma_.lower()+"|"+pos
        cnt[key]+=1; seen[key]+=1; n=seen[key]
        if n<=R or random.random()<R/n:
            a=max(0,t.idx-160); b=min(len(doc.text),t.idx+len(t.text)+160)
            snip=doc.text[a:t.idx]+"[["+t.text+"]]"+doc.text[t.idx+len(t.text):b]
            item={"g":g,"src":segs[i]["src"],"s":snip}
            if n<=R: pool.setdefault(key,[]).append(item)
            else: pool[key][random.randrange(R)]=item
total=sum(gcnt.values())
json.dump({"total_tokens":total,"genre_tokens":gcnt,"counts":cnt.most_common()},open("lemma_counts.json","w"),ensure_ascii=False)
top=[k for k,_ in cnt.most_common(6000)]
json.dump({k:pool[k] for k in top},open("contexts_pool.json","w"),ensure_ascii=False)
print(total,gcnt,cnt.most_common(30))
