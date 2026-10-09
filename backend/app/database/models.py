from datetime import datetime, timezone
from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.session import Base

class RiskSignal(Base):
    __tablename__ = "risk_signals"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    source: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str] = mapped_column(Text, default="")
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    text: Mapped[str] = mapped_column(Text)
    entity: Mapped[str] = mapped_column(String(120), index=True)
    ticker: Mapped[str] = mapped_column(String(20), default="")
    sector: Mapped[str] = mapped_column(String(100), default="")
    event_type: Mapped[str] = mapped_column(String(80), index=True)
    sentiment: Mapped[float] = mapped_column(Float)
    impact: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)
    corroboration: Mapped[int] = mapped_column(Integer, default=1)
    model_label: Mapped[str] = mapped_column(String(60), default="DEMO_HEURISTIC")
    explanation: Mapped[str] = mapped_column(Text, default="")
    data_status: Mapped[str] = mapped_column(String(20), default="FALLBACK")
    source_status: Mapped[str] = mapped_column(String(20), default="NOT_CONFIGURED")

class StressRun(Base):
    __tablename__ = "stress_runs"
    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(60))
    scenario_name: Mapped[str] = mapped_column(String(160))
    event_id: Mapped[str | None] = mapped_column(String(40), nullable=True)
    event_title: Mapped[str] = mapped_column(String(300), default="Manual scenario")
    baseline: Mapped[float] = mapped_column(Float)
    stressed: Mapped[float] = mapped_column(Float)
    loss: Mapped[float] = mapped_column(Float)
    loss_pct: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ProviderHealth(Base):
    __tablename__ = "provider_health"
    provider: Mapped[str] = mapped_column(String(120), primary_key=True)
    configured: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(String(24), default="NOT_CHECKED")
    last_attempt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    articles_ingested: Mapped[int] = mapped_column(Integer, default=0)

class FXRate(Base):
    __tablename__ = "fx_rates"
    pair: Mapped[str] = mapped_column(String(12), primary_key=True)
    rate: Mapped[float] = mapped_column(Float)
    rate_date: Mapped[str] = mapped_column(String(10))
    fetched_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    provider: Mapped[str] = mapped_column(String(100), default="Frankfurter")
