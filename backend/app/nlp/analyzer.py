"""Local financial event NLP with optional, lazily loaded models and honest fallbacks."""
import os
import re
from collections import Counter
from functools import lru_cache
from math import sqrt
from uuid import uuid4

EVENT_DESCRIPTIONS = {
    "GEOPOLITICAL": "war conflict sanctions military attack country diplomatic tension",
    "MACROECONOMIC": "inflation recession GDP growth employment economic slowdown",
    "MONETARY_POLICY": "central bank interest rates rate hike Federal Reserve monetary policy",
    "CREDIT": "default bankruptcy credit loss loan downgrade credit spread",
    "M&A": "merger acquisition takeover buyout deal",
    "EARNINGS": "quarterly revenue profit guidance earnings outlook",
    "REGULATORY": "regulator regulation court lawsuit compliance fine ban",
    "COMMODITY": "oil crude copper gold commodity supply price",
    "SUPPLY_CHAIN": "shipping logistics shortage production supply disruption",
    "CYBER": "cyberattack ransomware data breach hacking outage",
    "PRODUCT_LAUNCH": "launch release new product contract",
    "OTHER": "business event company announcement",
}
EVENT_RULES = {
    "MONETARY_POLICY": ["interest rate", "central bank", "federal reserve", "rate hike", "basis points", "fomc"],
    "GEOPOLITICAL": ["sanction", "war", "conflict", "geopolitical", "military", "invasion"],
    "CREDIT": ["default", "credit loss", "downgrade", "bankruptcy", "credit spread"],
    "M&A": ["acquire", "acquisition", "merger", "takeover", "buyout"],
    "EARNINGS": ["revenue", "earnings", "outlook", "profit", "guidance", "quarter"],
    "REGULATORY": ["regulator", "regulation", "court", "lawsuit", "compliance", "fine", "ban"],
    "COMMODITY": ["oil", "crude", "copper", "gold", "commodity"],
    "SUPPLY_CHAIN": ["supply disruption", "shipping disruption", "shortage", "shipping", "supply chain"],
    "CYBER": ["cyberattack", "ransomware", "data breach", "hacking", "cyber"],
    "PRODUCT_LAUNCH": ["launch", "release", "product"],
}
NEG = {"loss", "cut", "risk", "disruption", "default", "decline", "slowdown", "delay", "higher", "inflation", "sanction", "sanctions", "restricting", "restriction", "disrupt", "lawsuit", "outage", "downgrade", "fall", "shortage", "warning"}
POS = {"growth", "win", "wins", "profit", "launch", "beats", "record", "upgrade", "expands", "gain", "positive", "contract", "acquire"}
ENTITY_ALIASES = {
    "Northstar Bank": ("northstar", "NSB", "Financials"),
    "Acme Cloud": ("acme", "ACME", "Technology"),
    "Solaris Energy": ("solaris", "SLRS", "Energy"),
    "Maersk": ("maersk", "AMKBY", "Industrials"),
    "Federal Reserve": ("federal reserve", "—", "Macroeconomic"),
    "European Union": ("european union", "—", "Regulatory"),
    "Apple Inc.": ("apple", "AAPL", "Technology"),
    "Russia": ("russian", "—", "Geopolitical"),
    "Middle East": ("middle east", "—", "Geopolitical"),
    "Oil": ("crude", "CL=F", "Energy"),
}

_finbert_state = "NOT CHECKED"
_semantic_state = "NOT CHECKED"


def _has_term(text: str, term: str) -> bool:
    words = re.escape(term).replace(r"\ ", r"\s+")
    return re.search(r"(?<![a-z])" + words + r"(?:s|es)?(?![a-z])", text) is not None


@lru_cache(maxsize=1)
def _finbert_pipeline():
    global _finbert_state
    try:
        from transformers import pipeline
        loaded = pipeline("text-classification", model=os.getenv("FINBERT_MODEL", "ProsusAI/finbert"), top_k=None, truncation=True)
        _finbert_state = "ACTIVE"
        return loaded
    except Exception:
        _finbert_state = "UNAVAILABLE"
        return None


@lru_cache(maxsize=1)
def _semantic_model():
    global _semantic_state
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(os.getenv("NEXORA_SEMANTIC_MODEL", "sentence-transformers/all-MiniLM-L6-v2"))
        _semantic_state = "ACTIVE"
        return model
    except Exception:
        _semantic_state = "UNAVAILABLE"
        return None


