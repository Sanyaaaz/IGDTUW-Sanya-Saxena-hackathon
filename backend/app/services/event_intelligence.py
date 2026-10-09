"""Deterministic local event intelligence; deliberately avoids opaque external services."""
from collections import Counter
from datetime import datetime, timezone
from math import sqrt
import re
import json
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.models import RiskSignal
from app.stress_testing.engine import ASSETS
from app.nlp.analyzer import classify_event

STOP = {"about","after","against","amid","announces","announced","as","at","bank","be","by","for","from","has","have","in","into","its","of","on","over","that","the","their","to","with","will","says","said","new"}
DEFAULT_SOURCE_CONFIG = {
    "Reuters": {"type":"financial_news", "weight":0.90}, "Bloomberg": {"type":"financial_news", "weight":0.95},
    "GDELT": {"type":"news", "weight":0.65}, "RSS feed": {"type":"unknown", "weight":0.50},
    "Analyst submission": {"type":"analyst_input", "weight":0.70},
    "Synthetic news sample": {"type":"synthetic", "weight":0.0},
    "Synthetic social post": {"type":"synthetic", "weight":0.0},
}
ROOT=Path(__file__).resolve().parents[3]
def _load_json(path, fallback):
    try: return json.loads(path.read_text())
    except (OSError,ValueError): return fallback
SOURCE_CONFIG=_load_json(ROOT/"data"/"source_registry.json",DEFAULT_SOURCE_CONFIG)
ENTITY_REGISTRY=_load_json(ROOT/"data"/"entity_registry.json",{})
ENTITY_ALIASES={name:entity.get("aliases",[]) for name,entity in ENTITY_REGISTRY.items()}
ENTITY_META={name:(entity.get("ticker","—"),entity.get("sector","Unclassified"),entity.get("entity_type","other")) for name,entity in ENTITY_REGISTRY.items()}
RISK_RULES=_load_json(ROOT/"data"/"risk_rules.json",{"impact_adjustments":{"sentiment_weight":1.5,"sentiment_reference":0.5,"exposure_weight":2.0,"exposure_reference":0.15},"cluster_threshold":0.34})
SCENARIO_MAPPINGS=_load_json(ROOT/"data"/"event_scenario_mappings.json",{})
PROPAGATION_RULES=_load_json(ROOT/"data"/"propagation_rules.json",{})
RISK_FACTOR_CONFIG=_load_json(ROOT/"data"/"risk_factors.json",{})

def source_meta(source: str, url: str = "", verification: str = "NOT_CONFIGURED", data_status: str = "FALLBACK"):
    if verification != "LIVE":
        if data_status == "SYNTHETIC": return {"name":source,"source_type":"synthetic","weight":0.0,"domain":urlparse(url).netloc.lower() if url else ""}
        return {"name":source,"source_type":"analyst_input","weight":0.0,"domain":urlparse(url).netloc.lower() if url else ""}
    host=urlparse(url).netloc.lower().removeprefix("www.") if url else ""
    if url and source.lower().startswith("rss"):
        return {"name":source,"source_type":"news","weight":0.65,"domain":host}
    for key, val in SOURCE_CONFIG.items():
        if key.lower()!="gdelt" and (key.lower() in (source or "").lower() or key.lower() in host):
            return {"name":source,"source_type":val["type"],"weight":val["weight"],"domain":host}
    for key, val in SOURCE_CONFIG.items():
        if key.lower() in (source or "").lower(): return {"name":source,"source_type":val["type"],"weight":val["weight"],"domain":host}
    if host.endswith(".gov") or host.endswith(".gov.uk"): kind, weight = "official", 0.95
    elif host: kind, weight = "news", 0.65
    else: kind, weight = "unknown", 0.35
    return {"name":source,"source_type":kind,"weight":weight}

def _terms(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t)>2 and t not in STOP]

def similarity(a, b):
    ca, cb = Counter(_terms(a)), Counter(_terms(b))
    if not ca or not cb: return 0.0
    dot=sum(ca[t]*cb[t] for t in ca.keys() & cb.keys())
    return dot/(sqrt(sum(v*v for v in ca.values()))*sqrt(sum(v*v for v in cb.values())))

