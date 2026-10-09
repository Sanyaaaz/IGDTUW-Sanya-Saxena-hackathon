from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from uuid import uuid4
import os
import json
import asyncio
import httpx
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, desc, inspect, text as sql_text
from sqlalchemy.orm import Session
from app.core.config import FRONTEND_ORIGIN, DEMO_MODE
from app.database.session import Base, engine, get_db, SessionLocal
from app.database.models import RiskSignal, StressRun, ProviderHealth, FXRate
from app.schemas import AnalyzeRequest, StressRequest, StressRunOut, ScenarioAssumptions, ReverseStressRequest, CanonicalEventOut
from app.services.demo_data import seed_signals, add_signal
from app.nlp.analyzer import analyze, sentiment_model_status, classifier_status
from app.stress_testing.engine import ASSETS, SCENARIOS, SCENARIO_BY_ID, run_stress
from app.ingestion.connectors import fetch_gdelt, fetch_rss, fetch_sample_social, GDELTProvider, RSSProvider, DemoProvider, PROVIDER_STATUS, record_provider_result
from app.services.event_intelligence import canonical_events, propagation, generate_scenario, RISK_RULES, event_factor_shocks

Base.metadata.create_all(bind=engine)
with engine.begin() as _conn:
    _columns={column["name"] for column in inspect(_conn).get_columns("risk_signals")}
    for _column,_default in (("data_status","FALLBACK"),("source_status","NOT_CONFIGURED")):
        if _column not in _columns: _conn.execute(sql_text(f"ALTER TABLE risk_signals ADD COLUMN {_column} VARCHAR(20) NOT NULL DEFAULT '{_default}'"))
    _conn.execute(sql_text("UPDATE risk_signals SET data_status='SYNTHETIC', source_status='NOT_CONFIGURED' WHERE lower(source) LIKE '%synthetic%'"))
@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as db:
        seed_signals(db)
    yield

