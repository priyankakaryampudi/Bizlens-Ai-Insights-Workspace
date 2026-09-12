# BizLens Final Testing Guide

## What this test pack validates

1. **Happy path:** full sales data + business documents produce a quantified business story.
2. **Evidence separation:** observed facts, focus areas, operational signals and hypotheses are kept distinct.
3. **No correlation dump:** business-facing outputs do not expose `r=0.xx` as a driver explanation.
4. **Evidence conflict:** mismatched periods/KPIs are surfaced for validation rather than silently resolved.
5. **Missing evidence:** unavailable fields do not produce invented KPIs.
6. **Causation boundary:** aggregate SLA/support/cancellation signals are not presented as proven causal relationships.
7. **Traceability:** recommendations retain evidence IDs where matching evidence exists.
8. **Recommendation quality:** recommendations are consolidated into a small, coherent decision path.
9. **Deliverables:** DOCX/PDF outputs are generated for the core BA document types.

## Manual acceptance checklist

- [ ] Home starts with an executive answer, not statistical coefficients.
- [ ] Business Context contains a clean validation note only when evidence genuinely conflicts.
- [ ] Requirements table contains actual solution requirements, not meeting-note discussion points.
- [ ] Investigation explains what changed, where, what signals moved and what is still unproven.
- [ ] Recommendations answer what management should do next, who owns it and how success is measured.
- [ ] Customer-level cancellation evidence is described as a gap when the dataset cannot support causal analysis.
- [ ] Final exports are readable and management-ready.

## Automated validation

```powershell
python run_tests.py
```
