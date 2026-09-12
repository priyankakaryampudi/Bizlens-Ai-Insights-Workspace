# BizLens 4.1 — Final

AI-assisted Business Analysis Workspace.

## What changed

- Ask BizLens now routes the user's exact question to either the local evidence engine or the optional OpenAI reasoning layer.
- Dataset analysis uses business KPIs first and keeps missing values, duplicates and outliers in a separate Data Quality area.
- Investigation uses period-aligned business drivers (region, product, segment, channel, SLA and service pressure) instead of presenting statistical coefficients as root causes.
- Home, Business Context and Investigation lead with an executive answer and explicitly separate business focus, operational signals, hypotheses and confirmed facts.
- Recommendations are consolidated around one coherent solution path instead of generating one recommendation per chart. Each recommendation states the evidence, action, owner, success measure and decision boundary.
- BA Studio now exposes six core deliverables with distinct professional structures.
- BRD, FRD, User Stories, UAT and RTM share requirement IDs for traceability.
- DOCX/PDF exports preserve tables instead of dropping pipe-formatted content.
- A session-only OpenAI API key can be entered from the sidebar; no key is stored in source code.
- `run_bizlens.bat` creates the Python 3.13 environment and installs dependencies automatically.

## Windows / VS Code

Preferred Python version for this project: **Python 3.13**.

From the project folder:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Or simply double-click `run_bizlens.bat`.

If PowerShell says `.venv\Scripts\Activate.ps1` does not exist, the virtual environment has not been created in that folder yet. Run:

```powershell
py -3.13 -m venv .venv
```

Then activate it.

## Optional AI key

BizLens works without an API key using its deterministic evidence engine. For richer natural-language answers, either enter the key in the sidebar under **AI connection** or set:

```powershell
$env:OPENAI_API_KEY="your-key-here"
```

Never hard-code or commit a real API key.

## Data quality philosophy

BizLens detects duplicates, missing values, inconsistent fields and potential outliers without silently changing the source data. Mean/median/mode are conditional treatment options, not automatic fixes. A BA should validate the business meaning before imputation or deletion.

## Validation

```powershell
python -m compileall -q .
python tests\smoke_test.py
```

## AI and evidence behavior
BizLens works without an API key for calculations, charts, profiling and deterministic evidence answers. Optional Gemini/OpenAI synthesis can be configured in the sidebar for the current session only. API keys are not written to project files.

## Evidence rule
BizLens verifies a claimed trend or decline before proposing contributors or causes. Observed patterns, operational signals and document leads are labelled separately from proven causation. Automatic correlation coefficients are kept out of the business-facing pages.


## Final evidence and requirements hardening

The final 4.1 release keeps the established 4.1 application and deliverable experience while tightening the underlying BA quality controls:
- Explicit primary and secondary analysis periods are retained in evidence where available.
- Hypotheses use evidence-linked validation plans, including a customer-level validation path for service-to-cancellation questions.
- Functional, business and non-functional requirements are kept conceptually separate.
- Acceptance criteria and UAT scenarios use observable outcomes rather than generic approval text.
- Stakeholder ownership is not silently invented; unconfirmed owners are labelled for confirmation.
- AS-IS process documentation does not manufacture organisational actors or operational steps when the evidence does not establish them.
- Traceability and evidence links are shown as established only when a direct relationship can be supported.

## Final BA workflow

The intended flow is:

**Business problem → quantified change → focus area → contributing signals → validation → business impact → recommended action → owner → success measure.**

Analytical thresholds in the recommendation layer are explicit heuristics used to surface attention. They are not business-approved targets and never establish causation. BizLens keeps observed facts, derived patterns, document-supported leads and unvalidated hypotheses separate.

BizLens deliberately does not label a region, product or correlation as a root cause unless the connected evidence supports that conclusion.

## Included test evidence

The `test_data/` folder includes the full sales dataset plus requirements, management review, executive context, meeting notes and customer-call evidence. Run `python run_tests.py` to execute smoke, architecture, regression and final BA-quality tests.

## Final content polish
- Business Context now prefers evidence-derived drivers and pain points over generic theme labels.
- Solution direction is generated from the actual investigation signals (focus area, service performance and declining commercial pockets).
- Executive wording keeps facts, signals, hypotheses and evidence gaps distinct.
- Recommendations remain consolidated around a coherent solution path rather than one recommendation per chart.

## Portfolio positioning

BizLens is designed to demonstrate BA reasoning rather than just AI output: frame the problem, establish evidence, investigate a focused signal, distinguish fact from hypothesis, recommend an action with an owner and measure, then hand the result into a professional deliverable.

## Professional BA deliverables

The `deliverables/` folder contains a portfolio-style, end-to-end artifact pack based on the connected test evidence. It includes an Executive Brief, BRD, PRD, FRD, AS-IS/TO-BE process specification, RCA, Data & Business Analysis report, KPI review, Gap Analysis, Business Case, RTM, Implementation Roadmap, User Stories, Use Cases, UAT scenarios, Stakeholder Analysis, RACI and Action Plan. The pack is also available as `deliverables/BizLens_Deliverables_Pack.zip`.
