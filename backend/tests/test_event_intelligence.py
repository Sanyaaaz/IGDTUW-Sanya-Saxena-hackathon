from app.services.event_intelligence import generate_scenario, map_exposure, resolve_entities, similarity, event_factor_shocks
from app.nlp.analyzer import analyze, classify_event
from app.stress_testing.engine import run_stress


def test_similarity_groups_paraphrase_but_not_unrelated_story():
    a = "US announces new sanctions on Russian banks and financial institutions"
    b = "New sanctions target Russian banking institutions"
    c = "Solaris Energy wins a battery storage contract"
    assert similarity(a, b) > similarity(a, c)
    assert similarity(a, b) > 0.3


def test_entity_resolution_normalizes_aliases():
    entities = resolve_entities("AAPL falls after Apple Inc. cuts its guidance")
    apple = next(x for x in entities if x["name"] == "Apple Inc.")
    assert apple["ticker"] == "AAPL"
    assert apple["sector"] == "Technology"


def test_oil_event_maps_energy_and_indirect_assets():
    mapped = map_exposure("Geopolitical", "Oil supply disruption raises crude prices", [])
    assert any(x["sector"] == "Energy" and x["exposure_type"] == "INDIRECT" for x in mapped)
    assert all(x["reason"] for x in mapped)


def test_event_scenario_is_separate_from_forecast():
    scenario = generate_scenario({"event_type":"Geopolitical","canonical_title":"Oil supply disruption","impact":8,"event_id":"evt-demo"})
    assert scenario["id"] == "event-energy"
    assert scenario["data_status"] == "MODEL-INFERRED"
    assert "not forecasts" in scenario["assumption_label"]
    mild=generate_scenario({"event_type":"COMMODITY","canonical_title":"Major oil supply disruption in Middle East","impact":8,"event_id":"evt-demo"},"MILD")
    severe=generate_scenario({"event_type":"COMMODITY","canonical_title":"Major oil supply disruption in Middle East","impact":8,"event_id":"evt-demo"},"SEVERE")
    assert severe["factor_shocks"]["CRUDE_OIL"] > mild["factor_shocks"]["CRUDE_OIL"]
    assert severe["factor_shocks"]["CRUDE_OIL"] == 40

def test_three_hackathon_pipeline_cases():
    sanctions=analyze("US announces major sanctions on a Russian bank, restricting its access to international payment networks.")
    assert sanctions["event_type"] in {"GEOPOLITICAL","REGULATORY"}
    assert sanctions["sentiment"] < 0
    fed=analyze("Federal Reserve raises interest rates by 50 basis points, increasing borrowing costs.")
    assert fed["event_type"]=="MONETARY_POLICY"
    oil_text="Major oil supply disruption in Middle East raises crude prices and threatens airline fuel costs."
    oil=analyze(oil_text)
    assert classify_event(oil_text)["event_type"] in {"COMMODITY","GEOPOLITICAL"}
    entities=resolve_entities(oil_text)
    exposures=map_exposure(oil["event_type"],oil_text,entities)
    assert any(x["issuer"]=="Airline Corp" and x["direction"]=="NEGATIVE" and x["risk_factor"]=="CRUDE_OIL" for x in exposures)
    scenario=generate_scenario({"event_type":oil["event_type"],"canonical_title":"Major oil supply disruption in Middle East","text":oil_text,"impact":9,"event_id":"demo"})
    result=run_stress(scenario)
    airline=next(x for x in result["assets"] if x["issuer"]=="Airline Corp")
    assert airline["pnl"]<0
    assert result["loss"]>0

def test_factor_transmission_energy_hedge_and_airline_losses():
    shocks=event_factor_shocks({"canonical_title":"Major Middle East oil supply disruption","text":"Oil supply disruption raises crude and inflation","event_type":"COMMODITY"})
    result=run_stress({"factor_shocks":shocks,"pd_multiplier":1.0})
    rows={x["issuer"]:x for x in result["assets"]}
    assert rows["Airline Corp"]["pnl"]<0
    assert rows["Energy index"]["pnl"]>0
    assert rows["United States"]["pnl"]<0

def test_event_exposure_reports_each_shocked_factor_for_an_asset():
    event={"canonical_title":"Major Middle East oil supply disruption","text":"Crude oil, inflation, rates and supply costs rise","event_type":"COMMODITY"}
    shocks=event_factor_shocks(event)
    mapped=map_exposure("COMMODITY",event["text"],[],shocks)
    airline={(x["risk_factor"],x["sensitivity_coefficient"]) for x in mapped if x["issuer"]=="Airline Corp"}
    assert ("CRUDE_OIL",-0.8) in airline
    assert ("SUPPLY_CHAIN",-0.2) in airline
    assert len(airline)==2

def test_mild_base_severe_change_portfolio_pnl_monotonically():
    event={"event_type":"COMMODITY","canonical_title":"Major Middle East oil supply disruption","impact":8,"event_id":"demo"}
    results=[run_stress(generate_scenario(event,level)) for level in ("MILD","BASE","SEVERE")]
    assert results[0]["loss"] < results[1]["loss"] < results[2]["loss"]
    for result in results:
        assert round(sum(x["stressed_value"] for x in result["assets"]),2)==result["stressed"]
