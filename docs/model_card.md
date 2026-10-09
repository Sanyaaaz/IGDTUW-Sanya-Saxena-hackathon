# Model card: Nexora prototype

## Intended use

Demonstrate a transparent news-to-risk-to-stress workflow for education and analyst-tool prototyping. It is not an investment recommendation, production credit decision, accounting result or regulatory capital model.

## Current method

The offline implementation uses a small, inspectable keyword lexicon as the sentiment fallback. When its optional model runtime and weights are available, event classification uses local sentence embeddings against event descriptions; otherwise it falls back to explicit keyword rules and then token similarity. Confidence values are uncalibrated similarity or cue-strength indicators. Optional FinBERT performs sentiment inference only. Local TF cosine plus a same-entity/event-class rule clusters reports within verified source families. The entity registry normalizes a limited list of companies, countries, sectors, commodities and macro aliases; unknown entities remain unresolved. Source confidence is calculated separately from configured source weight, independent-source diversity and recency; only reports ingested through a successful provider fetch count as live corroboration.

Exposure maps event entities and event-relevant risk factors to configured synthetic asset sensitivities. Scenario shocks vary by mild/base/severe setting and produce model-implied stress P&L using factor sensitivities plus approximate loan expected-loss changes. This is a transparent deterministic transmission model, not a predictive or calibrated return model.

The impact score is a 1–10 prioritization heuristic. It is not a probability of default, expected loss forecast or calibrated market move. Confidence is a rule-based evidence-strength indication and has not been statistically calibrated. Source weights are configurable heuristics, not truth ratings.

## Data and evaluation

Bundled news and social examples are synthetic or illustrative. There is no ground-truth labeled corpus in this repository, so precision, recall, F1 and impact MAE are not reported. Evaluation should use a separately labeled, time-split and provenance-documented dataset, reviewed labels, entity-resolution audit samples and source-aware duplicate checks.

## Limitations and safeguards

- Lexical cues miss context, negation, sarcasm, multilingual nuance and domain-specific phrasing.
- The clusterer does not persist cluster lineage, understand every paraphrase or reliably distinguish separate events involving the same entity and class.
- Entity mapping only covers the configured registry and does not infer corporate ownership graphs.
- Exposure links, factor sensitivities and propagation chains are configurable rules over synthetic holdings, not learned causal relationships or externally validated sensitivities.
- Stress assumptions are illustrative sensitivities. Loans use approximate duration plus incremental expected loss; bonds use duration; derivatives use a proxy beta.
- Review evidence and scenario assumptions before acting. Analyst override workflow and calibrated production models remain future work.
