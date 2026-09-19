BizLens

BizLens — AI-Assisted Business Analysis Workspace

BizLens is a Streamlit application that connects business data, documents, investigation, recommendations, and professional BA deliverables in one workspace.

Instead of stopping at “what happened?”, BizLens helps move from:

What changed → Where to investigate → What needs validation → What action can be taken

Screenshots
Workspace Overview

BizLens Workspace

Data & Insights

Data and Insights Dashboard

Investigation

Investigation Workspace

Deliverables Studio

Deliverables Studio

Why BizLens?

Business analysis often requires working with different types of evidence:

Sales and operational datasets

Requirements documents

Meeting notes

Management reviews

Customer or support transcripts

Process observations

KPI reports

These sources are usually handled separately. BizLens brings them together so that analysis, investigation, recommendations, and deliverables are based on the same connected evidence.

What BizLens Does

BizLens helps a Business Analyst:

Understand the business context.

Quantify what changed.

Identify where the change is concentrated.

Investigate possible contributing signals.

Separate facts from hypotheses.

Identify what needs further validation.

Define actions, owners, and success measures.

Generate structured BA deliverables.

The application can also answer questions about uploaded data and documents using local analysis and optional AI-assisted synthesis.

Key Features

Evidence Workspace Connect datasets and business documents in one workspace.

Data & Insights Profile data, calculate KPIs, identify trends, and explore business dimensions.

Business Context Extract requirements, decisions, business concerns, and supporting evidence from documents.

Investigation Explore where changes are concentrated and identify possible contributing signals.

Recommendations Convert findings into an action path with evidence, owners, validation needs, and success measures.

Ask BizLens Ask questions about connected datasets and documents using natural language.

Deliverables Studio Generate structured BA documents from the same workspace.

Data Quality Checks Identify missing values, duplicates, inconsistent fields, and potential outliers.

How It Works
Business Evidence
       ↓
Understand
       ↓
Measure
       ↓
Investigate
       ↓
Validate
       ↓
Decide
       ↓
Deliver

The workflow follows a practical Business Analysis process:

Business problem → Quantified change → Investigation → Validation → Business impact → Action → Deliverable

Workspace

Area

	

Purpose




Home

	

Connect evidence and understand the overall business problem




Ask BizLens

	

Ask questions about connected data and documents




Data & Insights

	

KPIs, trends, charts, and data quality checks




Business Context

	

Requirements, business evidence, and open decisions




Investigation

	

Explore patterns, contributing signals, and validation needs




Recommendations

	

Define an actionable solution path




Studio

	

Generate structured BA deliverables

Supported file types:

CSV

XLSX

XLS

DOCX

PDF

PPTX

TXT

Core Principles

Evidence before assumptions

Facts are separated from hypotheses

Correlation is not treated as causation

Underlying numbers are calculated locally

Source data is not silently modified

Requirements remain traceable across deliverables

Unknown ownership is marked for confirmation

Human review remains part of the decision process

Deliverables

BizLens supports a structured BA deliverable pack including:

Executive Brief

Business Requirements Document

Product Requirements Document

Functional Requirements Document

AS-IS / TO-BE Process Specification

Root Cause Analysis

Data & Business Analysis Report

KPI Performance Review

Gap Analysis

Business Case

Requirements Traceability Matrix

Implementation Roadmap

User Stories

Use Cases

UAT Scenarios

Stakeholder Analysis

RACI Matrix

Action Plan

These deliverables can be generated through the Studio page using the connected workspace evidence.

Tech Stack

Area

	

Technology




Application

	

Streamlit




Language

	

Python




Data Analysis

	

Pandas, NumPy




Visualizations

	

Plotly




Spreadsheet Processing

	

OpenPyXL, XLRD




Document Parsing

	

python-docx, pypdf, pdfplumber, python-pptx




Report Generation

	

ReportLab, python-docx




Diagrams

	

Graphviz




Optional AI

	

Google Gemini, OpenAI




Configuration

	

python-dotenv

Project Structure
BizLens/
├── app.py
├── run_bizlens.bat
├── run_tests.py
├── requirements.txt
├── VERSION.txt
├── TESTING_GUIDE.md
├── .env.example
│
├── screenshots/
│   ├── home.png
│   ├── data-insights.png
│   ├── investigation.png
│   └── studio.png
│
├── pages/
│   ├── home.py
│   ├── 1_Ask.py
│   ├── 2_Data.py
│   ├── 3_Investigation.py
│   ├── 5_Documents.py
│   ├── 6_Recommendations.py
│   └── 7_Deliverables.py
│
├── src/
│   ├── ingest.py
│   ├── doc_intel.py
│   ├── analytics.py
│   ├── intelligence.py
│   ├── workspace.py
│   ├── evidence.py
│   ├── recommendations.py
│   ├── process_intel.py
│   ├── reports.py
│   ├── ai.py
│   ├── state.py
│   ├── styles.py
│   └── ui.py
│
├── data/
├── test_data/
├── tests/
└── deliverables/
Installation

Requirements: Python 3.13

py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Running BizLens
python -m streamlit run app.py

Or on Windows, run:

run_bizlens.bat

After launching, either upload your own evidence or use the included demo workspace.

Optional AI Configuration

BizLens works without an AI API key.

Local Python handles:

Data profiling

KPI calculations

Charts

Evidence extraction

Data quality checks

Structured analysis

AI is optional and is used for natural-language synthesis.

Gemini

Create a .env file:

GEMINI_API_KEY=your_api_key_here
OpenAI
$env:OPENAI_API_KEY="your-api-key"

Never commit real API keys to the repository.

Working With Your Data

Upload structured data and supporting business documents through the application.

If multiple datasets are uploaded, the active dataset can be selected from the workspace. Evidence remains connected across the different analysis stages.

Testing

Run the basic validation:

python -m compileall -q .
python tests\smoke_test.py

Or run the complete test suite:

python run_tests.py
Data Quality

BizLens identifies potential:

Missing values

Duplicate records

Inconsistent fields

Potential outliers

Data quality issues

The application does not silently modify source data. Any imputation, deletion, or treatment should be reviewed against the business context.

Evidence Principle

A signal is not automatically a root cause.

BizLens keeps observed trends, calculated metrics, document evidence, and hypotheses separate. It helps identify what should be investigated without presenting an unvalidated explanation as a confirmed cause.

Project Status

Version: 4.5.0

BizLens is a decision-support workspace designed to support structured analysis, investigation, recommendations, and professional Business Analysis documentation.
