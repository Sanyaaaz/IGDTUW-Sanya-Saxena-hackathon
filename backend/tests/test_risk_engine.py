from app.nlp.analyzer import analyze
from app.stress_testing.engine import ASSETS, SCENARIO_BY_ID, run_stress

def test_analyzer_returns_bounded_structured_signal():
    result = analyze("Northstar Bank reports a default and increases credit loss provisions.")
    assert result["event_type"] == "CREDIT"
    assert result["event_type_confidence"] > 0
    assert result["classification_evidence"]
    assert result["entity"] == "Northstar Bank"
    assert -1 <= result["sentiment"] <= 1
    assert 1 <= result["impact"] <= 10

def test_stress_run_reconciles_asset_values():
    result = run_stress(SCENARIO_BY_ID["geo-energy"])
    assert len(result["assets"]) == len(ASSETS)
    assert round(sum(x["stressed_value"] for x in result["assets"]), 2) == result["stressed"]
    assert result["baseline"] == sum(x["value"] for x in ASSETS)
    assert result["loss_pct"] > 0

def test_credit_scenario_changes_loan_loss():
    result = run_stress(SCENARIO_BY_ID["credit-down"])
    northstar = next(x for x in result["assets"] if x["id"] == "A-101")
    assert northstar["pnl"] < 0