def resolve_entities(text, signal_entity=""):
    low=text.lower(); found=[]
    if signal_entity and signal_entity not in ("Unresolved entity", "—"): found.append(signal_entity)
    for name, aliases in ENTITY_ALIASES.items():
        if any(alias in low for alias in aliases) and name not in found: found.append(name)
    for a in ASSETS:
        if a["issuer"].lower() in low and a["issuer"] not in found: found.append(a["issuer"])
    return [{"name":n,"ticker":ENTITY_META.get(n,("—","Unclassified","other"))[0],"sector":ENTITY_META.get(n,("—","Unclassified","other"))[1],"entity_type":ENTITY_META.get(n,("—","Unclassified","other"))[2]} for n in found]

def _event_rows(db: Session):
    return db.scalars(select(RiskSignal).order_by(RiskSignal.published_at.asc())).all()

def canonical_events(db: Session):
    """Cluster similar reports using local TF cosine; returns one event per cluster."""
    rows=_event_rows(db); clusters=[]
    for row in rows:
        best=None; best_score=0
        row_type=source_meta(row.source,row.source_url,row.source_status,row.data_status)["source_type"]
        row_family="synthetic" if row_type=="synthetic" else ("analyst" if row_type=="analyst_input" else "external")
        for c in clusters:
            cluster_type=source_meta(c["rows"][0].source,c["rows"][0].source_url,c["rows"][0].source_status,c["rows"][0].data_status)["source_type"]
            cluster_family="synthetic" if cluster_type=="synthetic" else ("analyst" if cluster_type=="analyst_input" else "external")
            if row_family!=cluster_family or row_family=="analyst": continue
            score=max(similarity(row.title+" "+row.text, r.title+" "+r.text) for r in c["rows"])
            if score>=0.15 and row.entity not in ("Unresolved entity","—") and any(r.entity==row.entity and r.event_type==row.event_type for r in c["rows"]):
                score=max(score,0.38)
            if score>best_score: best,best_score=c,score
        if best is not None and best_score>=RISK_RULES.get("cluster_threshold",0.34): best["rows"].append(row)
        else: clusters.append({"rows":[row]})
    out=[]
    now=datetime.now(timezone.utc)
    for c in clusters:
        rr=c["rows"]; primary=max(rr,key=lambda r:(r.impact,r.confidence)); sources=[]
        for row in rr:
            meta=source_meta(row.source,row.source_url,row.source_status,row.data_status)
            key=(meta["name"], row.source_url)
            if key not in [(x["name"],x["url"]) for x in sources]: sources.append({**meta,"url":row.source_url})
        independent={s["name"] for s in sources if s["source_type"] not in ("synthetic","analyst_input")}
        independent_sources=[s for s in sources if s["source_type"] not in ("synthetic","analyst_input")]
        source_score=sum(s["weight"] for s in independent_sources)/max(1,len(independent_sources))
        diversity=min(1.0,max(0,len(independent)-1)/3)
        newest=max((r.published_at for r in rr),default=now)
        age=max(0,(now-newest.replace(tzinfo=timezone.utc) if newest.tzinfo is None else now-newest).total_seconds()/86400)
        recency=max(0,1-age/7)
        confidence=round(min(0.97,max(0.0,(0.48*source_score+0.3*diversity+0.22*recency) if independent else 0.0)),2)
        classified=classify_event(primary.title+" "+primary.text); canonical_type=classified["event_type"]
        entities=resolve_entities(" ".join(r.title+" "+r.text for r in rr),primary.entity)
        if primary.entity not in ("Unresolved entity","—") and not any(e["name"]==primary.entity for e in entities):
            entities.insert(0,{"name":primary.entity,"ticker":primary.ticker,"sector":primary.sector,"entity_type":"company"})
        factor_shocks=event_factor_shocks({"canonical_title":primary.title,"text":primary.text,"event_type":canonical_type})
        exps=map_exposure(canonical_type, " ".join(r.title+" "+r.text for r in rr), entities, factor_shocks)
        for exp in exps:
            shock=factor_shocks.get(exp["risk_factor"],0); unit=10000 if exp["risk_factor"] in ("INTEREST_RATES","CREDIT_SPREADS") else 100
            exp["model_implied_return_pct"]=round(exp["sensitivity_coefficient"]*shock/unit*100,2)
            exp["model_implied_pnl"]=round(exp["asset_value"]*exp["model_implied_return_pct"]/100,2)
        sev=(primary.impact/10); exposure=min(1,sum(x["asset_value"] for x in exps)/max(1,sum(a["value"] for a in ASSETS)))
        adj=RISK_RULES.get("impact_adjustments",{}); sent_adj=adj.get("sentiment_weight",1.5)*(abs(primary.sentiment)-adj.get("sentiment_reference",.5)); exposure_adj=adj.get("exposure_weight",2.0)*(exposure-adj.get("exposure_reference",.15))
        impact=round(min(10,max(1,primary.impact+sent_adj+exposure_adj)),1)
        data_status="SYNTHETIC" if all(r.data_status=="SYNTHETIC" for r in rr) else ("LIVE" if any(r.data_status=="LIVE" for r in rr) else "FALLBACK")
        source_status="LIVE" if any(r.source_status=="LIVE" for r in rr) else ("FAILED" if any(r.source_status=="FAILED" for r in rr) else "NOT_CONFIGURED")
        sentiment_method="Seeded synthetic value" if "DEMO_HEURISTIC" in primary.model_label else ("FinBERT" if "FINBERT" in primary.model_label else "Lexical fallback")
        out.append({"id":primary.id,"event_id":primary.id,"canonical_title":primary.title,"title":primary.title,"event_type":canonical_type,"event_type_confidence":classified["confidence"],"classification_evidence":classified["evidence"],"classification_method":classified["method"],"entity":primary.entity,"entities":entities,"ticker":primary.ticker,"sector":primary.sector,"sentiment":primary.sentiment,"sentiment_model":sentiment_method,"impact":impact,"confidence":confidence,"first_seen":min(r.published_at for r in rr),"latest_seen":newest,"published_at":newest,"source_count":len(independent),"corroboration":len(independent),"source_list":sources,"source":primary.source,"source_url":primary.source_url,"text":primary.text,"model_label":primary.model_label,"corroboration_score":round(diversity,2),"data_status":data_status,"source_status":source_status,"signals":[r.id for r in rr],"exposures":exps,"risk_factor_shocks":factor_shocks,"why_this_matters":{"what_happened":primary.title,"confidence_basis":f"{len(independent)} independent source(s); confidence is source evidence strength, not probability.","affected_factors":list(factor_shocks),"exposed_assets":[x["asset_name"] for x in exps],"risk_manager_action":"Review source evidence, verify entity mapping and inspect the editable model-implied stress scenario."},"impact_drivers":{"base_event_severity":round(primary.impact,1),"sentiment_adjustment":round(sent_adj,2),"portfolio_exposure_share":round(exposure,3)},"confidence_drivers":{"source_quality":round(source_score,2),"independent_source_diversity":round(diversity,2),"recency":round(recency,2)},"novelty":{"state":"CURRENT-WINDOW ANOMALY" if sum(1 for x in out if x["event_type"]==canonical_type)>=RISK_RULES.get("current_window_anomaly_min_events",3)-1 else "INSUFFICIENT HISTORY","explanation":"Based on currently retained events only; no long-run baseline is available."},"explanation":primary.explanation,"model_metadata":{"sentiment_model":sentiment_method,"classification_method":classified["method"],"impact_model":"severity with sentiment and exposure adjustments","generated_at":primary.ingested_at,"data_status":data_status}})
    out.sort(key=lambda e:(e["impact"],e["latest_seen"]),reverse=True)
    return out

