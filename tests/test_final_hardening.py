import sys
from pathlib import Path
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

from src.doc_intel import extract_signals
from src.evidence import build_evidence_register
from src.intelligence import investigation_brief, decision_recommendations
from src.reports import professional_sections

DATA=ROOT/"test_data"/"BizLens_Test_Sales_Data.csv"
df=pd.read_csv(DATA,parse_dates=["Date"])

# Minimal document context matching the supplied demo evidence.
context_text="""Management needs to understand the South revenue decline.
The solution shall provide revenue, orders, customers and cancellation KPIs.
The solution shall identify significant changes and rank contributing dimensions.
The interface should be understandable to a non-technical business user.
The system should handle incomplete data without silently inventing values.
Investigate the relationship between SLA achievement and cancellations."""
sig=extract_signals(context_text)
sig["_context_text"]=context_text
arts=[{"name":DATA.name,"kind":"csv","text":""}]
reg=build_evidence_register(arts,df,sig,"")
brief=investigation_brief(df,sig,"")
assert brief["hypotheses"], "Expected investigation hypotheses"
cancel=[h for h in brief["hypotheses"] if h.get("kind")=="cancellation"]
if cancel:
    assert "customer/order-level cancellation" in " ".join(cancel[0]["validation"])
    assert "Link SLA breaches" in " ".join(cancel[0]["validation"])

recs=decision_recommendations(df,sig,[],"",reg)
assert all(r["owner"]=="Not specified - confirmation required" for r in recs)
assert all("suggested_owner" in r for r in recs)

sections=professional_sections("Functional Requirements Document (FRD)","",[],sig,df,[],recs,reg)
frd=dict(sections)
fr=frd["2. Functional requirements"]
assert "FR-001" in fr
assert "interface should be understandable" not in fr.lower()
assert "system should handle incomplete data" not in fr.lower()
assert "Given" in fr and "Then" in fr

process=dict(professional_sections("Process Specification","",[],sig,df,[],recs,reg))
asis=process["2. AS-IS process"]
assert "Actors, hand-offs and system steps: Not specified" in asis

print("FINAL HARDENING TEST PASSED")
