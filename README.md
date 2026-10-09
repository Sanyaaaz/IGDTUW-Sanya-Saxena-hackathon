# NEXORA — Event-Driven Risk Intelligence

**Candidate Name:** Sanya Saxena
**Registered Email ID:** sanyasaxena1465@gmail.com 
**College Email ID:** sanya118bteceai23@igdtuw.ac.in
**College / Campus:** Indira Gandhi Delhi Technical University for Women
**Demo Video Link:** Add after recording  
**Slide Deck Link:** add

---


## 1. Overview

**NEXORA** converts external unstructured news events into structured risk intelligence and traces how configurable event-driven risk-factor shocks propagate through a synthetic wholesale portfolio to produce explainable, model-implied stress testing results. Designed as an analyst-facing prototype, Nexora links incoming market headlines to issuer exposures, macro sensitivities, and transmission pathways—providing transparent auditability across every calculation step without relying on black-box predictions.

---

## 2. Problem Statement

Modern enterprise risk management faces a critical gap between qualitative market intelligence and quantitative stress testing:
- **Disjointed Intelligence:** News feeds and macro events arrive continuously, but translating an unstructured headline into an actionable portfolio shock requires manual analyst interpretation.
- **Opacity & Hallucination Risk:** Generative AI solutions often synthesize ungrounded risk claims without mechanical lineage or mathematical backing.
- **Rigid Macro Scenarios:** Traditional regulatory stress scenarios (e.g., CCAR / EBA) are published periodically and cannot rapidly simulate bespoke, fast-moving real-world disruptions (such as geopolitical supply shocks or sudden monetary shifts).
- **Unverified Provenance:** Systems rarely distinguish between live external news corroboration, synthetic demonstration scenarios, and uncalibrated heuristic scores.

---

## 3. Solution

Nexora addresses this operational bottleneck by providing an end-to-end, deterministic risk pipeline:
1. **Multi-Source News Ingestion:** Pulls headlines across multiple external RSS providers with clear fetch provenance and error handling.
2. **Transparent NLP & Classification:** Identifies event types via semantic sentence embeddings (with transparent fallback rules) and extracts sentiment via FinBERT (with lexical fallback).
3. **Deterministic Entity & Factor Resolution:** Normalizes company, sector, and commodity entities against a local registry and maps events to canonical risk factors.
4. **Parametric Stress Transmission:** Converts event shocks into asset-level returns and portfolio P&L using explicit factor sensitivities and credit loss formulas.
5. **Interactive Risk Lab & Reverse Stress Testing:** Enables risk managers to inspect propagation graphs, customize shock assumptions, and solve for threshold loss triggers via bisection search.

---

## 4. Key Innovation: Event-Driven Risk Transmission Engine

The core technical innovation of Nexora is its transparent, multi-tier **Risk Transmission Engine**. Rather than relying on end-to-end black-box statistical forecasting, the engine executes an explicit, auditable chain:

$$\text{Event} \longrightarrow \text{Risk Factor} \longrightarrow \text{Sector} \longrightarrow \text{Asset} \longrightarrow \text{Portfolio}$$

### Transmission Mechanics
- **Configured Factor Shocks:** Events trigger configured shocks across macro factors (e.g., Crude Oil, Interest Rates, Credit Spreads, Supply Chain).
- **Per-Asset Sensitivities:** Each portfolio asset maintains explicit sensitivity coefficients to specific risk factors.
- **Asset Returns:**
  - **Equities & Derivatives:** Percentage factor shocks (e.g., $+25\%$ Crude Oil) are applied directly through asset sensitivity coefficients ($\Delta P = V \times \beta \times \Delta F$).
  - **Fixed Income (Bonds):** Rates and spread shocks are specified in basis points and converted using modified duration and spread duration ($\Delta P = -V \times D \times \frac{\Delta y}{10{,}000}$).
  - **Credit & Loans:** Incorporates duration repricing plus incremental expected credit loss:
    $$\Delta \text{EL} = \text{EAD} \times \left(\min(0.95, \text{PD} \times M_{\text{PD}}) - \text{PD}\right) \times \text{LGD}$$