def map_exposure(event_type, text, entities, factor_shocks=None):
    low=text.lower(); entity_names={e["name"].lower() for e in entities}; sector_names={e["sector"].lower() for e in entities}
    if factor_shocks is None:
        factor_shocks=event_factor_shocks({"canonical_title":"","text":text,"event_type":event_type})
    result=[]
    for a in ASSETS:
        direct=a["issuer"].lower() in entity_names
        sector=a["sector"].lower() in sector_names
        reason="Direct issuer match" if direct else (f"Sector relationship: {a['sector']}" if sector else "")
        sensitivities=RISK_FACTOR_CONFIG.get("asset_sensitivities",{})
        asset_sens=sensitivities.get(a["issuer"],sensitivities.get("default_"+({"Corporate loan":"loan","Corporate bond":"bond","Government bond":"bond","Equity":"equity"}.get(a["type"],"")),sensitivities.get("default",{})))
        for factor, shock in factor_shocks.items():
            coefficient=asset_sens.get(factor,0)
            if not coefficient or not shock:
                continue
            factor_reason={"CRUDE_OIL":"crude-oil price sensitivity","INTEREST_RATES":"interest-rate duration sensitivity","CREDIT_SPREADS":"credit-spread sensitivity","ENERGY_COST":"energy-cost sensitivity","SUPPLY_CHAIN":"supply-chain cost sensitivity","EQUITY_VOLATILITY":"equity-volatility sensitivity","INFLATION":"inflation sensitivity","CONSUMER_DEMAND":"consumer-demand sensitivity"}.get(factor,f"{factor.lower().replace('_',' ')} sensitivity")
            why="Direct issuer match" if direct else (f"Sector relationship: {a['sector']}" if sector else f"Indirect exposure through configured {factor_reason}")
            sensitivity="HIGH" if direct or abs(coefficient)>=.65 else ("MEDIUM" if abs(coefficient)>=.25 else "LOW")
            direction="POSITIVE" if coefficient>0 else "NEGATIVE"
            result.append({"asset_id":a["id"],"asset_name":a["name"],"issuer":a["issuer"],"sector":a["sector"],"exposure_type":"DIRECT" if direct else "INDIRECT","reason":why,"exposure_reason":why,"sensitivity":sensitivity,"risk_factor":factor,"direction":direction,"sensitivity_coefficient":coefficient,"exposure_score":round(min(1,abs(coefficient)),2),"asset_value":a["value"]})
    return result

