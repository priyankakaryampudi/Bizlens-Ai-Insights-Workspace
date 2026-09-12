import sys
sys.path.insert(0,'.')
import pandas as pd
from src.analytics import profile,guess_metric,guess_dimension,guess_date,forecast,auto_insights,investigation_metrics,data_quality_findings
from src.doc_intel import extract_signals,ambiguity_flags

df=pd.read_csv('data/sales_demo.csv')
assert profile(df)['rows']==24
assert guess_metric(df)=='Revenue'
assert guess_dimension(df)=='Region'
assert guess_date(df)=='Date'
assert forecast(df,'Date','Revenue',3) is not None
assert auto_insights(df,'Revenue','Region','Date')
assert not investigation_metrics(df,'Revenue','Region').empty
text='Management agreed to automate reporting. The system should be fast. Owner to follow up. What is the SLA?'
s=extract_signals(text)
assert s['requirements'] and s['decisions'] and s['actions'] and s['questions']
assert ambiguity_flags(text)
assert data_quality_findings(df) is not None
print('ALL SMOKE TESTS PASSED')