- **Linear Additivity:** Factor impacts are aggregated linearly. The model explicitly avoids unverified non-linear interactions, correlation assumptions, or liquidity hair-cuts, ensuring every rupee of P&L can be decomposed directly to its source factor.

---

## 5. End-to-End Pipeline

```
  LIVE / SYNTHETIC EVENT
            ↓
  EVENT CLASSIFICATION (Semantic Similarity / Rule Fallback)
            ↓
  ENTITY RESOLUTION (Registry & Alias Normalization)
            ↓
  RISK FACTORS (Crude Oil, Rates, Spreads, Supply Chain, etc.)
            ↓
  RISK-FACTOR SHOCKS (Configured Baseline Multiplied by Severity)
            ↓
  ASSET SENSITIVITIES (Duration, Spread Duration, Equity Beta, Factor Coeffs)
            ↓
  ASSET IMPACT (Mark-to-Scenario Repricing + Incremental Loan Expected Loss)
            ↓
  PORTFOLIO P&L (Aggregated Baseline vs. Stressed Valuation)
            ↓
  STRESS SCENARIO (Mild / Base / Severe Scenarios & What-If Sandbox)
            ↓
  EXPLAINABILITY / PROPAGATION / REVERSE STRESS (Auditable Graphs & Factor Attribution)
```

---

## 6. Features

- **Command Center & Portfolio Overview:** Real-time visibility into portfolio exposure (₹100 Cr synthetic baseline), risk breakdown across 10 assets, HHI concentration metrics, and sentiment distribution.
- **Canonical Event Aggregation:** Clusters duplicate reports within 7-day windows using local TF cosine similarity and same-entity/event rules, strictly isolating live sources from synthetic fixtures.
- **Traceable NLP & Trust Badging:** Clear badges distinguishing `LIVE NEWS`, `SYNTHETIC`, and `FALLBACK ANALYSIS`, with explicit indicators for `FinBERT` vs. `Lexical fallback` and `semantic_similarity` vs. `rule_based_fallback`.
- **Deterministic Risk Clustering:** Groups canonical events based on shared entities, sectors, or macro risk factors over rolling 7-day windows without black-box clustering.
- **Propagation Graph:** Visualizes directional impact paths from Event $\rightarrow$ Macro Factor $\rightarrow$ Sector $\rightarrow$ Asset with per-edge calculation rationale.
- **Scenario Laboratory & What-If Sandbox:** Pre-configured stress templates and automatic event-to-scenario generators with editable factor shocks and loan default multipliers.
- **Reverse Stress Testing:** Multivariate bisection search solver determining the exact scenario vector scaling required to breach critical portfolio loss thresholds (e.g., 10% loss).
- **Indicative FX Reference:** Live USD/INR reference rate integration via Frankfurter API with offline cache resilience and currency conversion tool.

---

## 7. Architecture

Nexora is built as an explainable, modular monolith decoupling external connectors, deterministic NLP analysis, portfolio financial math, database persistence, and an interactive analyst dashboard.

```mermaid
flowchart LR
  A[RSS Feeds] --> I[Ingestion Connectors]
  B[GDELT API (Optional)] --> I
  C[Analyst Text / Synthetic Seed] --> P[Text Normalization]
  I --> P
  P --> N[Sentiment + Semantic Classifier]
  N --> E[Entity Resolution & Canonical Clustering]
  E --> R[Canonical Event & Source Provenance]
  R --> X[Exposure Mapping & Rule Propagation]
  X --> F[Risk Factor Shocks × Asset Sensitivities]
  F --> M[Severity Multipliers (Mild/Base/Severe)]
  M --> S[Portfolio Stress Engine]
  R --> DB[(SQLite / PostgreSQL)]
  S --> DB
  DB --> API[FastAPI Backend]
  API --> UI[React + Vite Dashboard]
```

