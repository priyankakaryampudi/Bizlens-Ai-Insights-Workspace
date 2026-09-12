import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))

from src.ai import classify_question, ai_status
from src.ingest import classify

def run():
    assert classify_question('What is the total revenue?', object(), {}) == 'data'
    assert classify_question('Which region performs best?', __import__('pandas').DataFrame({'Region':['A'],'Revenue':[1]}), {}) == 'data'
    assert classify_question('Show data quality issues', __import__('pandas').DataFrame({'Revenue':[1]}), {}) == 'data'
    assert classify_question('What requirements are documented?', None, {'requirements':['x']}) == 'documents'
    assert classify_question('Why is revenue declining and what should we investigate?', object(), {'risks':['x']}) == 'combined'
    status=ai_status()
    assert 'configured' in status and 'mode' in status
    data_dir=ROOT/'data'
    required=['sales_demo.csv','demo_meeting_notes.docx','demo_requirements.pdf','demo_business_review.pptx']
    assert all((data_dir/x).exists() for x in required)
    assert classify('sales_demo.csv')=='dataset'
    assert classify('demo_meeting_notes.docx')=='document'
    print('REGRESSION TESTS PASSED')

if __name__=='__main__': run()
