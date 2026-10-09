import json
from pathlib import Path

_RISK_FACTOR_CONFIG = json.loads((Path(__file__).resolve().parents[3] / "data" / "risk_factors.json").read_text())

ASSETS = [
 {"id":"A-101","name":"Northstar Bank senior loan","type":"Corporate loan","issuer":"Northstar Bank","sector":"Financials","value":125_000_000,"duration":3.2,"pd":0.025,"lgd":0.45,"equity_beta":0.0,"spread_duration":3.2},
 {"id":"A-102","name":"Acme Cloud term loan","type":"Corporate loan","issuer":"Acme Cloud","sector":"Technology","value":90_000_000,"duration":2.8,"pd":0.018,"lgd":0.40,"equity_beta":0.0,"spread_duration":2.8},
 {"id":"A-103","name":"US Treasury 10Y","type":"Government bond","issuer":"United States","sector":"Sovereign","value":160_000_000,"duration":7.4,"pd":0.001,"lgd":0.1,"equity_beta":0.0,"spread_duration":0.0},
 {"id":"A-104","name":"European infrastructure bond","type":"Corporate bond","issuer":"EuroGrid","sector":"Utilities","value":105_000_000,"duration":5.1,"pd":0.012,"lgd":0.35,"equity_beta":0.0,"spread_duration":5.1},
 {"id":"A-105","name":"Global equity basket","type":"Equity","issuer":"Diversified","sector":"Equities","value":110_000_000,"duration":0.0,"pd":0.0,"lgd":0.0,"equity_beta":1.0,"spread_duration":0.0},
 {"id":"A-106","name":"Energy index swap","type":"Derivative","issuer":"Energy index","sector":"Energy","value":45_000_000,"duration":0.0,"pd":0.0,"lgd":0.0,"equity_beta":0.55,"spread_duration":0.0},
 {"id":"A-107","name":"Solaris project finance","type":"Corporate loan","issuer":"Solaris Energy","sector":"Energy","value":80_000_000,"duration":4.0,"pd":0.022,"lgd":0.42,"equity_beta":0.0,"spread_duration":4.0},
 {"id":"A-108","name":"Investment grade credit fund","type":"Corporate bond","issuer":"Diversified","sector":"Credit","value":135_000_000,"duration":4.6,"pd":0.01,"lgd":0.35,"equity_beta":0.0,"spread_duration":4.6},
 {"id":"A-109","name":"Airline Corp equity","type":"Equity","issuer":"Airline Corp","sector":"Transportation","value":65_000_000,"duration":0.0,"pd":0.0,"lgd":0.0,"equity_beta":1.0,"spread_duration":0.0},
 {"id":"A-110","name":"Long Duration Bond Fund","type":"Corporate bond","issuer":"Long Duration Bond Fund","sector":"Fixed Income","value":85_000_000,"duration":9.0,"pd":0.01,"lgd":0.35,"equity_beta":0.0,"spread_duration":9.0},
]
SCENARIOS = [
 {"id":"geo-energy","name":"Geopolitical energy disruption","event_types":["Geopolitical"],"trigger_threshold":7,"rate_shock_bps":50,"spread_shock_bps":125,"equity_shock_pct":-0.12,"energy_shock_pct":0.18,"pd_multiplier":1.35,"description":"Illustrative rerouting and commodity shock: rates +50bp, credit spreads +125bp, equities -12%, energy-linked exposures +18%."},
 {"id":"macro-slowdown","name":"Macroeconomic slowdown","event_types":["Macroeconomic","Earnings"],"trigger_threshold":7,"rate_shock_bps":-25,"spread_shock_bps":175,"equity_shock_pct":-0.18,"energy_shock_pct":-0.08,"pd_multiplier":1.6,"description":"Illustrative growth slowdown: rates -25bp, spreads +175bp, equities -18%, energy -8%, credit PD x1.6."},
 {"id":"rates-up","name":"Interest-rate shock","event_types":["Macroeconomic"],"trigger_threshold":6,"rate_shock_bps":200,"spread_shock_bps":40,"equity_shock_pct":-0.04,"energy_shock_pct":0.0,"pd_multiplier":1.1,"description":"Parallel rate increase +200bp with modest credit widening and equity repricing."},
 {"id":"credit-down","name":"Credit deterioration","event_types":["Credit Event"],"trigger_threshold":7,"rate_shock_bps":0,"spread_shock_bps":250,"equity_shock_pct":-0.07,"energy_shock_pct":0.0,"pd_multiplier":2.0,"description":"Illustrative credit event: spreads +250bp, PD x2, equities -7%."},
 {"id":"equity-down","name":"Broad equity-market decline","event_types":["Other / Uncertain"],"trigger_threshold":8,"rate_shock_bps":0,"spread_shock_bps":50,"equity_shock_pct":-0.22,"energy_shock_pct":0.0,"pd_multiplier":1.15,"description":"Broad equity shock of -22% with a small credit spread widening."},
]
SCENARIO_BY_ID = {s["id"]: s for s in SCENARIOS}

