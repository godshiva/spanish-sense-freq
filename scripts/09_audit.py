"""Missing-words audit (v0.3). Flags (1) core closed-class words absent from the published list and
(2) high-frequency lemmas from external lists that are absent, with a reason for each gap.
Usage (from the work dir, after 05):  python 09_audit.py [--csv spanish_sense_frequency.csv] [--top 3000]
External lists expected in ./audit/: es_50k.txt (hermitdave FrequencyWords 2018, OpenSubtitles),
wikt2000.json (Wiktionary:Frequency_lists/Spanish1000 + 1001-2000, with lemma column),
buchmeier10k.json (User:Matthias_Buchmeier/Spanish_frequency_list 1-10000). Writes audit_report.json
and prints a summary; exit code 1 if any closed-class word is missing and not explained."""
import json, csv, sys, os, argparse, collections
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import ssf_lex as L
CLOSED={
 "determiner":"el uno este ese aquel mi tu su nuestro mucho poco todo otro alguno ninguno cualquiera cada varios demasiado bastante tanto mismo propio cierto tal ambos",
 "pronoun":"yo tú usted él ella ello nosotros ustedes me te se lo le nos mí ti sí conmigo contigo consigo esto eso aquello algo nada alguien nadie quien que cual cuyo mío tuyo suyo",
 "preposition":"a ante bajo con contra de desde durante en entre hacia hasta mediante para por según sin sobre tras",
 "conjunction":"y e o u ni pero sino que porque aunque si como cuando mientras pues",
 "adverb":"muy más menos ya también tampoco siempre nunca jamás aún todavía casi solo bien mal ahora hoy ayer mañana aquí allí allá acá ahí entonces luego después antes tan así sí no quizá donde",
 "numeral":"dos tres cuatro cinco seis siete ocho nueve diez once doce veinte treinta cien ciento mil millón primero segundo tercero",
 "question word":"qué quién cuál cuánto dónde cuándo cómo adónde porqué"}
SPAIN_ONLY={"vosotros","os","vuestro"}   # documented exclusions (rule: no Spain-only words are added)
def main():
    ap=argparse.ArgumentParser(); ap.add_argument("--csv",default="spanish_sense_frequency.csv"); ap.add_argument("--top",type=int,default=3000)
    ap.add_argument("--counts",default="lemma_counts.json"); ap.add_argument("--forms",default="surface_forms.json"); a=ap.parse_args()
    rows=list(csv.DictReader(open(a.csv)))
    first={}
    for r in rows: first.setdefault(r["lemma"],int(r["rank"]))
    have=set(first)
    lc=json.load(open(a.counts)); total=lc["total_tokens"]; cnt=dict(lc["counts"])
    lemma_cnt=collections.Counter()
    for k,n in cnt.items(): lemma_cnt[k.split("|")[0]]+=n
    inv=collections.defaultdict(collections.Counter)    # surface -> lemma counts (from 02 count stage)
    if os.path.exists("surface_lemma.json"):
        for sf,k in json.load(open("surface_lemma.json")).items(): inv[sf][k.split("|")[0]]+=1
    elif os.path.exists(a.forms):
        for k,forms in json.load(open(a.forms)).items():
            for s,n in forms: inv[s][k.split("|")[0]]+=n
    keymax=collections.Counter()
    for k,n in cnt.items(): keymax[k.split("|")[0]]=max(keymax[k.split("|")[0]],n)
    thr=144*1e6/total   # tagging threshold used by 10_incremental.py (MIN_COUNT)
    ABBR={"sr","sra","srta","dr","dra","ud","uds","mr","mrs","km","tv","eeuu","fbi","adn","ia","s"}
    EN=set("the to of and you i it is be will um ei io".split())
    def why(lemma):
        l=lemma.rstrip(".")
        if lemma in SPAIN_ONLY: return "excluded: Spain-only"
        if l in ABBR or lemma.endswith("."): return "abbreviation/symbol (not counted as a word)"
        if l in EN: return "English/foreign token"
        c=keymax.get(lemma,0)
        if c==0: return "not in corpus counts as a common word (proper name, or lemmatised elsewhere)"
        fpm=c*1e6/total
        if fpm<thr: return f"below tagging threshold ({fpm:.1f}/M < {thr:.1f}/M; mostly a proper name if capitalised in text)"
        return f"above threshold ({fpm:.1f}/M) but no usable Wiktionary senses"
    rep={"closed_class":{},"external":{}}
    bad=[]
    for cat,ws in CLOSED.items():
        for w in ws.split():
            ok=w in have
            rep["closed_class"][w]={"category":cat,"present":ok,"first_rank":first.get(w),"reason":None if ok else why(w)}
            if not ok and w not in SPAIN_ONLY: bad.append(w)
    def map_surface(s):
        if s in have: return s
        if inv.get(s): return inv[s].most_common(1)[0][0]
        return None
    ext={}
    if os.path.exists("audit/wikt2000.json"):
        ext["wiktionary_2000"]=[(r,w,lem) for r,w,lem in json.load(open("audit/wikt2000.json"))]
    if os.path.exists("audit/es_50k.txt"):
        ext["hermitdave_50k"]=[(i+1,l.split()[0],[]) for i,l in enumerate(open("audit/es_50k.txt")) if l.strip()][:a.top]
    if os.path.exists("audit/buchmeier10k.json"):
        ext["buchmeier_10k"]=[(i+1,w,[]) for i,(w,_) in enumerate(json.load(open("audit/buchmeier10k.json")))][:a.top]
    for name,items in ext.items():
        gaps=[]
        for r,w,lems in items[:a.top]:
            w=w.lower(); cands=[x.lower() for x in lems]+[w]; m=map_surface(w)
            if m: cands.append(m)
            if any(c in have for c in cands): continue
            key=m or (lems[0].lower() if lems else w)
            gaps.append({"rank":r,"word":w,"mapped_lemma":key,"reason":why(key)})
        rep["external"][name]={"checked":min(a.top,len(items)),"gaps":len(gaps),"items":gaps}
    json.dump(rep,open("audit_report.json","w"),ensure_ascii=False,indent=1)
    print("closed-class missing:",bad or "none")
    for n,v in rep["external"].items():
        print(f"{n}: {v['gaps']} gaps in top {v['checked']}; first 25:",[(g['rank'],g['word'],g['mapped_lemma']) for g in v['items'][:25]])
    sys.exit(1 if bad else 0)
if __name__=="__main__": main()
