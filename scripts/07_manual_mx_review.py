"""Apply the hand review of all rows flagged non_mexican by the LLM (06). non_mexican now means REGIONAL
(not normal in Mexico specifically), not register. Logs every change to data/manual_corrections.csv.
Usage: python 07_manual_mx_review.py manual_decisions.json  (run in data/)"""
import csv, json, sys
dec=json.load(open(sys.argv[1])); keep=set(dec["keep_regional"]); nu=set(dec["set_not_used"])
R=list(csv.DictReader(open("spanish_sense_frequency.csv"))); log=[]
def ch(r,f,new,why):
    if str(r[f])!=str(new): log.append({"sense_id":r["sense_id"],"field":f,"old":r[f],"new":new,"reason":why}); r[f]=new
for r in R:
    sid=r["sense_id"]
    if sid in dec["fill"]:
        s,e,n=dec["fill"][sid]; ch(r,"mx_status",s,"filled missing value (manual)"); ch(r,"non_mexican","False","filled missing value (manual)"); ch(r,"mx_note",n,"filled missing value (manual)")
        continue
    if r["non_mexican"]!="True": continue
    if sid in keep:
        if sid in nu: ch(r,"mx_status","not_used","manual: coger is vulgar in Mexico in this sense too")
        continue
    why="manual review: flag reflected register (literary/archaic/formal/technical) or the example snippet, not regional usage"
    if sid in dec["special_notes"]: why="manual review: wrong flag; "+dec["special_notes"][sid]
    ch(r,"non_mexican","False",why); ch(r,"mx_status","common",why); ch(r,"mx_equivalent","",why)
    ch(r,"mx_note",dec["special_notes"].get(sid,"Not regional; any issue is register or context (see register column)."),why)
with open("spanish_sense_frequency.csv","w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=list(R[0].keys())); w.writeheader(); w.writerows(R)
with open("manual_corrections.csv","a" if __import__("os").path.exists("manual_corrections.csv") else "w",newline="") as f:
    w=csv.DictWriter(f,fieldnames=["sense_id","field","old","new","reason"])
    if f.tell()==0: w.writeheader()
    w.writerows(log)
print("changes",len(log),"rows changed",len({l['sense_id'] for l in log}),"non_mexican now",sum(r["non_mexican"]=="True" for r in R))
