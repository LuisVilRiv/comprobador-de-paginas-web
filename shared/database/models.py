"""
models.py — Modelos de base de datos compartidos (SQLAlchemy ORM).
"""
import os
from contextlib import contextmanager

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    Text,
    create_engine,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.engine import Engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# ── Configuración de la conexión ──────────────────────────────────────────────
DB_HOST = os.environ.get("DB_HOST", "localhost")
DB_PORT = int(os.environ.get("DB_PORT", 5432))
DB_NAME = os.environ.get("DB_NAME", "web_auditor")
DB_USER = os.environ.get("DB_USER", "auditor")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "auditor_secret")

DATABASE_URL = (
    f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)

engine: Engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)
Base = declarative_base()


@contextmanager
def get_db():
    """Context manager para sesiones de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Modelos ORM ───────────────────────────────────────────────────────────────

class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    name = Column(Text, nullable=False)
    email = Column(Text)
    phone = Column(Text)
    company = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    websites = relationship("Website", back_populates="client", cascade="all, delete-orphan")


class Website(Base):
    __tablename__ = "websites"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id", ondelete="CASCADE"), nullable=False)
    url = Column(Text, nullable=False)
    label = Column(Text)
    strategy = Column(Text, nullable=False, default="auto")
    active = Column(Boolean, nullable=False, default=True)
    pending_audit = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    client = relationship("Client", back_populates="websites")
    runs = relationship("AuditRun", back_populates="website", cascade="all, delete-orphan", order_by="desc(AuditRun.started_at)")


class AuditRun(Base):
    __tablename__ = "audit_runs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    website_id = Column(UUID(as_uuid=True), ForeignKey("websites.id", ondelete="CASCADE"), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at = Column(DateTime(timezone=True))
    status = Column(Text, nullable=False, default="running")
    strategy_used = Column(Text)
    error_message = Column(Text)
    score = Column(SmallInteger)
    previous_score = Column(SmallInteger)
    audit_status = Column(Text)
    release_blocked = Column(Boolean, default=False)
    audit_date = Column(Date, nullable=False, server_default=func.current_date())
    sections_passed = Column(SmallInteger, nullable=False, default=0)
    sections_total = Column(SmallInteger, nullable=False, default=10)
    response_time_ms = Column(Integer)
    status_code = Column(Integer)
    word_count = Column(Integer)
    h1_count = Column(SmallInteger)
    image_count = Column(SmallInteger)
    links_count = Column(SmallInteger)
    forms_count = Column(SmallInteger)
    security_issue_count = Column(SmallInteger, default=0)
    seo_issue_count = Column(SmallInteger, default=0)
    content_issue_count = Column(SmallInteger, default=0)
    image_issue_count = Column(SmallInteger, default=0)
    structure_issue_count = Column(SmallInteger, default=0)
    link_issue_count = Column(SmallInteger, default=0)
    button_issue_count = Column(SmallInteger, default=0)
    technical_issue_count = Column(SmallInteger, default=0)
    report_json = Column(JSONB)
    report_text = Column(Text)

    website = relationship("Website", back_populates="runs")
    sections = relationship("AuditRunSection", back_populates="run", cascade="all, delete-orphan")
    issues = relationship("AuditIssue", back_populates="run", cascade="all, delete-orphan")


class AuditRunSection(Base):
    __tablename__ = "audit_run_sections"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    run_id = Column(UUID(as_uuid=True), ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False)
    section_key = Column(Text, nullable=False)
    section_label = Column(Text)
    passed = Column(Boolean, nullable=False, default=False)
    status = Column(Text)
    issue_count = Column(SmallInteger)
    check_description = Column(Text)
    result_description = Column(Text)
    details_json = Column(JSONB)

    run = relationship("AuditRun", back_populates="sections")


class AuditIssue(Base):
    __tablename__ = "audit_issues"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    run_id = Column(UUID(as_uuid=True), ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False)
    category = Column(Text, nullable=False)
    severity = Column(Text, nullable=False, default="info")
    message = Column(Text, nullable=False)
    line_no = Column(Integer)
    line_hint = Column(Text)

    run = relationship("AuditRun", back_populates="issues")


class GlobalSetting(Base):
    __tablename__ = "global_settings"

    key = Column(Text, primary_key=True)
    value = Column(JSONB, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
