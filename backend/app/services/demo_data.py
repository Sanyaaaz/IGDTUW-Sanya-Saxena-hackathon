from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.models import RiskSignal

NOW = datetime.now(timezone.utc)
SEED = [
 {"title":"Major Middle East oil supply disruption threatens shipping routes","source":"Synthetic news sample","entity":"Middle East","ticker":"—","sector":"Geopolitical","event_type":"Geopolitical","sentiment":-0.72,"impact":9,"confidence":0.0,"corroboration":0,"text":"DEMO SCENARIO: A major oil supply disruption in the Middle East interrupts shipping through the Strait of Hormuz, raising crude prices, inflation pressure and energy costs. This deterministic synthetic event is for illustrating model-implied portfolio stress only.","explanation":"Synthetic demonstration event. No live source corroboration; all downstream shocks are model-implied stress assumptions, not forecasts."},
 {"title":"Red Sea shipping disruption lifts freight and energy risk","source":"Synthetic news sample","entity":"Maersk","ticker":"AMKBY","sector":"Industrials","event_type":"Geopolitical","sentiment":-0.71,"impact":8,"confidence":0.87,"corroboration":0,"text":"Insurers raise premiums as vessels reroute around the Red Sea. The disruption is adding transit time and cost pressure across global supply chains and energy markets.","explanation":"Synthetic geopolitical disruption example; no independent source corroboration is present."},
 {"title":"Central bank signals rates may stay higher for longer","source":"Synthetic news sample","entity":"Federal Reserve","ticker":"—","sector":"Macroeconomic","event_type":"Macroeconomic","sentiment":-0.28,"impact":7,"confidence":0.82,"corroboration":0,"text":"Policymakers indicate borrowing costs could remain elevated as inflation progress slows, renewing repricing pressure across rate-sensitive assets.","explanation":"Synthetic macro policy example; no independent source corroboration is present."},
 {"title":"Acme Cloud trims annual outlook after enterprise slowdown","source":"Synthetic news sample","entity":"Acme Cloud","ticker":"ACME","sector":"Technology","event_type":"Earnings","sentiment":-0.66,"impact":6,"confidence":0.91,"corroboration":0,"text":"Acme Cloud cut its full-year revenue outlook after customers delayed software deployments. Management cited cautious enterprise spending and lower bookings.","explanation":"Synthetic issuer-specific earnings example; no independent source corroboration is present."},
 {"title":"Northstar Bank reports wider provisions on commercial property loans","source":"Synthetic news sample","entity":"Northstar Bank","ticker":"NSB","sector":"Financials","event_type":"Credit Event","sentiment":-0.58,"impact":8,"confidence":0.89,"corroboration":0,"text":"Northstar Bank increased credit-loss provisions as office vacancy rates rose and several borrowers sought covenant amendments.","explanation":"Synthetic credit deterioration example; no independent source corroboration is present."},
 {"title":"Solaris Energy wins multi-year grid storage contract","source":"Synthetic news sample","entity":"Solaris Energy","ticker":"SLRS","sector":"Energy","event_type":"Product Launch","sentiment":0.63,"impact":3,"confidence":0.79,"corroboration":0,"text":"Solaris Energy secured a multi-year battery storage contract supporting grid balancing and renewable integration.","explanation":"Synthetic positive contract example; no independent source corroboration is present."},
 {"title":"EU expands compliance deadline for selected carbon rules","source":"Synthetic news sample","entity":"European Union","ticker":"—","sector":"Regulatory","event_type":"Regulatory / Legal","sentiment":0.12,"impact":4,"confidence":0.73,"corroboration":0,"text":"Regulators proposed a phased compliance timeline for reporting requirements, giving affected companies additional time to prepare.","explanation":"Synthetic policy change example; no independent source corroboration is present."},
 {"title":"Copper supply outlook tightens after Chile mine stoppage","source":"Synthetic news sample","entity":"Copper Market","ticker":"HG=F","sector":"Materials","event_type":"Operational Disruption","sentiment":-0.49,"impact":6,"confidence":0.81,"corroboration":0,"text":"A labor stoppage at a major Chilean mine has disrupted shipments, tightening near-term concentrate availability and lifting treatment concerns.","explanation":"Synthetic supply disruption example; no independent source corroboration is present."},
 {"title":"Meridian Health to acquire diagnostics platform for $2.1bn","source":"Synthetic news sample","entity":"Meridian Health","ticker":"MDHN","sector":"Healthcare","event_type":"Merger & Acquisition","sentiment":0.31,"impact":5,"confidence":0.86,"corroboration":0,"text":"Meridian Health agreed to acquire a diagnostics platform, expanding its laboratory network. The deal remains subject to regulatory review.","explanation":"Synthetic strategic transaction example; no independent source corroboration is present."},
]

def seed_signals(db: Session):
    if not db.get(RiskSignal, "evt-001"):
        for i, item in enumerate(SEED):
            db.add(RiskSignal(id=f"evt-{i+1:03}", published_at=NOW-timedelta(hours=i*2+1), ingested_at=NOW, source_url="", model_label="DEMO_HEURISTIC", data_status="SYNTHETIC", source_status="NOT_CONFIGURED", **item))
        db.commit()
    demo_oil=next(x for x in SEED if x["title"].startswith("Major Middle East oil supply disruption"))
    if not db.scalar(select(RiskSignal.id).where(RiskSignal.title == demo_oil["title"]).limit(1)):
        db.add(RiskSignal(id="evt-demo-oil",published_at=NOW,ingested_at=NOW,source_url="",model_label="DEMO_HEURISTIC",data_status="SYNTHETIC",source_status="NOT_CONFIGURED",**demo_oil)); db.commit()
    if not db.scalar(select(RiskSignal.id).where(RiskSignal.source == "Synthetic social post").limit(1)):
        from app.nlp.analyzer import analyze
        sample_file = Path(__file__).resolve().parents[3] / "data" / "sample_social" / "sample_posts.json"
        for i, post in enumerate(json.loads(sample_file.read_text()), start=1):
            result = analyze(post["text"])
            db.add(RiskSignal(id=f"soc-demo-{i:02}", published_at=NOW-timedelta(minutes=15*i), ingested_at=NOW, source_url="", title=f"Social post · {post['entity']}", source=post["source"], text=post["text"], model_label=result["model_label"], explanation=result["explanation"], corroboration=1, data_status="SYNTHETIC", source_status="NOT_CONFIGURED", **{k:result[k] for k in ("entity","ticker","sector","event_type","sentiment","impact","confidence")}))
        db.commit()

def add_signal(db: Session, item: dict):
    allowed=set(RiskSignal.__table__.columns.keys())
    row_data = {k:v for k,v in item.items() if k in allowed}
    row_data.update({"id": item.get("id") or f"evt-{uuid4().hex[:10]}", "published_at": item.get("published_at", NOW), "ingested_at": NOW, "source_url": item.get("source_url", "")})
    if "data_status" not in row_data:
        is_synthetic="synthetic" in str(item.get("source","")).lower()
        row_data["data_status"]="SYNTHETIC" if is_synthetic else "FALLBACK"
        row_data["source_status"]="NOT_CONFIGURED"
    row = RiskSignal(**row_data)
    db.add(row); db.commit(); db.refresh(row)
    return row
