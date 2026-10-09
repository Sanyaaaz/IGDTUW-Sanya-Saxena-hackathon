from fastapi.testclient import TestClient
import pytest
from app.main import app

@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client

def test_health_and_demo_endpoints(client):
    assert client.get("/api/health").status_code == 200
    signals = client.get("/api/signals")
    assert signals.status_code == 200
    assert all(row["source_count"] == len({s["name"] for s in row["source_list"] if s["source_type"] not in {"synthetic","analyst_input"}}) for row in signals.json())
    assert all(row["data_status"] in {"SYNTHETIC", "LIVE", "FALLBACK"} for row in signals.json())
    summary = client.get("/api/dashboard/summary").json()
    impacts = [row["impact"] for row in summary["latest_events"]]
    assert impacts == sorted(impacts, reverse=True)
    assert client.get("/api/portfolio").json()["synthetic"] is True

def test_stress_threshold_and_manual_run(client):
    low = client.post("/api/stress-tests", json={"scenario_id":"geo-energy", "event_id":"evt-005"})
    assert low.status_code == 422
    result = client.post("/api/stress-tests", json={"scenario_id":"geo-energy"})
    assert result.status_code == 200
    assert len(result.json()["assets"]) >= 5

def test_analyze_persists_traceable_signal(client):
    result = client.post("/api/events/analyze", json={"title":"Northstar credit update", "source":"Analyst sample", "text":"Northstar Bank reports a default and higher credit loss provisions for commercial property loans."})
    assert result.status_code == 200
    signal = result.json()
    assert signal["entity"] == "Northstar Bank"
    assert signal["event_type"] == "CREDIT"
    assert signal["sentiment_model"] in {"FinBERT", "Lexical fallback"}
    assert signal["classification_method"] in {"semantic_similarity", "rule_based_fallback", "description_similarity_fallback"}

def test_event_to_stress_workflow(client):
    signal = client.post("/api/analyze", json={"title":"Northstar provision update", "source":"Analyst sample", "text":"Northstar Bank reports a default and higher credit loss provisions as commercial borrowers request covenant relief."}).json()
    assert signal["impact"] >= 6.5
    result = client.post("/api/stress-tests", json={"scenario_id":"credit-down", "event_id":signal["id"]})
    assert result.status_code == 200
    assert result.json()["event_id"] == signal["id"]
    assert result.json()["assets"]

def test_publication_time_parsing():
    from datetime import timezone
    from app.main import parse_publication_time
    assert parse_publication_time("20261005T021500Z").isoformat() == "2026-10-05T02:15:00+00:00"
    assert parse_publication_time("Mon, 05 Oct 2026 02:15:00 GMT").tzinfo == timezone.utc

def test_canonical_event_exposure_propagation_and_scenario(client):
    event = next(x for x in client.get("/api/events").json() if x["entity"] == "Maersk")
    assert event["source_count"] == 0  # seeded source reports are synthetic, not independent confirmations
    assert event["data_status"] == "SYNTHETIC"
    exposure = client.get(f"/api/events/{event['event_id']}/exposure").json()
    assert exposure["exposures"]
    graph = client.get(f"/api/events/{event['event_id']}/propagation").json()
    assert [node["kind"] for node in graph["nodes"]] == ["EVENT", "MACRO FACTOR", "SECTOR", "ASSET"]
    assert "Crude Oil" in graph["nodes"][1]["label"]
    assert "Airline Corp" in graph["nodes"][3]["label"]
    assert all(edge["reason"] and edge["direction"] for edge in graph["edges"])
    demo=next(x for x in client.get("/api/events").json() if x["canonical_title"].startswith("Major Middle East oil supply"))
    demo_graph=client.get(f"/api/events/{demo['event_id']}/propagation").json()
    assert any(path["factor"]=="INTEREST_RATES" for path in demo_graph["paths"])
    scenario = client.post(f"/api/events/{event['event_id']}/generate-scenario").json()
    assert scenario["data_status"] == "MODEL-INFERRED"
    assert "not forecasts" in scenario["assumption_label"]
    legacy_detail = client.get(f"/api/signals/{event['signals'][0]}").json()
    assert legacy_detail["source_count"] == 0
    assert legacy_detail["confidence"] == 0

def test_what_if_and_reverse_stress_endpoints(client):
    what_if = client.post("/api/stress-test", json={"name":"Demo what-if","rate_shock_bps":50,"spread_shock_bps":100,"equity_shock_pct":-0.1,"energy_shock_pct":0.2,"pd_multiplier":1.4})
    assert what_if.status_code == 200
    assert len(what_if.json()["assets"]) == 10
    reverse = client.post("/api/reverse-stress-test", json={"scenario_id":"event-energy","target_loss_pct":10})
    assert reverse.status_code == 200
    assert reverse.json()["achieved_loss_pct"] >= 10

def test_external_reports_corroborate_but_synthetic_does_not(client):
    first = client.post("/api/analyze", json={"title":"US announces new sanctions on Russian banks","source":"Reuters","source_url":"https://reuters.com/story/1","text":"The United States announced sanctions targeting Russian banking institutions after the escalation."}).json()
    second = client.post("/api/analyze", json={"title":"New sanctions target Russian financial institutions","source":"GDELT · example.com","source_url":"https://example.com/story/2","text":"New restrictions target Russian financial institutions following the escalation."}).json()
    assert first["event_id"] != second["event_id"]
    assert second["source_count"] == 0
    assert second["data_status"] == "FALLBACK"