app=FastAPI(title="Nexora", version="0.1.0", description="Explainable financial event intelligence and illustrative portfolio stress testing.", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[FRONTEND_ORIGIN,"http://localhost:5173","http://127.0.0.1:5173","http://127.0.0.1:5174"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def parse_publication_time(value: str | None) -> datetime:
    if not value:
        return datetime.now(timezone.utc)
    try:
        if len(value) == 16 and value.endswith("Z"):
            return datetime.strptime(value, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
        parsed = parsedate_to_datetime(value)
        return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
    except (TypeError, ValueError, OverflowError):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.replace(tzinfo=timezone.utc) if parsed.tzinfo is None else parsed.astimezone(timezone.utc)
        except (TypeError, ValueError, OverflowError):
            return datetime.now(timezone.utc)

def configured_rss_feeds():
    env_url=os.getenv("NEWS_RSS_URL","").strip()
    if env_url: return [{"name":"Configured RSS feed","url":u.strip()} for u in env_url.split(",") if u.strip()]
    try: return json.loads((Path(__file__).resolve().parents[2]/"data"/"rss_feeds.json").read_text())
    except (OSError,ValueError): return []

def gdelt_enabled():
    return os.getenv("GDELT_ENABLED", "true").strip().lower() not in {"false", "0", "off", "disabled"}

def utc_iso(value):
    if value is None: return None
    if value.tzinfo is None: value=value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat()

@app.get("/api/health")
def health(): return {"status":"operational","mode":"offline demo" if DEMO_MODE else "connected","timestamp":datetime.now(timezone.utc).isoformat()}

@app.get("/api/status")
def status(db:Session=Depends(get_db)):
    try:
        with engine.connect() as conn: conn.execute(sql_text("SELECT 1"))
        db_state="connected"
    except Exception as exc: db_state=f"unavailable: {str(exc)[:100]}"
    return {"mode":"DEMO / SYNTHETIC" if DEMO_MODE else "LIVE CONNECTORS CONFIGURED","database":db_state,"providers":[{"name":x["provider"],"type":"news provider","status":x["source_status"],"configured":x["configured"],"last_attempt":x["last_attempt"],"last_fetch":x["last_success"],"last_error":x["last_error"],"articles_ingested":x["articles_ingested"]} for x in source_status(db)],"nlp":{"sentiment":sentiment_model_status(),"classification":classifier_status(),"entity_resolution":"Local alias registry"},"portfolio":{"status":"SYNTHETIC","currency":"INR","asset_count":len(ASSETS)}}

def persist_provider_result(db:Session,name:str,configured:bool,count:int,error:str|None):
    now=datetime.now(timezone.utc); row=db.get(ProviderHealth,name)
    state="FAILED" if error else ("LIVE" if configured else "NOT_CONFIGURED")
    if row is None:
        row=ProviderHealth(provider=name,configured=configured,status=state,last_attempt=now,last_success=now if configured and not error else None,last_error=error,articles_ingested=count)
        db.add(row)
    else:
        row.configured=configured; row.status=state; row.last_attempt=now; row.last_error=error; row.articles_ingested=count
        if configured and not error: row.last_success=now
    db.commit()

def source_status(db:Session):
    feeds=configured_rss_feeds()
    all_names=["GDELT"]+[x["name"] for x in feeds]+["DemoProvider"]
    saved={row.provider:row for row in db.scalars(select(ProviderHealth)).all()}
    out=[]
    for name in all_names:
        configured=(name=="GDELT" and gdelt_enabled()) or any(x["name"]==name for x in feeds)
        record=saved.get(name)
        state=(record.status if record else "NOT_CHECKED") if configured else "NOT_CONFIGURED"
        out.append({"provider":name,"configured":configured,"source_status":state,"last_attempt":utc_iso(record.last_attempt) if record else None,"last_success":utc_iso(record.last_success) if record else None,"last_error":record.last_error if record else None,"articles_ingested":record.articles_ingested if record else 0})
    return out

@app.get("/api/sources/status")
def get_source_status(db:Session=Depends(get_db)):
    return source_status(db)

@app.get("/api/dashboard/summary")
def summary(db:Session=Depends(get_db)):
    rows=canonical_events(db); runs=db.scalars(select(StressRun).order_by(desc(StressRun.created_at)).limit(5)).all()
    event_types={}; sectors={}; pos=neg=neutral=0
    for x in rows:
        event_types[x["event_type"]]=event_types.get(x["event_type"],0)+1; sectors[x["sector"]]=sectors.get(x["sector"],0)+1
        if x["sentiment"]>.12: pos+=1
        elif x["sentiment"]<-.12: neg+=1
        else: neutral+=1
    return {"total_events":len(rows),"high_impact":sum(x["impact"]>=7 for x in rows),"affected_entities":len(set(e["name"] for x in rows for e in x["entities"])),"sentiment":{"positive":pos,"negative":neg,"neutral":neutral},"event_types":[{"name":k,"count":v} for k,v in event_types.items()],"sectors":[{"name":k,"count":v} for k,v in sectors.items()],"latest_events":[{k:x[k] for k in ("id","title","source","source_url","published_at","text","entity","ticker","sector","event_type","sentiment","impact","confidence","corroboration","model_label","explanation")} for x in rows[:6]],"recent_runs":[StressRunOut.model_validate(x).model_dump(mode="json") for x in runs],"portfolio_value":sum(a["value"] for a in ASSETS)}

@app.get("/api/signals")
def signals(search:str|None=None,event_type:str|None=None,min_impact:int=Query(1,ge=1,le=10),limit:int=Query(100,ge=1,le=250),db:Session=Depends(get_db)):
    result=canonical_events(db)
    if event_type and event_type!="All events": result=[r for r in result if r["event_type"]==event_type]
    if search: result=[r for r in result if search.lower() in (r["title"]+" "+r["entity"]+" "+r["text"]).lower()]
    return [r for r in result if r["impact"]>=min_impact][:limit]

@app.get("/api/signals/{signal_id}", response_model=CanonicalEventOut)
def signal_detail(signal_id:str,db:Session=Depends(get_db)):
    row=db.get(RiskSignal,signal_id)
    if not row: raise HTTPException(404,"Risk signal not found")
    return next(x for x in canonical_events(db) if signal_id in x["signals"])

@app.post("/api/analyze", response_model=CanonicalEventOut)
@app.post("/api/events/analyze", response_model=CanonicalEventOut)
def analyze_text(payload:AnalyzeRequest,db:Session=Depends(get_db)):
    data=analyze(payload.text)
    row=add_signal(db,{**data,"title":payload.title,"source":payload.source,"source_url":payload.source_url,"text":payload.text})
    return next((x for x in canonical_events(db) if row.id in x["signals"]), None)

@app.post("/api/ingest")
async def ingest(db:Session=Depends(get_db)):
    feeds=configured_rss_feeds(); providers=([GDELTProvider(fetch_gdelt)] if gdelt_enabled() else [])+[RSSProvider(item["name"],item["url"],fetch_rss) for item in feeds]
    records=[]; errors=[]; provider_counts={};
    async def fetch_one(provider):
        try:
            docs=await provider.fetch(); record_provider_result(provider.name,True,len(docs)); return provider.name,docs,None
        except Exception as exc:
            message=str(exc)[:180]; record_provider_result(provider.name,True,0,message); return provider.name,[],message
    results=await asyncio.gather(*(fetch_one(provider) for provider in providers))
    for name,docs,error in results:
        records.extend([{**doc,"_ingested_provider":name} for doc in docs if isinstance(doc,dict)]); provider_counts[name]=len([doc for doc in docs if isinstance(doc,dict)])
        if error: errors.append({"source":name,"message":error})
    try:
        demo=DemoProvider(); samples=await demo.fetch(); records.extend(samples); provider_counts[demo.name]=0
        record_provider_result(demo.name,False,0)
    except Exception as exc:
        errors.append({"source":"DemoProvider","message":str(exc)[:180]}); record_provider_result("DemoProvider",False,0,str(exc)[:180])
    inserted=0
    for doc in records:
        try:
            body=str(doc.get("text", ""))[:12000].strip(); title=str(doc.get("title", "")).strip()[:300]
            if len(body)<12 or not title: continue
            if db.scalar(select(RiskSignal.id).where(RiskSignal.text == body).limit(1)): continue
            result=analyze(body); source_name=str(doc.get("source","Unknown source"))[:100]; live=bool(doc.get("_ingested_provider"))
            add_signal(db,{**result,"title":title,"source":source_name,"source_url":doc.get("source_url", ""),"text":body,"published_at":parse_publication_time(doc.get("published_at")),"data_status":"LIVE" if live else "SYNTHETIC","source_status":"LIVE" if live else "NOT_CONFIGURED"}); inserted+=1
        except (TypeError,ValueError,KeyError):
            continue
    for name,count in provider_counts.items():
        error=next((e["message"] for e in errors if e["source"]==name),None)
        record_provider_result(name,name!="DemoProvider",count,error)
        persist_provider_result(db,name,name!="DemoProvider",count,error)
    return {"inserted":inserted,"errors":errors,"note":"External sources may be unreachable; bundled records remain available."}

@app.get("/api/portfolio")
def portfolio():
    total=sum(a["value"] for a in ASSETS)
    return {"name":"Nexora Synthetic Demonstration Portfolio","synthetic":True,"label":"For demonstration of event-to-risk transmission","currency":"INR","total_value":total,"assets":ASSETS,"allocation":[{"name":typ,"value":sum(a["value"] for a in ASSETS if a["type"]==typ)} for typ in sorted(set(a["type"] for a in ASSETS))]}

@app.get("/api/fx/usd-inr")
async def usd_inr_rate(db:Session=Depends(get_db)):
    pair="USD/INR"; row=db.get(FXRate,pair); now=datetime.now(timezone.utc)
    try:
        async with httpx.AsyncClient(timeout=6) as client:
            response=await client.get("https://api.frankfurter.dev/v2/rate/usd/inr")
            response.raise_for_status(); payload=response.json()
        rate=float(payload["rate"]); rate_date=str(payload["date"])
        if rate<=0: raise ValueError("Provider returned a non-positive rate")
        if row is None:
            row=FXRate(pair=pair,rate=rate,rate_date=rate_date,fetched_at=now,provider="Frankfurter")
            db.add(row)
        else:
            row.rate=rate; row.rate_date=rate_date; row.fetched_at=now; row.provider="Frankfurter"
        db.commit()
        return {"pair":pair,"rate":rate,"rate_date":rate_date,"updated_at":now.isoformat(),"status":"LIVE","label":"Indicative FX rate","provider":"Frankfurter"}
    except Exception as exc:
        if row:
            stamp=row.fetched_at.replace(tzinfo=timezone.utc) if row.fetched_at.tzinfo is None else row.fetched_at
            return {"pair":pair,"rate":row.rate,"rate_date":row.rate_date,"updated_at":stamp.isoformat(),"status":"CACHED","label":"Indicative FX rate · cached","provider":row.provider,"error":str(exc)[:160]}
        return {"pair":pair,"rate":None,"rate_date":None,"updated_at":None,"status":"UNAVAILABLE","label":"FX rate unavailable","provider":"Frankfurter","error":str(exc)[:160]}

@app.get("/api/scenarios")
def scenarios(): return SCENARIOS

@app.post("/api/stress-tests")
def stress_test(payload:StressRequest,db:Session=Depends(get_db)):
    if payload.scenario_id not in SCENARIO_BY_ID: raise HTTPException(404,"Scenario not found")
    event=db.get(RiskSignal,payload.event_id) if payload.event_id else None
    if payload.event_id and not event: raise HTTPException(404,"Risk signal not found")
    canonical=next((x for x in canonical_events(db) if event and event.id in x["signals"]),None)
    if canonical and canonical["impact"]<SCENARIO_BY_ID[payload.scenario_id]["trigger_threshold"]:
        raise HTTPException(422,"Event impact is below this scenario's configured trigger threshold")
    result=run_stress(SCENARIO_BY_ID[payload.scenario_id]); row=StressRun(id=f"str-{uuid4().hex[:10]}",scenario_id=payload.scenario_id,scenario_name=SCENARIO_BY_ID[payload.scenario_id]["name"],event_id=event.id if event else None,event_title=event.title if event else "Manual scenario",baseline=result["baseline"],stressed=result["stressed"],loss=result["loss"],loss_pct=result["loss_pct"],created_at=datetime.now(timezone.utc)); db.add(row); db.commit(); db.refresh(row)
    return {**StressRunOut.model_validate(row).model_dump(mode="json"),"assets":result["assets"],"sector_pnl":result["sector_pnl"],"assumptions":result["scenario"]}

@app.get("/api/stress-tests",response_model=list[StressRunOut])
def stress_runs(db:Session=Depends(get_db)):
    return db.scalars(select(StressRun).order_by(desc(StressRun.created_at)).limit(30)).all()

# Canonical event intelligence endpoints. Existing /signals remain for backward compatibility.
def _canonical_event(event_id: str, db: Session):
    event=next((x for x in canonical_events(db) if x["event_id"]==event_id),None)
    if not event: raise HTTPException(404,"Event not found")
    return event

@app.get("/api/events", response_model=list[CanonicalEventOut])
def events(search: str|None=None, event_type: str|None=None, limit: int=Query(100,ge=1,le=250), db: Session=Depends(get_db)):
    rows=canonical_events(db)
    if search: rows=[r for r in rows if search.lower() in (r["canonical_title"]+" "+r["entity"]+" "+r["event_type"]).lower()]
    if event_type and event_type!="All events": rows=[r for r in rows if r["event_type"]==event_type]
    return rows[:limit]

@app.get("/api/events/{event_id}", response_model=CanonicalEventOut)
def event_detail(event_id: str, db: Session=Depends(get_db)): return _canonical_event(event_id,db)

@app.get("/api/events/{event_id}/exposure")
def event_exposure(event_id: str, db: Session=Depends(get_db)):
    row=_canonical_event(event_id,db)
    return {"event_id":event_id,"data_status":row["data_status"],"exposures":row["exposures"],"total_exposed_value":sum({x["asset_id"]:x["asset_value"] for x in row["exposures"]}.values()),"exposed_asset_count":len({x["asset_id"] for x in row["exposures"]})}

@app.get("/api/events/{event_id}/propagation")
def event_propagation(event_id: str, db: Session=Depends(get_db)):
    return propagation(_canonical_event(event_id,db))

@app.get("/api/events/{event_id}/stress")
def event_stress_preview(event_id: str, severity: str=Query("BASE",pattern="^(MILD|BASE|SEVERE)$"), db: Session=Depends(get_db)):
    row=_canonical_event(event_id,db); scenario=generate_scenario(row,severity)
    result=run_stress(scenario)
    return {"scenario":scenario,"preview":{"baseline":result["baseline"],"stressed":result["stressed"],"loss":result["loss"],"loss_pct":result["loss_pct"],"assets":result["assets"],"sector_pnl":result["sector_pnl"]}}

@app.post("/api/events/{event_id}/generate-scenario")
def event_generate_scenario(event_id: str, severity: str=Query("BASE",pattern="^(MILD|BASE|SEVERE)$"), db: Session=Depends(get_db)):
    return generate_scenario(_canonical_event(event_id,db),severity)

@app.get("/api/risk/alerts")
def risk_alerts(db: Session=Depends(get_db)):
    rows=[r for r in canonical_events(db) if r["impact"]>=RISK_RULES.get("minimum_alert_impact",7) and r["confidence"]>=RISK_RULES.get("minimum_alert_confidence",.4) and r["exposures"]]
    return [{"id":r["event_id"],"event_id":r["event_id"],"title":r["canonical_title"],"impact":r["impact"],"confidence":r["confidence"],"source_count":r["source_count"],"exposed_assets":len(r["exposures"]),"data_status":r["data_status"],"suggested_action":"Review mapped exposures and run the event-implied stress scenario."} for r in rows]

@app.get("/api/risk/overview")
def risk_overview(db: Session=Depends(get_db)):
    rows=canonical_events(db); alerts=[r for r in rows if r["impact"]>=RISK_RULES.get("minimum_alert_impact",7) and r["confidence"]>=RISK_RULES.get("minimum_alert_confidence",.4) and r["exposures"]]
    return {"event_count":len(rows),"alerts":[{"event_id":r["event_id"],"title":r["canonical_title"],"impact":r["impact"],"confidence":r["confidence"],"data_status":r["data_status"]} for r in alerts],"highest_impact_event":rows[0] if rows else None,"history_status":"CURRENT-WINDOW ONLY · insufficient history for long-run baseline","portfolio_status":"SYNTHETIC"}

@app.get("/api/portfolio/exposure")
def portfolio_exposure(db: Session=Depends(get_db)):
    rows=canonical_events(db); vulnerable=[]
    for a in ASSETS:
        matches=[r for r in rows if any(x["asset_id"]==a["id"] for x in r["exposures"])]
        if matches:
            top=max(matches,key=lambda r:r["impact"])
            vulnerable.append({"asset_id":a["id"],"asset_name":a["name"],"issuer":a["issuer"],"sector":a["sector"],"value":a["value"],"event_id":top["event_id"],"event":top["canonical_title"],"impact":top["impact"],"confidence":top["confidence"],"sensitivity":next(x["sensitivity"] for x in top["exposures"] if x["asset_id"]==a["id"]),"data_status":top["data_status"]})
    return {"synthetic":True,"vulnerabilities":sorted(vulnerable,key=lambda x:x["impact"],reverse=True)}

@app.post("/api/stress-test")
def what_if_stress(payload: ScenarioAssumptions, db: Session=Depends(get_db)):
    scenario={"id":"what-if","name":payload.name,"rate_shock_bps":payload.rate_shock_bps,"spread_shock_bps":payload.spread_shock_bps,"equity_shock_pct":payload.equity_shock_pct,"energy_shock_pct":payload.energy_shock_pct,"pd_multiplier":payload.pd_multiplier,"factor_shocks":payload.factor_shocks}
    result=run_stress(scenario)
    event=db.get(RiskSignal,payload.event_id) if payload.event_id else None
    row=StressRun(id=f"str-{uuid4().hex[:10]}",scenario_id="what-if",scenario_name=payload.name,event_id=payload.event_id,event_title=event.title if event else payload.name,baseline=result["baseline"],stressed=result["stressed"],loss=result["loss"],loss_pct=result["loss_pct"],created_at=datetime.now(timezone.utc)); db.add(row); db.commit()
    return {"id":row.id,"scenario_id":"what-if","scenario_name":payload.name,"event_id":payload.event_id,"event_title":row.event_title,**result,"assumptions":scenario,"data_status":"MODEL-INFERRED · SYNTHETIC PORTFOLIO"}

@app.post("/api/reverse-stress-test")
def reverse_stress(payload: ReverseStressRequest):
    if payload.scenario_id not in SCENARIO_BY_ID and payload.scenario_id not in ("event-energy","event-credit","event-macro","event-generic"):
        raise HTTPException(404,"Unknown scenario template")
    template=SCENARIO_BY_ID.get(payload.scenario_id) or {"id":payload.scenario_id,"name":"Event-implied template","rate_shock_bps":0,"spread_shock_bps":0,"equity_shock_pct":0,"energy_shock_pct":0,"pd_multiplier":payload.pd_multiplier,"factor_shocks":payload.factor_shocks or (event_factor_shocks({"canonical_title":"credit deterioration","text":"credit default","event_type":"CREDIT"}) if payload.scenario_id=="event-credit" else event_factor_shocks({"canonical_title":"rate repricing","text":"interest rate policy","event_type":"MONETARY_POLICY"}) if payload.scenario_id=="event-macro" else event_factor_shocks({"canonical_title":"oil supply disruption","text":"oil supply disruption","event_type":"COMMODITY"}))}
    low,high=0.0,10.0; target=payload.target_loss_pct
    def scaled(f):
        return {**template,"rate_shock_bps":template["rate_shock_bps"]*f,"spread_shock_bps":template["spread_shock_bps"]*f,"equity_shock_pct":template["equity_shock_pct"]*f,"energy_shock_pct":template["energy_shock_pct"]*f,"factor_shocks":{k:v*f for k,v in template.get("factor_shocks",{}).items()},"pd_multiplier":max(.1,1+(template["pd_multiplier"]-1)*f)}
    for _ in range(45):
        mid=(low+high)/2
        if run_stress(scaled(mid))["loss_pct"]<target: low=mid
        else: high=mid
    answer=scaled(high); out=run_stress(answer)
    return {"target_loss_pct":target,"achieved_loss_pct":out["loss_pct"],"severity_multiplier":round(high,4),"required_shocks":{k:answer[k] for k in ("rate_shock_bps","spread_shock_bps","equity_shock_pct","energy_shock_pct","pd_multiplier")},"factor_shocks":answer.get("factor_shocks",{}),"portfolio_loss":out["loss"],"threshold_found":out["loss_pct"]>=target,"data_status":"MODEL-IMPLIED THRESHOLD · SYNTHETIC PORTFOLIO"}

@app.get("/api/risk/clusters")
def risk_clusters(db: Session=Depends(get_db)):
    rows=canonical_events(db); groups={}
    for event in rows:
        factors=set(event_factor_shocks(event))
        kind=event["event_type"]
        if kind not in ("COMMODITY","GEOPOLITICAL","SUPPLY_CHAIN"):
            factors.difference_update({"CRUDE_OIL","SUPPLY_CHAIN","ENERGY_COST"})
        if kind not in ("MONETARY_POLICY","MACROECONOMIC"):
            factors.difference_update({"INTEREST_RATES","INFLATION"})
        if kind!="CREDIT": factors.discard("CREDIT_SPREADS")
        if kind not in ("EQUITY_VOLATILITY","CYBER","GEOPOLITICAL"): factors.discard("EQUITY_VOLATILITY")
        entity_keys={e["name"] for e in event["entities"]}
        sector_keys={e["sector"] for e in event["entities"] if e.get("sector") not in ("Unclassified","—")}
        candidates=factors|{f"ENTITY:{x}" for x in entity_keys}|{f"SECTOR:{x}" for x in sector_keys}
        for key in sorted(candidates): groups.setdefault(key,[]).append(event)
    output=[]; seen=set()
    for key,events_ in groups.items():
        distinct={x["event_id"]:x for x in events_}
        if len(distinct)<2: continue
        ids=tuple(sorted(distinct))
        if ids in seen: continue
        seen.add(ids); vals=list(distinct.values()); newest=max(x["latest_seen"] for x in vals)
        if (datetime.now(timezone.utc)-newest.replace(tzinfo=timezone.utc) if newest.tzinfo is None else datetime.now(timezone.utc)-newest).total_seconds()>7*86400: continue
        factor=key
        cluster_name=(f"{key.removeprefix('ENTITY:')} Entity Cluster" if key.startswith("ENTITY:") else f"{key.removeprefix('SECTOR:')} Sector Cluster" if key.startswith("SECTOR:") else f"{key.replace('_',' ').title()} Risk Cluster")
        output.append({"name":cluster_name,"factor":factor,"event_ids":[x["event_id"] for x in vals],"events":[x["canonical_title"] for x in vals],"cluster_score":round(min(10,4+len(vals)*1.1+sum(x["impact"] for x in vals)/len(vals)*.25),1),"event_count":len(vals),"data_status":"MODEL-INFERRED","window":"7 days","basis":"Shared entity, sector or configured event-relevant risk factor; deterministic grouping."})
    return sorted(output,key=lambda x:(x["cluster_score"],x["event_count"]),reverse=True)[:10]
