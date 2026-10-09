# Data dictionary

## Risk signal

| Field | Meaning |
|---|---|
| `id` | Stable generated signal identifier |
| `title`, `text` | Headline and original evidence text |
| `source`, `source_url` | Publisher label and original URL when available |
| `published_at`, `ingested_at` | Event publication and platform ingestion times |
| `entity`, `ticker`, `sector` | Resolved primary entity (or explicit unresolved value) |
| `event_type` | Configured event taxonomy class |
| `event_type_confidence`, `classification_evidence` | Deterministic keyword/similarity evidence strength and the matched cues; not calibrated probabilities |
| `sentiment` | Lexical score bounded to [-1, 1] |
| `impact` | Heuristic prioritization score, 1–10 |
| `confidence` | Uncalibrated rule-based confidence indicator |
| `corroboration` | Distinct independently fetched external publisher count; synthetic and analyst-entered items do not add corroboration |
| `data_status` | `LIVE` only for a successful provider response; `SYNTHETIC` for bundled fixtures; `FALLBACK` for analyst entries or records without verified fetch provenance |
| `source_status` | `LIVE`, `FAILED` or `NOT_CONFIGURED` provenance state |
| `risk_factor_shocks` | Editable rule-derived stress assumptions in percent or basis points; not predictions |
| `model_label`, `explanation` | Method provenance and score rationale |

## Portfolio asset

Assets use `value` as INR exposure, `duration` and `spread_duration` as approximate sensitivities, `pd` as baseline probability of default, `lgd` as loss given default, and `equity_beta` as a simple market proxy. All bundled portfolio rows are synthetic.