Detailed architectural contracts are documented in [docs/architecture.md](file:///Users/sanya/Downloads/codetoconnect/docs/architecture.md).

---

## 8. Verified Tech Stack

The repository uses only the verified libraries and tools present in the codebase:

### Backend
- **Language & Framework:** Python 3.11+, [FastAPI](https://fastapi.tiangolo.com/) (REST APIs), [Uvicorn](https://www.uvicorn.org/) (ASGI server)
- **Validation & Schemas:** [Pydantic v2](https://docs.pydantic.dev/)
- **Data Persistence:** [SQLAlchemy 2.0](https://www.sqlalchemy.org/) with [SQLite](https://www.sqlite.org/) (default local) and [PostgreSQL](https://www.postgresql.org/) ([psycopg v3](https://www.psycopg.org/) binary, supported via Docker Compose)
- **HTTP & RSS Parsing:** [HTTPX](https://www.python-httpx.org/) (async requests), [feedparser](https://feedparser.readthedocs.io/) (RSS feed extraction)
- **Testing:** [pytest](https://docs.pytest.org/)

### NLP & AI (Local & Deterministic)
- **Sentiment Analysis:** Optional local [FinBERT](https://huggingface.co/ProsusAI/finbert) (`ProsusAI/finbert` via Hugging Face `transformers` and `torch`), with rule-based lexical fallback.
- **Semantic Classification:** Optional local sentence embeddings (`sentence-transformers/all-MiniLM-L6-v2` via `sentence-transformers`), with rule-based keyword and bag-of-words fallback.

### Frontend
- **Framework & Build:** [React 19](https://react.dev/), [TypeScript](https://www.typescriptlang.org/), [Vite](https://vite.dev/)
- **Visualizations:** [Recharts](https://recharts.org/) (responsive pie, bar, and donut charts)
- **UI & Icons:** [Lucide React](https://lucide.dev/), Vanilla CSS design system (dark analyst aesthetic)

*(Note: Technologies not present in the repository, such as LangChain, OpenAI API, Kafka, Spark, Redis, Kubernetes, or cloud deployments, are intentionally omitted).*

---

## 9. Data Sources and Provenance

Nexora enforces strict data provenance labeling at both the API and UI levels:

| Provider / Source | Type | Status / Verification | Detail |
|---|---|---|---|
| **BBC Business RSS** | External RSS | **LIVE** (Verified: 25 articles ingested) | `https://feeds.bbci.co.uk/news/business/rss.xml` |
| **NPR Business RSS** | External RSS | **LIVE** (Verified: 10 articles ingested) | `https://feeds.bbci.co.uk/news/business/rss.xml` / `https://feeds.npr.org/1006/rss.xml` |
| **The Guardian Business RSS** | External RSS | **LIVE** (Verified: 25 articles ingested) | `https://www.theguardian.com/business/rss` |
| **GDELT 2.0 API** | External News API | **LIVE / OPTIONAL** (Rate limited / 0 articles in latest fetch) | External news intelligence API; subject to HTTP 429 rate limiting; not claimed as guaranteed live stream. |
| **Frankfurter FX API** | Reference Rate API | **LIVE / INDICATIVE** (Verified: USD/INR 96.20 on 2026-10-05) | Public ECB reference rate feed (`https://api.frankfurter.dev`). Indicative reference only; no API key required; cached locally upon network failure. |
| **Synthetic Portfolio** | Internal Benchmark | **SYNTHETIC** | ₹100 Cr INR baseline across 10 diversified assets; illustrative holding assumptions. |
| **Seeded Demo Events** | Internal Benchmark | **SYNTHETIC** | Seeded historical scenarios (including the Middle East oil disruption event) for offline testing. |

### Latest System Verification State
- **Canonical Events in Database:** 67 canonical events total
  - **Live External News Events:** 58 events
  - **Synthetic Seeded Events:** 9 events
  - **Fallback Records:** 0 events
- **Independent Live Sources:** Seeded synthetic events report zero live source corroboration (`source_count = 0`), preventing synthetic fixtures from validating actual news reports.

---

## 10. AI / NLP Pipeline & Fallback Hierarchy

Nexora implements a dual-path NLP pipeline designed for stability and transparency:

```
Input News Text
    ├── Sentiment Branch
    │     ├── Primary: ProsusAI/finbert (Transformer pipeline, PyTorch)
    │     └── Fallback: Lexical keyword lexicon bounded to [-1.0, 1.0]
    │
    └── Classification Branch
          ├── Primary: sentence-transformers (all-MiniLM-L6-v2 cosine distance)
          ├── Fallback 1: Domain keyword rule heuristics
          └── Fallback 2: Bag-of-words token similarity to taxonomy definitions
```

### Critical Methodology Boundaries
- **No Calibrated Probability:** Event type and evidence confidence scores represent raw heuristic cue strength or cosine similarity (0.0 to 1.0). They are **not** statistically calibrated Bayesian probabilities.
- **No Financial Forecasting:** Semantic similarity matches taxonomy descriptions; it does not constitute a trained econometric or pricing model.
- **Model Traceability:** Every event signal explicitly reports its execution metadata (e.g., `sentiment_model: "FinBERT"`, `classification_method: "semantic_similarity"`). See [docs/model_card.md](file:///Users/sanya/Downloads/codetoconnect/docs/model_card.md).

---

## 11. Risk Transmission Methodology

The transmission engine converts high-level events into portfolio financial impact using configured assumptions:

1. **Event Classification:** Event taxonomy class maps to a baseline risk-factor shock vector defined in [data/risk_factors.json](file:///Users/sanya/Downloads/codetoconnect/data/risk_factors.json).
2. **Entity & Sector Mapping:** Normalized entities identify directly exposed issuers and indirectly exposed sector peers.
3. **Sensitivity Multiplication:**
   - For percentage factors (Crude Oil, Supply Chain, Energy Cost, Volatility):
     $$\Delta \text{Return} = \text{Sensitivity Coefficient} \times \frac{\text{Shock}_{\%}}{100}$$
   - For basis-point factors (Interest Rates, Credit Spreads):
     $$\Delta \text{Return} = \text{Sensitivity Coefficient} \times \frac{\text{Shock}_{\text{bps}}}{10{,}000}$$
4. **Loan Expected Loss Increment:**
   - Loans calculate duration repricing plus the change in Expected Loss ($\Delta \text{EL} = \text{EL}_{\text{stressed}} - \text{EL}_{\text{base}}$).
5. **Additive Assumption:** Asset impacts are summed across active factors.

> **Methodological Note:** Sensitivities and shock magnitudes are configured deterministic assumptions, not econometric estimates. The model omits second-order liquidity spirals, correlation breakdowns, and non-linear interactions. Outputs are **model-implied stress figures**, not market forecasts.

---

## 12. Stress Testing Engine

### Automatic Event-to-Scenario Generation
When an analyst selects an event, Nexora automatically generates an editable stress scenario parameterized by event severity:
- **MILD:** Multiplier $\times 0.5$ applied to underlying factor shocks and PD increments.
- **BASE:** Multiplier $\times 1.0$ (baseline calibrated event shock).
- **SEVERE:** Multiplier $\times 1.6$ applied to underlying factor shocks and PD increments.

### Synthetic Demonstration Event: "Major Middle East oil supply disruption"
*(Explicitly labeled as a SYNTHETIC DEMO EVENT)*

#### Configured Base Shocks:
- `CRUDE_OIL`: $+25\%$
- `INFLATION`: $+0.8\%$
- `INTEREST_RATES`: $+40\text{ bps}$
- `CREDIT_SPREADS`: $+75\text{ bps}$
- `EQUITY_VOLATILITY`: $+15\%$
- `SUPPLY_CHAIN`: $+12\%$
- `ENERGY_COST`: $+18\%$

#### Verified Stress Testing Results (₹100 Cr Baseline):

| Severity | Portfolio Loss (INR) | Portfolio Loss (%) | Stressed Portfolio Value |
|---|---|---|---|
| **Mild** | **₹1.422 Cr** | **1.422%** | ₹98.58 Cr |
| **Base** | **₹2.843 Cr** | **2.843%** | **₹97.16 Cr** |
| **Severe** | **₹4.549 Cr** | **4.549%** | ₹95.45 Cr |

---

## 13. Calculation Examples

To demonstrate the deterministic mechanics, consider two key asset repricing calculations under the **Base** scenario:

### 1. Airline Corp Equity (Asset ID: `A-109`)
- **Holding Value:** ₹6.5 Cr ($65{,}000{,}000\text{ INR}$)
- **Configured Sensitivities:** Crude Oil: $-0.80$, Supply Chain: $-0.20$
- **Factor Shocks:** Crude Oil: $+25\%$, Supply Chain: $+12\%$
- **Factor Returns:**
  - Crude Oil: $-0.80 \times 25\% = -20.0\%$
  - Supply Chain: $-0.20 \times 12\% = -2.4\%$
  - **Combined Return:** $-22.4\%$
- **Model-Implied P&L:**
  $$\text{P&L} = ₹6.5\text{ Cr} \times (-22.4\%) \approx -\mathbf{₹1.456\text{ Cr}}$$

### 2. Long Duration Bond Fund (Asset ID: `A-110`)
- **Holding Value:** ₹8.5 Cr ($85{,}000{,}000\text{ INR}$)
- **Configured Sensitivities:** Interest Rates Duration: $-9.0$, Credit Spread Duration: $-4.0$
- **Factor Shocks:** Interest Rates: $+40\text{ bps}$, Credit Spreads: $+75\text{ bps}$
- **Factor Returns:**
  - Interest Rates: $-9.0 \times \frac{40}{10{,}000} = -3.6\%$
  - Credit Spreads: $-4.0 \times \frac{75}{10{,}000} = -3.0\%$
  - **Combined Return:** $-6.6\%$
- **Model-Implied P&L:**
  $$\text{P&L} = ₹8.5\text{ Cr} \times (-6.6\%) \approx -\mathbf{₹56.10\text{ L}}\quad (-₹56{,}10{,}000\text{ INR})$$

---

## 14. Reverse Stress Testing

Reverse stress testing determines the macro shock magnitude necessary to breach a specified portfolio loss threshold.

### Mechanics: Model-Implied Multivariate Scenario Scaling
- Implemented via a 45-iteration **bisection search**.
- Rather than optimizing an arbitrary single factor in isolation, the algorithm scales the complete multi-factor scenario vector $\mathbf{F}_{\text{scaled}} = k \cdot \mathbf{F}_{\text{base}}$ until the requested loss target is achieved.

### Verified Demo Run:
- **Target Loss Threshold:** $10.0\%$ portfolio loss (₹10.0 Cr)
- **Required Scenario Scaling:** $\approx \mathbf{3.5169\times}$ base factor vector
- **Implied Oil Shock:** $\approx \mathbf{+87.9\%}$ ($25\% \times 3.5169$)
- **Implied PD Multiplier:** $\approx \mathbf{\times 2.76}$

> **Important Terminology:** This calculation represents **model-implied multivariate scenario scaling**. It is **not** a single-factor minimum, an economically optimal equilibrium shock, or a calibrated historical likelihood.

---

## 15. Explainability & Provenance Architecture

Explainability in Nexora is grounded in mathematical and evidence-based lineage rather than opaque LLM prose:

- **Source Provenance:** Shows publishing domain, ingestion timestamp, and independent corroboration count.
- **Method Badging:** Distinguishes whether FinBERT or lexical rules produced sentiment, and whether embeddings or keyword matches produced classification.
- **Factor Transmission Attribution:** Decomposes asset gains and losses to individual risk factor sensitivities.
- **Propagation Graph:** Explicitly maps:
  $$\text{Event Node} \longrightarrow \text{Macro Factor Node} \longrightarrow \text{Sector Node} \longrightarrow \text{Asset Node}$$
  Each edge displays qualitative rationale and transmission direction (e.g., showing mixed positive/negative asset returns under the same macro shock).
- **"Why This Matters":** Formulates deterministic analyst briefing cards detailing top single-factor contributors and total scenario loss.

---

## 16. Synthetic vs. Live Data Boundaries

| Dimension | Live Implementation | Synthetic / Mock Implementation | Model-Inferred / Rule-Based |
|---|---|---|---|
| **News Headlines** | External RSS feeds (BBC, NPR, Guardian) | Seeded demonstration stories, sample social media fixtures | — |
| **FX Rates** | Frankfurter ECB reference rate | Offline fallback cached rate if API is unreachable | Indicative conversion calculations |
| **Portfolio Book** | — | ₹100 Cr wholesale book across 10 synthetic assets | Exposure calculations, HHI concentration |
| **Risk Factors** | — | — | Shocks, sensitivities, P&L, scenario losses |
| **Causality / Graphs** | — | — | Deterministic rule propagation; not learned causal graphs |

---

## 17. Project Structure

```
codetoconnect/
├── README.md                           # Master project documentation
├── docker-compose.yml                  # Docker Compose configuration (FastAPI + PostgreSQL + React)
├── LICENSE                             # MIT License
├── .env.example                        # Template environment configuration
├── finrisk.sqlite3                     # Local SQLite database (auto-created and seeded)
├── backend/
│   ├── app/
│   │   ├── main.py                     # FastAPI application, route handlers, and lifespan hooks
│   │   ├── schemas.py                  # Pydantic request/response data contracts
│   │   ├── core/
│   │   │   └── config.py               # Environment configuration and paths
│   │   ├── database/
│   │   │   ├── models.py               # SQLAlchemy ORM models (RiskSignal, StressRun, FXRate)
│   │   │   └── session.py              # Engine creation and session dependency
│   │   ├── ingestion/
│   │   │   └── connectors.py           # RSS and GDELT async ingestion connectors
│   │   ├── nlp/
│   │   │   └── analyzer.py             # FinBERT, semantic similarity, and rule-based fallbacks
│   │   ├── services/
│   │   │   ├── demo_data.py            # Synthetic portfolio and demo event fixtures
│   │   │   └── event_intelligence.py   # Canonical clustering, propagation, and scenario generation
│   │   └── stress_testing/
│   │       └── engine.py               # Portfolio assets, factor repricing, and stress math
│   ├── tests/
│   │   ├── conftest.py                 # Pytest test client fixtures
│   │   ├── test_api.py                 # API integration and route verification tests
│   │   ├── test_event_intelligence.py  # Clustering, propagation, and mapping tests
│   │   └── test_risk_engine.py         # Financial repricing and calculation tests
│   ├── requirements.txt                # Core backend dependencies
│   ├── requirements-ml.txt             # Optional local ML packages (torch, transformers)
│   ├── Dockerfile                      # Backend container definition
│   └── pytest.ini                      # Pytest runner configuration
├── frontend/
│   ├── src/
│   │   ├── App.tsx                     # Main React analyst dashboard and view routing
│   │   ├── main.tsx                    # React application entry point
│   │   ├── styles.css                  # Custom responsive dark analyst stylesheet
│   │   ├── api/
│   │   │   └── client.ts               # Typed API client for FastAPI endpoints
│   │   └── types/
│   │       └── index.ts                # TypeScript domain models and interfaces
│   ├── package.json                    # Frontend dependencies and scripts
│   ├── vite.config.ts                  # Vite build and dev-server configuration
│   └── index.html                      # Single-page application template
├── data/
│   ├── entity_registry.json            # Entities, aliases, and sector classifications
│   ├── event_scenario_mappings.json    # Event-to-scenario mapping rules
│   ├── propagation_rules.json          # Propagation graph traversal templates
│   ├── risk_factors.json               # Factor definitions, asset sensitivities, base shocks
│   ├── risk_rules.json                 # Clustering and impact score adjustment weights
│   └── rss_feeds.json                  # Configured public RSS feed endpoints
└── docs/
    ├── architecture.md                 # System architecture and scaling design
    ├── data_dictionary.md              # Complete schema field reference
    ├── demo_script.md                  # Step-by-step judge demonstration guide
    ├── model_card.md                   # Machine learning and heuristic limitations
    └── presentation-v2.pptx            # Slide deck
```

---

## 18. Quickstart & Installation

### Prerequisites
- Python 3.11+
- Node.js 20+
- npm 9+

### 1. Environment Configuration
Copy the template configuration file:
```bash
cp .env.example .env
```

*(Default settings run in standalone demo mode with local SQLite and auto-detected FinBERT/sentence embeddings).*

---

## 19. Running the Backend

From the repository root:

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install core dependencies
pip install -r backend/requirements.txt

# (Optional) Install ML packages for local FinBERT and sentence transformers:
# pip install -r backend/requirements-ml.txt

# Run FastAPI backend
cd backend
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- API Base URL: `http://127.0.0.1:8000`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`

---

## 20. Running the Frontend

In a second terminal window:

```bash
cd frontend
npm install
npm run dev
```

- Web Dashboard: `http://127.0.0.1:5173`

---

## 21. Docker Compose (Alternative)

To run the complete system with PostgreSQL:

```bash
docker compose up --build
```
- Dashboard: `http://localhost:5173`
- Backend API Docs: `http://localhost:8000/docs`

---

## 22. API Overview

All routes are fully implemented and verified in [backend/app/main.py](file:///Users/sanya/Downloads/codetoconnect/backend/app/main.py):

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service liveness probe and operation mode |
| `GET` | `/api/status` | Database connectivity, provider health, NLP states |
| `GET` | `/api/sources/status` | Detailed provider ingestion status, timestamps, and error logs |
| `GET` | `/api/dashboard/summary` | Consolidated dashboard overview: event counts, sentiment, allocations |
| `GET` | `/api/events` | List canonical event clusters with search and taxonomy filters |
| `GET` | `/api/events/{event_id}` | Retrieve individual canonical event detail and evidence |
| `POST` | `/api/events/analyze` | Ingest analyst-submitted custom text through full NLP pipeline |
| `GET` | `/api/events/{event_id}/exposure` | Retrieve mapped portfolio asset exposures for an event |
| `GET` | `/api/events/{event_id}/propagation` | Generate rule-based transmission graph (Event $\rightarrow$ Factor $\rightarrow$ Sector $\rightarrow$ Asset) |
| `GET` | `/api/events/{event_id}/stress` | Preview mild/base/severe stress testing P&L for an event |
| `POST` | `/api/events/{event_id}/generate-scenario` | Generate editable scenario assumption template from event |
| `POST` | `/api/ingest` | Trigger manual refresh across configured RSS and GDELT connectors |
| `GET` | `/api/portfolio` | Retrieve synthetic portfolio holdings, duration, PD/LGD, and allocation |
| `GET` | `/api/portfolio/exposure` | Retrieve top portfolio asset vulnerabilities mapped to active events |
| `GET` | `/api/fx/usd-inr` | Retrieve indicative USD/INR daily reference rate via Frankfurter API |
| `GET` | `/api/scenarios` | List pre-configured benchmark macro scenarios |
| `POST` | `/api/stress-tests` | Execute pre-configured scenario run and log to history |
| `GET` | `/api/stress-tests` | Retrieve historical stress test run records |
| `POST` | `/api/stress-test` | Execute custom What-If scenario with user-adjusted shocks |
| `POST` | `/api/reverse-stress-test` | Calculate model-implied scenario scaling for target portfolio loss |
| `GET` | `/api/risk/alerts` | Filter events breaching critical impact and confidence thresholds |
| `GET` | `/api/risk/overview` | Current-window risk summary and highest-impact events |
| `GET` | `/api/risk/clusters` | Deterministic 7-day multi-event clusters grouped by entity, sector, or factor |

---

## 23. Testing & Verification

The test suite validates API contracts, risk math, event clustering, and transmission mechanics:

### Backend Tests
```bash
cd backend
pytest -q
```
**Verified Result:**
```
.........................                                                [100%]
25 passed, 1 warning in 17.43s
```
*(Note: One standard Starlette/httpx deprecation warning is present in testclient imports; all 25 tests pass completely).*

### Frontend Production Build
```bash
cd frontend
npm run build
```
**Verified Result:**
```
✓ built in 342ms
dist/index.html                   0.42 kB
dist/assets/index-Dea4ct4N.css   32.80 kB
dist/assets/index-DgpSmqN-.js   671.22 kB
```
*(Note: Vite issues a standard optimization advisory regarding bundle chunk size exceeding 500 kB minified due to Recharts and Lucide icon sets; production bundle compiles without error).*

---

## 24. Limitations & Responsible-Use Notes

1. **Synthetic Portfolio:** All 10 portfolio assets are synthetic educational representations; they do not reflect actual trading positions or proprietary holdings.
2. **Deterministic Stress Assumptions:** Risk factor shocks and asset sensitivities are configurable assumptions. They do **not** reflect econometric backtesting or regulatory-approved capital models (e.g., Basel III / FRTB).
3. **Linear Repricing:** Repricing formulas use linear duration approximations and scalar sensitivities. Interaction effects, volatility skew, and liquidity dry-ups are omitted.
4. **NLP & Lexical Boundaries:** Keyword and embedding rules can miss subtle sarcasm, linguistic negations, and complex multi-entity ownership hierarchies.
5. **Heuristic Confidence:** Evidence confidence scores represent source corroboration heuristics, not calibrated probabilities.
6. **No Investment Advice:** Outputs are strictly educational and illustrative prototypes; they must never be construed as investment, credit, legal, or accounting advice.

---

## 25. Recommended Demo Flow (3-Minute Judge Script)

See [docs/demo_script.md](file:///Users/sanya/Downloads/codetoconnect/docs/demo_script.md) for full timing notes:

1. **Step 1: Portfolio Overview (`/`)**
   - Review the ₹100 Cr baseline wholesale portfolio and 10 asset holdings.
   - Point out the emerging event clusters and note the `NO LONG-RUN BASELINE` badge (current-window only).
2. **Step 2: Event Intelligence & Auditability (`/events`)**
   - Open the seeded demonstration event: **"Major Middle East oil supply disruption"**.
   - Show that data status is explicitly marked `SYNTHETIC` with `0 independent sources`.
   - Inspect the verified NLP metadata: FinBERT sentiment, semantic classification, normalized entities, and mapped factor shocks.
3. **Step 3: Risk Propagation Graph**
   - Click to inspect the propagation chain: Event $\rightarrow$ Crude Oil ($+25\%$) $\rightarrow$ Transportation / Fixed Income $\rightarrow$ Assets.
   - Show how Airline Corp loses ($-22.4\%$) while Energy Index Swaps gain ($+18.75\%$).
4. **Step 4: Scenario Laboratory & Stress Testing (`/stress`)**
   - Select **Generate editable stress scenario** to load the model-implied template.
   - Run the **What-If** calculation: view the resulting ₹2.843 Cr ($2.843\%$) Base loss and ₹97.16 Cr stressed valuation.
5. **Step 5: Reverse Stress Testing**
   - Set target loss to **10%** and click **Find model-implied threshold**.
   - Demonstrate the bisection solver reaching $10.0\%$ loss at $\approx 3.52\times$ scenario scaling (implied oil shock $\approx +87.9\%$).
6. **Step 6: Data & Model Provenance (`/status`)**
   - Open the status dashboard showing live provider fetch states (BBC, NPR, Guardian) and the indicative Frankfurter USD/INR reference rate.

---

## 26. Future Improvements

- **Persistent Event Store & Incremental Clustering:** Implement database-level incremental clustering with graph-based entity resolution across multi-month historical windows.
- **Non-Linear Factor Interaction:** Introduce non-linear copula correlations and liquidity-adjusted stress haircuts.
- **Authenticated Broker / Custody Integrations:** Connect live portfolio accounting via FIX/SWIFT protocol connectors.
- **Analyst Override Ledger:** Add audit logging and approval workflows for human analysts overriding NLP classifications or model sensitivities.

---

## 27. License & Acknowledgements

- **License:** Distributed under the MIT License. See [LICENSE](file:///Users/sanya/Downloads/codetoconnect/LICENSE) for details.
- **Data & Model Attributions:**
  - Sentiment inference powered by [ProsusAI/finbert](https://huggingface.co/ProsusAI/finbert).
  - Sentence embeddings powered by [sentence-transformers/all-MiniLM-L6-v2](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).
  - Indicative FX reference rates provided by the [Frankfurter API](https://api.frankfurter.dev) (European Central Bank data).
  - External news RSS feeds provided by BBC, NPR, and The Guardian.
