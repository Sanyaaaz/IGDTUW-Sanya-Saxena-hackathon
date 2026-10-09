from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

class AnalyzeRequest(BaseModel):
    text: str = Field(min_length=12, max_length=12000)
    source: str = "Analyst submission"
    title: str = "Analyst submitted text"
    source_url: str = ""

class SignalOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    title: str
    source: str
    source_url: str
    published_at: datetime
    text: str
    entity: str
    ticker: str
    sector: str
    event_type: str
    sentiment: float
    sentiment_model: str = "Lexical fallback"
    impact: float
    confidence: float
    corroboration: int
    model_label: str
    explanation: str

class StressRequest(BaseModel):
    scenario_id: str
    event_id: str | None = None

class ScenarioAssumptions(BaseModel):
    rate_shock_bps: float = Field(ge=-1000, le=2000)
    spread_shock_bps: float = Field(ge=0, le=3000)
    equity_shock_pct: float = Field(ge=-1, le=1)
    energy_shock_pct: float = Field(ge=-1, le=2)
    pd_multiplier: float = Field(ge=0.1, le=10)
    name: str = "What-if scenario"
    event_id: str | None = None
    factor_shocks: dict[str, float] = {}

class ReverseStressRequest(BaseModel):
    scenario_id: str = "event-energy"
    target_loss_pct: float = Field(default=10, gt=0.1, le=90)
    factor_shocks: dict[str, float] = {}
    pd_multiplier: float = Field(default=1.0, ge=0.1, le=10)

class StressRunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    scenario_id: str
    scenario_name: str
    event_id: str | None
    event_title: str
    baseline: float
    stressed: float
    loss: float
    loss_pct: float
    created_at: datetime

class EntityOut(BaseModel):
    name: str
    ticker: str = "—"
    sector: str = "Unclassified"
    entity_type: str = "other"

class SourceOut(BaseModel):
    name: str
    source_type: str
    weight: float
    url: str = ""

class ExposureOut(BaseModel):
    asset_id: str
    asset_name: str
    issuer: str
    sector: str
    exposure_type: str
    reason: str
    sensitivity: str
    asset_value: float
    risk_factor: str = ""
    direction: str = ""
    exposure_score: float = 0.0
    sensitivity_coefficient: float = 0.0
    exposure_reason: str = ""
    model_implied_return_pct: float = 0.0
    model_implied_pnl: float = 0.0

class CanonicalEventOut(BaseModel):
    id: str
    event_id: str
    canonical_title: str
    title: str
    event_type: str
    event_type_confidence: float = 0.0
    classification_evidence: list[str] = []
    classification_method: str = ""
    entity: str
    entities: list[EntityOut]
    ticker: str
    sector: str
    sentiment: float
    sentiment_model: str = "Lexical fallback"
    impact: float
    confidence: float
    first_seen: datetime
    latest_seen: datetime
    published_at: datetime
    source_count: int
    corroboration: int
    source_list: list[SourceOut]
    source: str
    source_url: str
    text: str
    model_label: str
    corroboration_score: float
    data_status: str
    source_status: str = "NOT_CONFIGURED"
    signals: list[str]
    exposures: list[ExposureOut]
    impact_drivers: dict[str, float]
    confidence_drivers: dict[str, float]
    novelty: dict[str, str]
    explanation: str
    risk_factor_shocks: dict[str, float] = {}
    why_this_matters: dict[str, object] = {}
    model_metadata: dict[str, object]