def calc_asset(a, scenario):
    value = a["value"]
    if scenario.get("factor_shocks"):
        config=_RISK_FACTOR_CONFIG.get("asset_sensitivities",{})
        defaults={"Corporate loan":"default_loan","Corporate bond":"default_bond","Government bond":"default_bond","Equity":"default_equity"}
        sens=config.get(a["issuer"],config.get(defaults.get(a["type"],"default"),{}))
        change=0.0
        for factor,shock in scenario["factor_shocks"].items():
            coefficient=sens.get(factor,0)
            shock_unit=shock/10000 if factor in ("INTEREST_RATES","CREDIT_SPREADS") else shock/100
            change += value*coefficient*shock_unit
        if a["type"] == "Corporate loan":
            old_el=value*a["pd"]*a["lgd"]
            new_el=value*min(.95,a["pd"]*scenario.get("pd_multiplier",1))*a["lgd"]
            change -= new_el-old_el
        return {**a,"stressed_value":round(value+change,2),"pnl":round(change,2),"pnl_pct":round(change/value*100,3)}
    rate_return = -a["duration"] * scenario["rate_shock_bps"] / 10000
    spread_return = -a["spread_duration"] * scenario["spread_shock_bps"] / 10000
    if a["type"] == "Corporate loan":
        old_el = value * a["pd"] * a["lgd"]
        new_el = value * min(0.95, a["pd"] * scenario["pd_multiplier"]) * a["lgd"]
        change = value * (rate_return + spread_return) - (new_el - old_el)
    elif a["type"] == "Government bond":
        change = value * rate_return
    elif a["type"] == "Corporate bond":
        change = value * (rate_return + spread_return)
    elif a["type"] == "Equity":
        change = value * scenario["equity_shock_pct"]
    else:
        change = value * (a["equity_beta"] * scenario["equity_shock_pct"] + scenario["energy_shock_pct"] * (1 if a["sector"] == "Energy" else 0))
    return {**a, "stressed_value": round(value+change, 2), "pnl": round(change, 2), "pnl_pct": round(change/value*100, 3)}

def run_stress(scenario):
    rows = [calc_asset(a, scenario) for a in ASSETS]
    baseline = sum(a["value"] for a in ASSETS); stressed = sum(a["stressed_value"] for a in rows)
    sectors = {}
    for row in rows: sectors[row["sector"]] = sectors.get(row["sector"], 0) + row["pnl"]
    return {"baseline": baseline, "stressed": round(stressed,2), "loss": round(baseline-stressed,2), "loss_pct": round((baseline-stressed)/baseline*100,3), "assets": rows, "sector_pnl": [{"sector":k,"pnl":round(v,2)} for k,v in sorted(sectors.items(), key=lambda x:x[1])], "scenario": scenario}
