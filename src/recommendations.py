from .analytics import *

# Analytical triggers are intentionally conservative heuristics, not business truth.
# They help BizLens decide what deserves attention; they never establish causation.
TRIGGER_RULES = {
    'gap_pct_priority_1': 40,
    'decline_pct_investigate': -2,
    'improvement_pct_protect': 5,
    'concentration_pct_attention': 40,
}


def _item(priority, title, evidence, recommendation, owner, impact, measure, steps, dependencies='Confirm stakeholder ownership, source data and implementation constraints.'):
    return {
        'priority': priority, 'title': title, 'evidence': evidence,
        'recommendation': recommendation, 'owner': owner, 'impact': impact,
        'measure': measure, 'steps': steps, 'dependencies': dependencies,
    }


def build_recommendations(df, doc_signals=None, investigations=None):
    doc_signals = doc_signals or {}
    investigations = investigations or []
    items = []

    if df is not None and len(df):
        metric, dim, date = guess_metric(df), guess_dimension(df), guess_date(df)
        if metric and dim:
            g = dimension_breakdown(df, dim, metric, 20)
            if len(g) >= 2:
                top, bottom = g.iloc[0], g.iloc[-1]
                gap_pct = ((float(top.total) - float(bottom.total)) / max(abs(float(top.total)), 1)) * 100
                priority = 1 if gap_pct >= TRIGGER_RULES['gap_pct_priority_1'] else 2
                items.append(_item(
                    priority,
                    f'Close the {dim} performance gap before scaling a broad intervention',
                    f'{top[dim]} records {float(top.total):,.0f} for {metric}, compared with {float(bottom.total):,.0f} for {bottom[dim]}. The observed gap is {gap_pct:.1f}% relative to the leading group.',
                    f'Run a focused diagnostic on {bottom[dim]} versus {top[dim]} across the next available business dimension and the relevant time period. Identify the specific controllable difference, then pilot the corrective action in the weakest group before rolling it out.',
                    'Business owner + process owner',
                    'High potential if the gap reflects a controllable process or customer issue.',
                    f'Reduce the gap in {metric} between the weakest and leading {dim} groups.',
                    ['Validate the comparison and metric definition.', 'Identify the operational/customer driver through drill-down.', 'Pilot one corrective action.', 'Review KPI movement before scaling.']
                ))
                concentration = float(top.total) / max(float(g.total.sum()), 1)
                if concentration >= TRIGGER_RULES['concentration_pct_attention'] / 100:
                    items.append(_item(
                        2,
                        f'Reduce dependency on {top[dim]}',
                        f'{top[dim]} represents {concentration*100:.1f}% of the observed {metric} across the analysed groups.',
                        'Assess whether the current outcome is overly dependent on one segment. Build a second reliable contributor rather than assuming the leading group will continue carrying the same share.',
                        'Business / growth owner',
                        'Medium to high resilience improvement.',
                        f'Monitor concentration of {metric} in the leading {dim} group.',
                        ['Validate concentration over time.', 'Identify underperforming but scalable groups.', 'Select one diversification experiment.', 'Track contribution share monthly.']
                    ))

        if metric and date:
            t = trend(df, date, metric)
            if len(t) >= 2 and pd.notna(t.iloc[-1].change_pct):
                pct = float(t.iloc[-1].change_pct)
                prev, recent = float(t.iloc[-2][metric]), float(t.iloc[-1][metric])
                if pct <= TRIGGER_RULES['decline_pct_investigate']:
                    items.append(_item(
                        1,
                        f'Contain and explain the latest {metric} decline',
                        f'{metric} changed {pct:.1f}% in the latest observed period ({prev:,.0f} → {recent:,.0f}).',
                        'Treat the decline as an investigation trigger. Break it into volume, mix, customer/segment and operational contributors before committing to a remedy.',
                        'Performance owner',
                        'High if the decline is persistent.',
                        f'Restore and sustain the previous {metric} trajectory.',
                        ['Confirm the period and source data.', 'Locate the segments driving the change.', 'Check process/customer events around the change.', 'Agree a corrective action and review date.']
                    ))
                elif pct >= TRIGGER_RULES['improvement_pct_protect']:
                    items.append(_item(
                        2,
                        f'Protect the recent {metric} improvement',
                        f'{metric} increased {pct:.1f}% in the latest observed period ({prev:,.0f} → {recent:,.0f}).',
                        'Identify the segment and operating conditions associated with the improvement, then convert the repeatable part into a monitored business practice instead of assuming the increase will persist.',
                        'Business / operations owner',
                        'Opportunity to preserve a positive movement.',
                        f'Sustain the improved {metric} level over subsequent periods.',
                        ['Validate the improvement.', 'Identify contributing segments and conditions.', 'Document the repeatable practice.', 'Monitor for regression.']
                    ))

        qa = quality_actions(df)
        if qa:
            biggest = qa[0]
            priority = 1 if biggest['count'] >= max(5, len(df)*.05) else 3
            items.append(_item(
                priority,
                f'Fix the data issue affecting {biggest["issue"].lower()}',
                f'{biggest["count"]:,} records or values are affected. {biggest["treatment"]}',
                'Assign a data owner, confirm the source-of-truth treatment and document the rule before the affected KPI is used for management decisions.',
                'Data / analytics owner',
                'Improves confidence and reproducibility of every downstream decision.',
                'Affected-record count and recurrence rate should trend down to an agreed threshold.',
                ['Identify the source system or process.', 'Agree the treatment rule.', 'Correct or exclude only with traceability.', 'Add a recurring quality check.']
            ))

    for risk in doc_signals.get('risks', [])[:3]:
        items.append(_item(1, 'Mitigate a documented business risk', risk,
            'Convert the risk into a named action with owner, likelihood, impact, mitigation, dependency and decision date.',
            'Business owner', 'Reduces unmanaged delivery or operational exposure.', 'Risk status and mitigation completion.',
            ['Validate the risk statement.', 'Assign owner.', 'Define mitigation.', 'Review at the next governance checkpoint.']))

    for question in doc_signals.get('questions', [])[:3]:
        items.append(_item(2, 'Close an open business decision', question,
            'Resolve the missing definition or decision before baselining requirements, committing delivery scope or measuring success.',
            'Product / business owner', 'Prevents rework and scope ambiguity.', 'Open-question count and decision turnaround time.',
            ['Identify the decision owner.', 'Provide the required evidence.', 'Set a decision date.', 'Record the outcome and downstream impact.']))

    for inv in investigations[:2]:
        items.append(_item(1, f'Validate the saved investigation: {inv.get("focus", "selected segment")}', inv.get('signal','Saved investigation evidence exists.'),
            'Complete the documented cross-dimension and time checks, then confirm or reject the working hypothesis with the responsible process owner.',
            'Investigation owner', 'Turns an observed signal into a validated decision input.', 'Hypothesis confirmed/rejected with evidence.',
            inv.get('hypotheses', ['Review the saved evidence and confirm the next validation step.'])))

    dedup = {}
    for item in items:
        key = item['title']
        if key not in dedup or item['priority'] < dedup[key]['priority']:
            dedup[key] = item
    return sorted(dedup.values(), key=lambda x: (x['priority'], x['title']))[:8]
