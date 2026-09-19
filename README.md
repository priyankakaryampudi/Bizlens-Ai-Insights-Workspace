# BizLens

**BizLens — AI-Assisted Business Analysis Workspace**

BizLens is a Streamlit application that turns raw business evidence — sales data, requirements docs, meeting notes, management reviews, call transcripts — into a connected workspace that helps a Business Analyst move from "something changed" to a management-ready decision pack.

It is built to demonstrate BA reasoning, not just AI output. The workflow deliberately mirrors how a real BA works a problem:

- **Home** is orientation only: workspace snapshot, objective, current signal, next action and workflow progress.
- **Business Context** focuses on business meaning: objective, pain points, requirements, stakeholders, decisions, risks and evidence gaps.
- **Data & Insights** is the numeric layer: KPIs, charts, concentration, operational signals and data quality.
- **Investigation** is the reasoning layer: evidence, hypotheses, validation plans, candidate signals and root-cause status.
- **Recommendations** is the decision layer: actions, owners, dependencies, success measures and decision guardrails.
- **Studio** remains the formal BA deliverable layer with the existing 18 artefacts.

The key design principle is: **Home summarizes → Context frames → Data measures → Investigation explains → Recommendations act → Studio documents.**

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
- **Works with zero AI configuration.** All calculations, charts, profiling, and evidence answers run on a deterministic local Python engine. AI (Gemini or OpenAI) is optional and only used for natural-language synthesis, never for the underlying numbers.
- **No silent data changes.** BizLens detects duplicates, missing values, inconsistent fields, and outliers, and surfaces them in a separate Data Quality area. It never imputes or deletes automatically, a BA validates the business meaning first.
- **Correlation is not causation.** Automatic correlation coefficients are computed internally but are kept out of business-facing pages; the app talks in observed patterns and validated hypotheses instead of "r = 0.xx" style statistics.
- **Traceability across deliverables.** BRD, FRD, User Stories, UAT scenarios, and the RTM share requirement IDs, so a requirement can be traced end-to-end through the deliverable pack.
- **Unconfirmed ownership is never invented.** If a stakeholder owner isn't established by the evidence, it's labelled "for confirmation" rather than guessed.

## How the workspace is organized

The app's navigation follows the BA workflow, grouped into five stages:

| Group | Page | Purpose |
|---|---|---|
| **Workspace** | Home | Connect evidence (upload or try the demo workspace); shows the executive answer, what changed, and the current solution direction. |
| | Ask BizLens | Free-text Q&A, routed to local evidence or AI synthesis depending on the question type. |
| **Understand** | Data & Insights | Auto-built executive dashboard from the active dataset: KPIs, charts, and a separate Data Quality panel. |
| | Business Context | The BA view of the problem: extracted requirements, business evidence, and decisions still needed. |
| **Investigate** | Investigation | Where the change is concentrated, what business drivers move with it, and what's still unproven. |
| **Decide** | Recommendations | The consolidated recommended solution path, evidence, action, owner, success measure, and decision boundary. |
| **Deliver** | Studio | Generates the professional BA deliverables (DOCX/PDF/XLSX) from the connected workspace. |

Evidence you upload from any page stays connected across every other page, you build the workspace once.

## Project structure

```text
BizLens/
├── app.py                     # Streamlit entry point, page routing, sidebar (uploads + AI key)
├── run_bizlens.bat            # Windows one-click setup + launch
├── run_tests.py               # Runs the full test suite
├── requirements.txt
├── VERSION.txt
├── TESTING_GUIDE.md           # Manual + automated acceptance checklist
├── .env.example               # Template for an optional Gemini API key
├── .streamlit/config.toml

├── pages/                     # One Streamlit page per workflow stage
│   ├── home.py
│   ├── 1_Ask.py
│   ├── 2_Data.py
│   ├── 3_Investigation.py
│   ├── 5_Documents.py
│   ├── 6_Recommendations.py
│   └── 7_Deliverables.py

├── src/                       # Application logic
│   ├── ingest.py              # File upload handling / parsing entry point
│   ├── doc_intel.py           # Extracts business signals from documents
│   ├── analytics.py           # KPI detection, metric/dimension guessing, dashboards
│   ├── intelligence.py        # Evidence graph, investigation briefs, recommendations engine
│   ├── workspace_intelligence.py # Workspace-level context building, technique selection
│   ├── workspace.py           # Shared workspace state backbone used by all pages
│   ├── evidence.py            # Central Evidence Object model (fact/hypothesis/signal tracking)
│   ├── recommendations.py     # Decision recommendation logic
│   ├── process_intel.py       # AS-IS/TO-BE process modeling
│   ├── diagrams.py            # Graphviz-based flowchart rendering for process specs
│   ├── reports.py             # DOCX/PDF generation for deliverables
│   ├── studio.py              # Deliverables Studio section definitions
│   ├── dashboard_export.py    # Self-contained HTML dashboard export
│   ├── ai.py                  # AI routing (Gemini/OpenAI), question classification
│   ├── state.py               # Session state initialization
│   ├── styles.py              # CSS injection, branding, UI components
│   └── ui.py                  # Shared UI helpers (uploads, workspace clearing)

├── data/                      # Small built-in demo dataset + documents ("Try the demo workspace")
├── test_data/                 # Full test evidence set (sales data + supporting documents)
├── tests/                     # Automated tests (smoke, regression, architecture, hardening)

└── deliverables/              # Pre-generated example output pack (18 BA artefacts, DOCX + PDF/XLSX)
    ├── README.md / INDEX.md
    └── BizLens_Deliverables_Pack.zip