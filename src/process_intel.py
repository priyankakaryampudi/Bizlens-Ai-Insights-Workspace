def process_artifacts(ctx):
    reqs=ctx.get('requirements',[])
    actors=ctx.get('stakeholders',[]) or ['Business User','Process Owner','System']
    steps=['Start request','Capture required information','Validate completeness','Route for review/approval','Perform required action','Notify stakeholders','Close and track outcome']
    return {'actors':actors,'as_is':steps,'gaps':['Manual handoffs or unclear ownership may delay progress','Requirements may be captured inconsistently','Status visibility may be fragmented'],'to_be':['Start request','Validate required information automatically','Assign clear owner','Route approval with status tracking','Handle exceptions','Notify stakeholders and record outcome'],'requirements_used':reqs[:10]}

def use_cases(ctx):
    reqs=ctx.get('requirements',[]) or ['The system shall support the documented business process']
    actor=(ctx.get('stakeholders') or ['Business User'])[0]
    return [{'name':f'UC-{i+1}: {r[:70]}','actor':actor,'preconditions':'Required information is available','trigger':'Actor initiates the business request','main_flow':['Validate information','Process request','Record outcome'],'alternative_flow':['Request correction when validation fails'],'exceptions':['System or approval exception is logged'],'postconditions':'Outcome and status are available'} for i,r in enumerate(reqs[:5])]
