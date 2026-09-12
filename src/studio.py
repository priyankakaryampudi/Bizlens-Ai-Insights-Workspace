from .reports import professional_sections, clip as _clip, quality_filter

def studio_sections(kind, objective, findings, signals, df, investigations, recommendations=None, evidence_register=None):
    base_map={
      'BRD':'Business Requirements Document (BRD)',
      'Functional Requirements Document (FRD)':'Functional Requirements Document (FRD)',
      'User Stories & Acceptance Criteria':'User Stories & Acceptance Criteria',
      'Use Case Catalogue':'Use Case Catalogue',
      'Process Specification (AS-IS / TO-BE)':'Process Specification',
      'Executive Brief':'Executive Business Report',
      'UAT & Test Scenarios':'UAT & Test Scenarios',
      'Requirements Traceability Matrix (RTM)':'Requirements Traceability Matrix (RTM)',
      'Root Cause Analysis (RCA)':'Root Cause Analysis (RCA)',
      'Product Requirements Document (PRD)':'Product Requirements Document (PRD)',
      'KPI / Performance Review':'KPI / Performance Review',
      'Data & Business Analysis Report':'Data & Business Analysis Report',
      'Implementation Roadmap':'Implementation Roadmap',
      'Stakeholder Analysis':'Stakeholder Analysis',
      'RACI Matrix':'RACI Matrix',
      'Gap Analysis':'Gap Analysis',
      'Business Case / Improvement Proposal':'Business Case / Improvement Proposal',
      'Action Plan':'Action Plan',
      'Requirements Traceability Matrix (RTM)':'Requirements Traceability Matrix (RTM)',
    }
    if kind in base_map:
        return professional_sections(base_map[kind],objective,findings,signals,df,investigations,recommendations,evidence_register)
    req=quality_filter(signals.get('requirements',[]), ['No approved requirement was extracted. Validate with stakeholders.'], require_verb=True)
    stakeholders=signals.get('stakeholders',[]) or ['No confirmed stakeholder list was extracted.']
    risks=quality_filter(signals.get('risks',[]), ['No explicit risk was extracted.'])
    questions=quality_filter(signals.get('questions',[]), ['No open question was extracted.'])
    return _remaining_sections(kind,objective,findings,signals,df,investigations,req,stakeholders,risks,questions)

def _remaining_sections(kind,objective,findings,signals,df,investigations,req,stakeholders,risks,questions):
    if kind=='Stakeholder Analysis':
        rows='| Stakeholder | Role | Interest | Influence | Concerns | Engagement approach |\n|---|---|---|---|---|---|\n'+'\n'.join(f'| {_clip(x,40)} | Confirm from evidence | TBD | TBD | TBD | Review and confirm |' for x in stakeholders)
        return [('1. Purpose',objective),('2. Stakeholder analysis',rows),('3. Evidence boundary','Only stakeholders explicitly identified in the connected evidence should be treated as confirmed.')]
    if kind=='RACI Matrix':
        rows='| Task | Responsible | Accountable | Consulted | Informed |\n|---|---|---|---|---|\n'+'\n'.join(f'| {_clip(r)} | TBD | TBD | TBD | TBD |' for r in req[:12])
        return [('1. Purpose',objective),('2. RACI matrix',rows),('3. Validation note','RACI assignments are draft placeholders until accountable stakeholders confirm them.')]
    if kind=='Gap Analysis':
        rows='| Current state evidence | Desired state | Gap | Required change | Evidence / validation |\n|---|---|---|---|---|\n'
        problems=(risks+questions)[:10]
        rows+='\n'.join(f'| {_clip(x)} | TBD / confirm objective | Gap to validate | Define approved change | Connected workspace |' for x in problems)
        return [('1. Business objective',objective),('2. Gap analysis',rows),('3. Next step','Validate the current-state evidence and desired-state criteria with the business owner.')]
    if kind=='Business Case / Improvement Proposal':
        return [('1. Problem',objective),('2. Proposed improvement','Select the intervention only after investigation evidence and stakeholder validation.'),('3. Expected benefits','Operational improvement, clearer ownership and measurable business outcome where supported by evidence.'),('4. Costs / considerations','TBD: people, systems, policy, change management and implementation effort.'),('5. Risks','\n'.join('- '+x for x in risks)),('6. Success measures','Define baseline, target, owner, source of truth and review frequency.')]
    if kind=='Action Plan':
        rows='| Action | Owner | Priority | Expected outcome | Evidence / dependency |\n|---|---|---|---|---|\n'
        rows+='\n'.join(f'| Validate: {_clip(q,110)} | TBD | Medium | Decision closed | Stakeholder confirmation |' for q in questions[:12])
        return [('1. Objective',objective),('2. Action plan',rows),('3. Governance','Review actions with the accountable business owner and retain evidence for completion decisions.')]
    return [('1. Overview',objective)]