def event_factor_shocks(event,severity="BASE"):
    text=(event.get("canonical_title","")+" "+event.get("text","")+" "+event.get("event_type","")).lower()
    key="oil_supply" if any(t in text for t in ("oil","crude","energy supply","shipping disruption","supply disruption","middle east")) else "monetary_policy" if any(t in text for t in ("interest rate","rate hike","monetary_policy","MONETARY_POLICY")) else "credit" if any(t in text for t in ("credit","bank","default","sanction")) else "geopolitical" if "geopolitical" in text or "conflict" in text else "generic"
    scale=RISK_FACTOR_CONFIG.get("severity_multipliers",{}).get(severity.upper(),1.0)
    raw=RISK_FACTOR_CONFIG.get("event_shocks",{}).get(key,RISK_FACTOR_CONFIG.get("event_shocks",{}).get("generic",{}))
    return {factor:round(value*scale,3) for factor,value in raw.items()}

def propagation(event):
    text=(event.get("canonical_title","")+" "+event.get("event_type","")).lower()
    rule=PROPAGATION_RULES.get("generic",{})
    for candidate in PROPAGATION_RULES.values():
        if any(term in text for term in candidate.get("match",[])):
            rule=candidate; break
    shocks=event_factor_shocks(event)
    exps=event.get("exposures",[])
    exposed_scores={k:sum(abs(x.get("sensitivity_coefficient",0)*shocks.get(k,0)) for x in exps if x.get("risk_factor")==k) for k in shocks}
    event_text=(event.get("canonical_title","")+" "+event.get("text","")).lower()
    oil_event=any(term in event_text for term in ("oil","crude","middle east","shipping disruption","energy supply"))
    factor="CRUDE_OIL" if oil_event and "CRUDE_OIL" in shocks and exposed_scores.get("CRUDE_OIL",0)>0 else (max(exposed_scores,key=exposed_scores.get) if exposed_scores and max(exposed_scores.values())>0 else (max(shocks,key=lambda k:abs(shocks[k])) if shocks else "EQUITY_VOLATILITY"))
    shock=shocks.get(factor,0); direction="↑" if shock>=0 else "↓"
    exposure_rows=[x for x in exps if x.get("risk_factor")==factor]
    sectors=sorted({x.get("sector","Unclassified") for x in exposure_rows})
    asset_names=[x.get("asset_name","Unknown asset") for x in sorted(exposure_rows,key=lambda x:x.get("exposure_score",0),reverse=True)[:4]]
    coefficient=sum(x.get("sensitivity_coefficient",0) for x in exposure_rows)/max(1,len(exposure_rows))
    implied_returns=[x.get("sensitivity_coefficient",0)*shock for x in exposure_rows]
    gains=sum(value>0 for value in implied_returns); losses=sum(value<0 for value in implied_returns)
    transmission="MIXED" if gains and losses else ("↑" if gains else "↓")
    nodes=[{"id":"0","kind":"EVENT","label":event["canonical_title"],"data_status":event.get("data_status","MODEL-INFERRED")},{"id":"1","kind":"MACRO FACTOR","label":f"{factor.replace('_',' ').title()} {direction} {abs(shock):g}{' bps' if factor in ('INTEREST_RATES','CREDIT_SPREADS') else '%'}","data_status":"MODEL-INFERRED"},{"id":"2","kind":"SECTOR","label":", ".join(sectors[:4]) or event.get("sector","Mapped portfolio sectors"),"data_status":"SYNTHETIC"},{"id":"3","kind":"ASSET","label":", ".join(asset_names) or "No configured asset sensitivity match","data_status":"SYNTHETIC"}]
    edges=rule.get("edges",["CAUSES","AFFECTS","EXPOSES"])
    # Each edge records its causal direction and a plain-language, rule-derived explanation.
    reasons=["The event matched a configured event-to-risk-factor rule.",f"The {factor} shock is transmitted through configured sector sensitivities; {gains} mapped assets gain and {losses} lose under this factor alone.",f"Assets are ranked by configured sensitivity to {factor}; indicated asset directions are {transmission.lower()}."]
    directions=["UP" if shock>=0 else "DOWN",transmission,transmission]
    strengths=[event["impact"]/10,min(.95,abs(coefficient)),min(.95,max((x.get("exposure_score",0) for x in exposure_rows),default=.2))]
    paths=[]
    for path_factor,path_shock in sorted(shocks.items(),key=lambda item:(item[0]!=factor,-abs(item[1]))):
        mapped=[x for x in exps if x.get("risk_factor")==path_factor]
        if not mapped: continue
        coeff=sum(x.get("sensitivity_coefficient",0) for x in mapped)/len(mapped)
        paths.append({"factor":path_factor,"shock":path_shock,"direction":"UP" if path_shock>=0 else "DOWN","asset_return_direction":"UP" if coeff*path_shock>=0 else "DOWN","sectors":sorted({x["sector"] for x in mapped}),"assets":[{"name":x["asset_name"],"sensitivity":x.get("sensitivity_coefficient",0),"exposure_score":x.get("exposure_score",0)} for x in sorted(mapped,key=lambda row:row.get("exposure_score",0),reverse=True)[:5]],"reason":f"{path_factor} shock {path_shock:+g} transmitted through configured asset sensitivity (mean {coeff:+.2f})."})
    return {"nodes":nodes,"edges":[{"source":str(i),"target":str(i+1),"relationship":edges[i],"direction":directions[i],"strength":round(max(.2,min(.95,strengths[i])),2),"reason":reasons[i]} for i in range(3)],"paths":paths,"risk_factor_shocks":shocks,"basis":"Configurable deterministic relationship and sensitivity rules; not a learned causal model."}