def _cosine(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = sqrt(sum(x * x for x in a)) or 1
    nb = sqrt(sum(y * y for y in b)) or 1
    return dot / (na * nb)


def _description_similarity(text: str):
    tokens = Counter(re.findall(r"[a-z0-9]+", text.lower()))
    norm = sqrt(sum(v * v for v in tokens.values())) or 1
    scores = {kind: sum(tokens[t.lower()] for t in desc.split()) / norm / sqrt(len(desc.split())) for kind, desc in EVENT_DESCRIPTIONS.items()}
    return max(scores.items(), key=lambda row: row[1])


@lru_cache(maxsize=8192)
def classify_event(text: str):
    """Prefer local sentence embeddings when installed; report deterministic fallback otherwise."""
    kinds = list(EVENT_DESCRIPTIONS)
    try:
        model = _semantic_model()
        if model is not None:
            vectors = model.encode([text, *(EVENT_DESCRIPTIONS[k] for k in kinds)], normalize_embeddings=True)
            scores = [_cosine(vectors[0], vector) for vector in vectors[1:]]
            best = max(range(len(kinds)), key=scores.__getitem__)
            kind, score = kinds[best], max(0.0, min(1.0, float(scores[best])))
            evidence = [f"closest event description: {EVENT_DESCRIPTIONS[kind]}"]
            confidence_basis = "uncalibrated semantic similarity"
            # A commodity noun plus explicit disruption language is more specific
            # than the model's broader supply-chain neighbour for this taxonomy.
            low = text.lower()
            if kind == "SUPPLY_CHAIN" and any(_has_term(low, term) for term in ("oil", "crude", "gas")) and any(_has_term(low, term) for term in ("disruption", "disrupt", "supply")):
                kind = "COMMODITY"
                evidence.append("commodity disruption cue: oil, crude, or gas with supply disruption")
                confidence_basis = "uncalibrated semantic similarity with specific commodity cue"
            return {"event_type": kind, "confidence": round(score, 2), "confidence_basis": confidence_basis, "evidence": evidence, "method": "semantic_similarity"}
    except Exception:
        pass

    low = text.lower()
    hits = {kind: [term for term in terms if _has_term(low, term)] for kind, terms in EVENT_RULES.items()}
    counts = {kind: len(terms) for kind, terms in hits.items()}
    ranked = sorted(counts.items(), key=lambda row: row[1], reverse=True)
    if ranked and ranked[0][1]:
        kind, n = ranked[0]
        second = ranked[1][1] if len(ranked) > 1 else 0
        confidence = min(.96, .55 + .12 * min(2, n - 1) + .08 * min(2, n - second))
        return {"event_type": kind, "confidence": round(confidence, 2), "confidence_basis": "rule cue strength; uncalibrated", "evidence": hits[kind], "method": "rule_based_fallback"}
    kind, score = _description_similarity(text)
    if score < .10:
        kind, score = "OTHER", 0.0
    return {"event_type": kind, "confidence": round(min(.55, score), 2), "confidence_basis": "bag-of-words description similarity; uncalibrated", "evidence": [f"nearest description: {EVENT_DESCRIPTIONS[kind]}"], "method": "description_similarity_fallback"}


def sentiment_model_status():
    setting = os.getenv("FINRISK_USE_FINBERT", "auto").lower()
    if setting in {"false", "0", "off", "disabled"}:
        return {"active": False, "status": "DISABLED", "model": "Lexical fallback"}
    return {"active": _finbert_state == "ACTIVE", "status": _finbert_state, "model": "FinBERT" if _finbert_state == "ACTIVE" else "Lexical fallback"}


def classifier_status():
    return {"active": _semantic_state == "ACTIVE", "status": _semantic_state, "method": "semantic_similarity" if _semantic_state == "ACTIVE" else "rule_based_fallback"}


def analyze(text: str):
    low = text.lower()
    toks = re.findall(r"[a-z]+", low)
    neg = sum(t in NEG for t in toks)
    pos = sum(t in POS for t in toks)
    sentiment = max(-1.0, min(1.0, (pos - neg) / max(4, (pos + neg) * 1.35)))
    classified = classify_event(text)
    event_type = classified["event_type"]
    material = min(4, sum(kw in low for kw in ["billion", "major", "global", "default", "sanction", "central bank", "supply", "systemic"]))
    entity = "Unresolved entity"
    ticker = "—"
    sector = "Unclassified"
    for name, (alias, sym, sec) in ENTITY_ALIASES.items():
        if alias in low:
            entity, ticker, sector = name, sym, sec
            break

    finbert_setting = os.getenv("FINRISK_USE_FINBERT", "auto").lower()
    use_finbert = finbert_setting not in {"false", "0", "off", "disabled"}
    finbert = _finbert_pipeline() if use_finbert else None
    sentiment_model = "Lexical fallback"
    if finbert:
        try:
            predictions = finbert(text[:4000])[0]
            probs = {p["label"].lower(): float(p["score"]) for p in predictions}
            sentiment = max(-1.0, min(1.0, probs.get("positive", 0.0) - probs.get("negative", 0.0)))
            sentiment_model = "FinBERT"
        except Exception:
            sentiment_model = "Lexical fallback"
    if sentiment_model == "Lexical fallback" and use_finbert and _finbert_state == "NOT CHECKED":
        _finbert_pipeline()
    impact = max(1, min(10, round(3 + abs(sentiment) * 3 + material * .65 + (1 if event_type in {"CREDIT", "GEOPOLITICAL", "MACROECONOMIC", "MONETARY_POLICY"} else 0))))
    model_label = "FINBERT_SENTIMENT" if sentiment_model == "FinBERT" else ("LEXICAL_DEMO_BASELINE (FINBERT UNAVAILABLE)" if use_finbert and _finbert_state == "UNAVAILABLE" else "LEXICAL_DEMO_BASELINE")
    explanation = f"{event_type} selected by {classified['method']}; evidence: {', '.join(classified['evidence']) or 'no direct evidence'}. Sentiment method: {sentiment_model} ({pos} positive, {neg} negative lexical cues)."
    return {
        "id": f"evt-{uuid4().hex[:10]}", "entity": entity, "ticker": ticker, "sector": sector,
        "event_type": event_type, "sentiment": round(sentiment, 2), "impact": impact,
        "confidence": 0.55 if entity == "Unresolved entity" else 0.72, "event_type_confidence": classified["confidence"],
        "classification_evidence": classified["evidence"], "classification_method": classified["method"],
        "sentiment_model": sentiment_model, "corroboration": 1, "model_label": model_label,
        "explanation": explanation,
    }
