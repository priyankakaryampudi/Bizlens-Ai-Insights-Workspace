# BizLens

**BizLens — AI-Assisted Business Analysis Workspace**

BizLens is a Streamlit application that turns raw business evidence — sales data, requirements docs, meeting notes, management reviews, call transcripts — into a single connected workspace that a Business Analyst can use to go from "something changed" to a management-ready decision pack.

It is built to demonstrate BA reasoning, not just AI output. The workflow deliberately mirrors how a real BA works a problem:

> **Business problem → quantified change → focus area → contributing signals → validation → business impact → recommended action → owner → success measure → professional deliverable**

---

## Table of contents

- [What BizLens does](#what-bizlens-does)
- [Core design principles](#core-design-principles)
- [How the workspace is organized](#how-the-workspace-is-organized)
- [Project structure](#project-structure)
- [Installation and setup](#installation-and-setup)
- [Running BizLens](#running-bizlens)
- [Optional AI configuration](#optional-ai-configuration)
- [Working with your own data](#working-with-your-own-data)
- [Included demo/test evidence](#included-demotest-evidence)
- [Deliverables pack](#deliverables-pack)
- [Testing and validation](#testing-and-validation)
- [Data quality philosophy](#data-quality-philosophy)
- [Evidence rule (how BizLens avoids false causation)](#evidence-rule-how-bizlens-avoids-false-causation)

---

## What BizLens does

You connect the business evidence you already have — a sales dataset (CSV/XLSX), and supporting documents (requirements, meeting notes, management reviews, call transcripts, as PDF/DOCX/PPTX/TXT) — and BizLens:

1. **Profiles the data and reads the documents** to build a shared picture of the business situation.
2. **States what changed**, quantified, before speculating about why.
3. **Investigates** where the change is concentrated (region, product, segment, channel, SLA/service pressure) and what signals move with it — without presenting a statistical correlation as a proven cause.
4. **Separates fact from hypothesis.** Observed facts, derived patterns, document-supported leads, and unvalidated hypotheses are always kept visually and structurally distinct.
5. **Recommends one coherent action path** (not one recommendation per chart), each with the supporting evidence, the action, an owner, a success measure, and the boundary of what the recommendation does and doesn't claim.
6. **Produces professional BA deliverables** — BRD, FRD, PRD, RCA, RTM, Business Case, UAT scenarios, RACI, and more — generated directly from the same connected evidence, so every document in the pack is traceable back to the same workspace.

You can also just **ask BizLens a question** in plain language ("Why did revenue drop in Q4?", "What are the open requirements?", "Who are the stakeholders?") and it routes the question to the right source: local Python calculations for numbers, extracted document evidence for business context, and an optional AI layer for synthesis and phrasing.

## Core design principles

- **Evidence before assumptions.** Nothing is labelled a root cause unless the connected evidence actually supports that conclusion.
- **Works with zero AI configuration.** All calculations, charts, profiling, and evidence answers run on a deterministic local Python engine. AI (Gemini or OpenAI) is optional and only used for natural-language synthesis — never for the underlying numbers.
- **No silent data changes.** BizLens detects duplicates, missing values, inconsistent fields, and outliers, and surfaces them in a separate Data Quality area. It never imputes or deletes automatically — a BA validates the business meaning first.
- **Correlation is not causation.** Automatic correlation coefficients are computed internally but are kept out of business-facing pages; the app talks in observed patterns and validated hypotheses instead of "r = 0.xx" style statistics.
- **Traceability across deliverables.** BRD, FRD, User Stories, UAT scenarios, and the RTM share requirement IDs, so a requirement can be traced end-to-end through the deliverable pack.
- **Unconfirmed ownership is never invented.** If a stakeholder owner isn't established by the evidence, it's labelled "for confirmation" rather than guessed.

## How the workspace is organized

The app's navigation follows the BA workflow, grouped into five stages:

| Group | Page | Purpose |
|---|---|---|
| **Workspace** | Home | Connect evidence (upload or try the demo workspace); shows the executive answer — what changed, and the current solution direction. |
| | Ask BizLens | Free-text Q&A, routed to local evidence or AI synthesis depending on the question type. |
| **Understand** | Data & Insights | Auto-built executive dashboard from the active dataset: KPIs, charts, and a separate Data Quality panel. |
| | Business Context | The BA view of the problem: extracted requirements, business evidence, and decisions still needed. |
| **Investigate** | Investigation | Where the change is concentrated, what business drivers move with it, and what's still unproven. |
| **Decide** | Recommendations | The consolidated recommended solution path — evidence, action, owner, success measure, and decision boundary. |
| **Deliver** | Studio | Generates the professional BA deliverables (DOCX/PDF/XLSX) from the connected workspace. |

Evidence you upload from any page stays connected across every other page — you build the workspace once.

## Project structure

```
BizLens/
├── app.py                     # Streamlit entry point, page routing, sidebar (uploads + AI key)
├── run_bizlens.bat            # Windows one-click setup + launch
├── run_tests.py                # Runs the full test suite
├── requirements.txt
├── VERSION.txt
├── TESTING_GUIDE.md            # Manual + automated acceptance checklist
├── .env.example                 # Template for an optional Gemini API key
├── .streamlit/config.toml
│
├── pages/                     # One Streamlit page per workflow stage
│   ├── home.py
│   ├── 1_Ask.py
│   ├── 2_Data.py
│   ├── 3_Investigation.py
│   ├── 5_Documents.py
│   ├── 6_Recommendations.py
│   └── 7_Deliverables.py
│
├── src/                       # Application logic
│   ├── ingest.py               # File upload handling / parsing entry point
│   ├── doc_intel.py            # Extracts business signals from documents
│   ├── analytics.py            # KPI detection, metric/dimension guessing, dashboards
│   ├── intelligence.py         # Evidence graph, investigation briefs, recommendations engine
│   ├── workspace_intelligence.py # Workspace-level context building, technique selection
│   ├── workspace.py             # Shared workspace state backbone used by all pages
│   ├── evidence.py             # Central Evidence Object model (fact/hypothesis/signal tracking)
│   ├── recommendations.py       # Decision recommendation logic
│   ├── process_intel.py         # AS-IS/TO-BE process modeling
│   ├── diagrams.py              # Graphviz-based flowchart rendering for process specs
│   ├── reports.py               # DOCX/PDF generation for deliverables
│   ├── studio.py                # Deliverables Studio section definitions
│   ├── dashboard_export.py      # Self-contained HTML dashboard export
│   ├── ai.py                    # AI routing (Gemini/OpenAI), question classification
│   ├── state.py                 # Session state initialization
│   ├── styles.py                # CSS injection, branding, UI components
│   └── ui.py                    # Shared UI helpers (uploads, workspace clearing)
│
├── data/                       # Small built-in demo dataset + documents ("Try the demo workspace")
├── test_data/                  # Full test evidence set (sales data + supporting documents)
├── tests/                      # Automated tests (smoke, regression, architecture, hardening)
│
└── deliverables/               # Pre-generated example output pack (18 BA artefacts, DOCX + PDF/XLSX)
    ├── README.md / INDEX.md
    └── BizLens_Deliverables_Pack.zip
```

## Installation and setup

**Requirements:** Python 3.13 (preferred). Tested on Windows / VS Code.

From the project folder:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Or simply double-click **`run_bizlens.bat`**, which creates the virtual environment and installs dependencies automatically.

If PowerShell says `.venv\Scripts\Activate.ps1` does not exist, the environment hasn't been created yet — run `py -3.13 -m venv .venv` first, then activate it.

### Key dependencies

| Purpose | Library |
|---|---|
| App framework | `streamlit` |
| Data handling | `pandas`, `numpy`, `openpyxl`, `xlrd` |
| Charts | `plotly` |
| Document parsing | `python-docx`, `pypdf`, `pdfplumber`, `python-pptx` |
| Report generation | `reportlab` (PDF), `python-docx` (DOCX) |
| Diagrams | `graphviz` |
| AI (optional) | `google-genai`, `openai` |
| Config | `python-dotenv` |

## Running BizLens

Once launched, the app opens on **Home**. From there you either:

- Upload your own files (CSV/XLSX dataset + DOCX/PDF/PPTX/TXT documents), or
- Click **"Try the complete demo workspace"** to load the built-in demo dataset and documents instantly.

Once evidence is connected, walk through the pages left to right (Home → Ask → Data & Insights → Business Context → Investigation → Recommendations → Studio) — each stage builds on the last, and you can add more evidence at any point without losing your place.

## Optional AI configuration

BizLens is **fully functional with no AI key** — all KPIs, charts, profiling, and evidence-based answers run locally. An AI key only improves the *quality of natural-language phrasing* in synthesis answers; it never touches the underlying calculations.

To enable it:

- **Session-only:** enter a key directly in the sidebar under **AI Connection**, or
- **Persistent:** copy `.env.example` to `.env` and add your key:

  ```
  GEMINI_API_KEY=your_gemini_api_key_here
  # Optional model override:
  # BIZLENS_MODEL=gemini-3.7-flash
  ```

  OpenAI is also supported — set `OPENAI_API_KEY` as an environment variable instead:

  ```powershell
  $env:OPENAI_API_KEY="your-key-here"
  ```

Keys entered in the sidebar are held only for that Streamlit session and are never written to project files. Never commit a real API key to `.env`.

## Working with your own data

Supported file types: **CSV, XLSX, XLS** (structured data) and **DOCX, PDF, PPTX, TXT** (business documents). Upload from the sidebar (available on every page) or from Home.

If more than one dataset is uploaded, use the **Active dataset** selector in the sidebar to switch which one drives the Data & Insights and Investigation pages. Use **Clear workspace** to start over.

## Included demo/test evidence

Two evidence sets ship with the project:

- **`data/`** — a small built-in demo set used by the "Try the complete demo workspace" button: a demo sales CSV, meeting notes, a business review deck, and a requirements PDF.
- **`test_data/`** — the full evidence set used for testing and validation: the complete sales dataset (`BizLens_Test_Sales_Data.csv`), business requirements, a management review deck, an executive context report, Q4 meeting notes, and a customer call transcript.

## Deliverables pack

The `deliverables/` folder contains a portfolio-style, end-to-end BA artefact pack generated from the connected test evidence — 18 coordinated documents, each available as DOCX and PDF (or XLSX for tabular artefacts):

1. Executive Brief
2. Business Requirements Document (BRD)
3. Product Requirements Document (PRD)
4. Functional Requirements Document (FRD)
5. Process Specification (AS-IS/TO-BE)
6. Root Cause Analysis (RCA)
7. Data & Business Analysis Report
8. KPI Performance Review
9. Gap Analysis
10. Business Case
11. Requirements Traceability Matrix (RTM)
12. Implementation Roadmap
13. User Stories
14. Use Cases
15. UAT Scenarios
16. Stakeholder Analysis
17. RACI Matrix
18. Action Plan

Start with `01_Executive_Brief`, then `02_BRD`, `04_FRD`, `06_RCA`, `07_Data_Business_Analysis`, and `11_RTM` (see `deliverables/INDEX.md`). The whole set is also bundled as `deliverables/BizLens_Deliverables_Pack.zip`. New deliverables from your own workspace are generated from the **Studio** page.

## Testing and validation

```powershell
python -m compileall -q .
python tests\smoke_test.py
```

or run the complete suite (smoke, architecture, regression, and final BA-quality hardening tests):

```powershell
python run_tests.py
```

`TESTING_GUIDE.md` documents what the test pack validates — including that the app correctly separates fact from hypothesis, never exposes raw correlation coefficients as business explanations, surfaces evidence conflicts instead of silently resolving them, and never invents KPIs from missing fields — plus a manual acceptance checklist for reviewing the app end to end.

## Data quality philosophy

BizLens detects duplicates, missing values, inconsistent fields, and potential outliers **without silently changing the source data**. Mean/median/mode treatments are offered as conditional options, never applied automatically — a BA should validate the business meaning of the data before any imputation or deletion.

## Evidence rule (how BizLens avoids false causation)

BizLens verifies a claimed trend or decline before proposing contributors or causes. Observed patterns, operational signals, and document-derived leads are always labelled separately from proven causation, and correlation coefficients are kept out of business-facing pages entirely.

Analytical thresholds used in the Recommendations layer are explicit heuristics meant to draw attention to something worth investigating — they are **not** business-approved targets, and they never establish causation on their own. BizLens will not label a region, product, or correlation as a root cause unless the connected evidence actually supports that conclusion.

---

*Human review remains the final approval step. BizLens is a decision-support workspace, not an autonomous decision-maker.*
