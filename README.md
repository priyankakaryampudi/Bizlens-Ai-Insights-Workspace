


BizLens
AI-Assisted Business Analysis Workspace
BizLens is a Streamlit application that connects business data, documents, investigation, recommendations, and professional BA deliverables in one workspace.

Instead of stopping at "what happened?", BizLens helps move from:

What changed → Where to investigate → What needs validation → What action can be taken

Why BizLens?
Business analysis often involves working across multiple sources:

Sales and operational data

Requirements documents

Meeting notes

Management reviews

Customer or support information

KPI reports

BizLens brings these sources together into one connected workflow, allowing analysis, investigation, recommendations, and deliverables to work from the same business evidence.

Screenshots
Workspace

Data & Insights

Investigation

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
The workflow follows a practical Business Analysis approach:

Business problem → Quantified change → Investigation → Validation → Business impact → Action → Deliverable

Key Features
Evidence Workspace
Connect business datasets and supporting documents in one workspace.

Supported formats:
CSV · XLSX · XLS · DOCX · PDF · PPTX · TXT

Data & Insights
KPI analysis

Trend analysis

Business dimension analysis

Interactive visualizations

Data profiling

Data quality checks

Business Context
Organize:

Requirements

Business evidence

Decisions

Open questions

Stakeholder context

Investigation
Explore:

Where changes are concentrated

Possible contributing signals

Operational patterns

Areas requiring further validation

Recommendations
Turn findings into an actionable path containing:

Supporting evidence

Proposed action

Owner

Success measure

Validation requirements

Ask BizLens
Ask questions about the connected workspace using natural language.

Example questions:

Why did revenue change?

Which region requires attention?

What are the key business requirements?

What information still needs validation?
Deliverables Studio
Generate structured Business Analysis deliverables from the connected workspace.

Core Principles
Evidence Before Assumptions
Observed evidence is kept separate from assumptions and hypotheses.

Analysis Before Conclusions
Business patterns are identified before recommendations are generated.

Validation Before Root Cause
A contributing signal is not automatically treated as a confirmed root cause.

No Silent Data Changes
Potential data quality issues are surfaced instead of silently changing the source data.

Traceability
Requirements and findings can be carried through into downstream BA deliverables.

BA Deliverables
BizLens supports a structured deliverable pack including:

#	Deliverable
01	Executive Brief
02	Business Requirements Document
03	Product Requirements Document
04	Functional Requirements Document
05	AS-IS / TO-BE Process Specification
06	Root Cause Analysis
07	Data & Business Analysis Report
08	KPI Performance Review
09	Gap Analysis
10	Business Case
11	Requirements Traceability Matrix
12	Implementation Roadmap
13	User Stories
14	Use Cases
15	UAT Scenarios
16	Stakeholder Analysis
17	RACI Matrix
18	Action Plan
Tech Stack
Area	Technology
Application	Streamlit
Language	Python
Data Analysis	Pandas, NumPy
Visualization	Plotly
Spreadsheet Processing	OpenPyXL, XLRD
Document Parsing	python-docx, pypdf, pdfplumber, python-pptx
Report Generation	ReportLab, python-docx
Diagrams	Graphviz
Optional AI	Google Gemini, OpenAI
Configuration	python-dotenv
Project Structure
BizLens/
│
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
│   └── investigation.png
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
Requirements
Python 3.13

Windows / VS Code recommended

Create a virtual environment:

py -3.13 -m venv .venv
Activate it:

.\.venv\Scripts\Activate.ps1
Install dependencies:

python -m pip install -r requirements.txt
Running BizLens
Start the application:

python -m streamlit run app.py
Or use the Windows launcher:

run_bizlens.bat
Once launched, upload your own business evidence or use the included demo workspace.

Optional AI Configuration
BizLens can run without an AI API key.

Core calculations, profiling, charts, data quality checks, and structured analysis are handled locally.

AI is optional and can be used for natural-language synthesis.

Gemini
Create a .env file:

GEMINI_API_KEY=your_api_key_here
OpenAI
$env:OPENAI_API_KEY="your-api-key"
Never commit real API keys to the repository.

Working With Your Data
Upload structured datasets and supporting business documents through the application.

Multiple datasets can be connected to the workspace, with an active dataset selected for analysis.

The connected evidence remains available across the different stages of the workflow.

Testing
Run the basic validation:

python -m compileall -q .
python tests\smoke_test.py
Run the complete test suite:

python run_tests.py
Data Quality
BizLens identifies potential:

Missing values

Duplicate records

Inconsistent fields

Potential outliers

Other data quality issues

The source data is not silently modified. Any imputation, deletion, or treatment should be reviewed against the business context.

Project Status
Version: 4.5.0

BizLens is a portfolio project demonstrating how business evidence can be connected to structured analysis, investigation, recommendations, and professional Business Analysis documentation.

Author
Priyanka Karyampudi

GitHub Repository

Evidence before assumptions. Analysis before conclusions. Validation before action.