def generate_scenario(event,severity="BASE"):
    name=event["event_type"].lower()+" "+event["canonical_title"].lower(); intensity=max(.5,min(1.5,event["impact"]/7))
    severity_name=severity.upper() if isinstance(severity,str) else "BASE"
    scale=RISK_FACTOR_CONFIG.get("severity_multipliers",{}).get(severity_name,1.0)
    selected=SCENARIO_MAPPINGS.get("generic",{"id":"event-generic","name":"Event-implied broad risk shock","rate_shock_bps":25,"spread_shock_bps":100,"equity_shock_pct":-.1,"energy_shock_pct":0,"pd_multiplier":1.4})
    for rule in SCENARIO_MAPPINGS.values():
        if any(term in name for term in rule.get("match",[])):
            selected=rule; break
    base={k:v for k,v in selected.items() if k!="match"}
    base.update({"event_types":[event["event_type"]],"trigger_threshold":1,"description":f"Template mapped from {event['event_type']} classification.","severity":severity_name})
    # Keep shocks editable in API/UI; intensity scaling is explicit and bounded.
    for k in ("rate_shock_bps","spread_shock_bps"): base[k]=round(base[k]*intensity)
    for k in ("equity_shock_pct","energy_shock_pct"): base[k]=round(base[k]*intensity,3)
    base["pd_multiplier"]=round(1+(base["pd_multiplier"]-1)*intensity*scale,2)
    base.update({"rate_shock_bps":0,"spread_shock_bps":0,"equity_shock_pct":0,"energy_shock_pct":0,"factor_shocks":event_factor_shocks(event,severity_name),"calculation_basis":"Configured factor shocks multiplied by per-asset sensitivities; legacy scalar shocks are not used.","data_status":"MODEL-INFERRED","assumption_label":"Model-implied stress assumptions · editable · not forecasts","event_id":event.get("event_id",event.get("id",""))})
    return base