def test_ingestion_keeps_sample_fallback_when_gdelt_fails(client, monkeypatch):
    async def fail(): raise RuntimeError("offline")
    async def empty(_url): return []
    monkeypatch.setattr("app.main.fetch_gdelt", fail)
    monkeypatch.setattr("app.main.fetch_rss", empty)
    result = client.post("/api/ingest").json()
    assert result["errors"][0]["source"] == "GDELT"
    assert "bundled records remain available" in result["note"]

def test_live_status_requires_successful_provider_fetch(client, monkeypatch):
    async def gdelt_ok():
        return [{"title":"Sanctions widen on Russian banking system","text":"US sanctions expand to Russian banking institutions and disrupt cross-border payments.","source":"GDELT · reuters.com","source_url":"https://reuters.com/a","published_at":""}]
    async def rss_ok(_url, **_kwargs):
        return [{"title":"New restrictions target Russian banks","text":"New sanctions target Russian banks as payment restrictions expand.","source":"RSS · bbc.co.uk","source_url":"https://bbc.co.uk/a","published_at":""}]
    monkeypatch.setenv("NEWS_RSS_URL","https://feeds.example.test/rss.xml")
    monkeypatch.setattr("app.main.fetch_gdelt",gdelt_ok)
    monkeypatch.setattr("app.main.fetch_rss",rss_ok)
    response=client.post("/api/ingest")
    assert response.status_code==200
    status=client.get("/api/sources/status").json()
    assert next(x for x in status if x["provider"]=="GDELT")["source_status"]=="LIVE"
    assert next(x for x in status if x["provider"]=="GDELT")["last_success"]
    external=next(x for x in client.get("/api/events").json() if x["data_status"]=="LIVE" and "Russian" in x["canonical_title"])
    assert external["source_count"]==2

def test_fx_rate_live_and_cached_fallback(client, monkeypatch):
    import app.main as main
    class Response:
        def raise_for_status(self): pass
        def json(self): return {"date":"2026-10-05","base":"USD","quote":"INR","rate":96.2}
    class GoodClient:
        def __init__(self, **_kwargs): pass
        async def __aenter__(self): return self
        async def __aexit__(self, *_args): pass
        async def get(self, _url): return Response()
    monkeypatch.setattr(main.httpx,"AsyncClient",GoodClient)
    live=client.get("/api/fx/usd-inr").json()
    assert live["status"]=="LIVE" and live["rate"]==96.2
    class FailedClient(GoodClient):
        async def get(self, _url): raise RuntimeError("offline")
    monkeypatch.setattr(main.httpx,"AsyncClient",FailedClient)
    cached=client.get("/api/fx/usd-inr").json()
    assert cached["status"]=="CACHED" and cached["rate"]==96.2

def test_analyst_claiming_reuters_is_not_marked_live(client):
    event=client.post("/api/analyze",json={"title":"News claim","source":"Reuters","source_url":"https://reuters.com/story","text":"Reuters says a Russian bank faces sanctions and restrictions."}).json()
    assert event["data_status"]=="FALLBACK"
    assert event["source_status"]=="NOT_CONFIGURED"
    assert event["source_count"]==0

def test_deterministic_oil_demo_severity_and_transmission(client):
    event=next(x for x in client.get("/api/events").json() if x["canonical_title"].startswith("Major Middle East oil supply"))
    assert event["data_status"]=="SYNTHETIC"
    assert event["source_count"]==0
    assert "CRUDE_OIL" in event["risk_factor_shocks"]
    mild=client.post(f"/api/events/{event['event_id']}/generate-scenario?severity=MILD").json()
    severe=client.post(f"/api/events/{event['event_id']}/generate-scenario?severity=SEVERE").json()
    assert severe["factor_shocks"]["CRUDE_OIL"]>mild["factor_shocks"]["CRUDE_OIL"]
    preview=client.get(f"/api/events/{event['event_id']}/stress?severity=SEVERE").json()
    assert preview["preview"]["loss"]>0
    airline=next(x for x in preview["preview"]["assets"] if x["issuer"]=="Airline Corp")
    assert airline["pnl"]<0
    reverse=client.post("/api/reverse-stress-test",json={"scenario_id":severe["id"],"target_loss_pct":5,"factor_shocks":severe["factor_shocks"]}).json()
    assert reverse["threshold_found"] is True
    assert reverse["achieved_loss_pct"]>=5
    assert "CRUDE_OIL" in reverse["factor_shocks"]

def test_remaining_risk_and_history_routes(client):
    assert client.get("/api/risk/alerts").status_code == 200
    assert client.get("/api/risk/overview").status_code == 200
    assert client.get("/api/portfolio/exposure").json()["synthetic"] is True
    assert client.get("/api/scenarios").status_code == 200
    event = client.get("/api/events").json()[0]
    assert client.get(f"/api/events/{event['event_id']}/stress").status_code == 200
    assert client.get("/api/stress-tests").status_code == 200
    assert client.get("/api/sources/status").status_code == 200
    assert client.get("/api/risk/clusters").status_code == 200
    assert client.get("/openapi.json").status_code == 200
