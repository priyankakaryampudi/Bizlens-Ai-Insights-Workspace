import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import pandas as pd
from src.intelligence import investigation_brief, decision_recommendations
from src.analytics import custom_analysis_request
from src.studio import studio_sections

def run():
    df=pd.read_csv('test_data/BizLens_Test_Sales_Data.csv')
    sig={'requirements':['The solution shall provide revenue KPIs.'],'stakeholders':['Management'],'risks':['Approval delays'],'questions':['Who owns overdue approvals?'],'decisions':[]}
    brief=investigation_brief(df,sig,'Why is performance changing?')
    assert brief['problem']=='Why is performance changing?'
    assert brief.get('evidence') is not None
    recs=decision_recommendations(df,sig,[])
    assert all('data-quality' not in r.get('title','').lower() for r in recs)
    result,_=custom_analysis_request(df,'Compare Revenue by Region')
    assert result is not None
    for kind in ['Stakeholder Analysis','RACI Matrix','Gap Analysis','Business Case / Improvement Proposal','Action Plan','BRD','Use Cases']:
        assert studio_sections(kind,'Improve performance',['Revenue changed'],sig,df,[])
    print('V3 ARCHITECTURE TESTS PASSED')

if __name__=='__main__': run()
