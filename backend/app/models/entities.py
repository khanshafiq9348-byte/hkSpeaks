from typing import Optional, List, Dict, Any
from datetime import datetime
from sqlalchemy import (
    String, Integer, Float, Boolean, DateTime, ForeignKey, Text, JSON, Enum, Index
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base_class import Base, generate_uuid, utc_now

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    display_name: Mapped[str] = mapped_column(String(100), default="Creator")
    avatar_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)  # active, suspended, deleted
    role: Mapped[str] = mapped_column(String(50), default="user")  # user, admin
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    memberships: Mapped[List["Membership"]] = relationship("Membership", back_populates="user", cascade="all, delete-orphan")
    subscriptions: Mapped[List["Subscription"]] = relationship("Subscription", back_populates="user")
    projects: Mapped[List["Project"]] = relationship("Project", back_populates="user")
    generations: Mapped[List["Generation"]] = relationship("Generation", back_populates="user")
    api_keys: Mapped[List["ApiKey"]] = relationship("ApiKey", back_populates="user")
    credit_ledgers: Mapped[List["CreditLedger"]] = relationship("CreditLedger", back_populates="user")
    voice_clones: Mapped[List["VoiceClone"]] = relationship("VoiceClone", back_populates="user")

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    memberships: Mapped[List["Membership"]] = relationship("Membership", back_populates="organization", cascade="all, delete-orphan")

class Membership(Base):
    __tablename__ = "memberships"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(50), default="member")  # owner, admin, member, viewer
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="memberships")
    organization: Mapped["Organization"] = relationship("Organization", back_populates="memberships")

class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    monthly_price: Mapped[float] = mapped_column(Float, default=0.0)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    included_characters: Mapped[int] = mapped_column(Integer, default=10000)
    included_seconds: Mapped[int] = mapped_column(Integer, default=300)
    allow_cloning: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_premium_voices: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_api: Mapped[bool] = mapped_column(Boolean, default=False)
    allow_commercial_use: Mapped[bool] = mapped_column(Boolean, default=False)
    priority: Mapped[int] = mapped_column(Integer, default=1)  # 1=free, 2=starter, 3=creator, 4=pro, 5=unlimited
    fair_use_limit: Mapped[int] = mapped_column(Integer, default=200000)  # max chars for fair use / month
    active: Mapped[bool] = mapped_column(Boolean, default=True)

class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("plans.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50), default="mock")  # stripe, mock
    provider_customer_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider_subscription_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True)
    status: Mapped[str] = mapped_column(String(50), default="active", index=True)  # active, past_due, canceled
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
    plan: Mapped["Plan"] = relationship("Plan")

class Voice(Base):
    __tablename__ = "voices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(20), default="en", index=True)
    locale: Mapped[str] = mapped_column(String(20), default="en-US")
    accent: Mapped[str] = mapped_column(String(50), default="American")
    gender: Mapped[str] = mapped_column(String(20), default="neutral")  # male, female, neutral
    style: Mapped[str] = mapped_column(String(50), default="natural")
    tier: Mapped[str] = mapped_column(String(50), default="standard", index=True)  # free, standard, premium, ultra, custom
    provider: Mapped[str] = mapped_column(String(50), default="mock")
    provider_voice_id: Mapped[str] = mapped_column(String(100))
    model: Mapped[str] = mapped_column(String(100), default="standard-v1")
    preview_audio_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_clonable: Mapped[bool] = mapped_column(Boolean, default=False)
    commercial_use_allowed: Mapped[bool] = mapped_column(Boolean, default=True)
    license_type: Mapped[str] = mapped_column(String(50), default="standard")
    owner_user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    @property
    def type(self) -> str:
        return "cloned" if (self.tier == "custom" or self.owner_user_id) else "library"

    @property
    def voice_type(self) -> str:
        return "clone" if (self.tier == "custom" or self.owner_user_id) else "library"

    @property
    def styles(self) -> List[str]:
        if not self.style:
            return ["Conversational"]
        tags = [s.strip() for s in self.style.split(",") if s.strip()]
        return tags if tags else ["Conversational"]

class VoiceClone(Base):
    __tablename__ = "voice_clones"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    voice_id: Mapped[str] = mapped_column(String(36), ForeignKey("voices.id", ondelete="CASCADE"), index=True)
    source_audio_key: Mapped[str] = mapped_column(String(512))
    quality_score: Mapped[float] = mapped_column(Float, default=1.0)
    consent_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    rights_confirmed: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(50), default="ready", index=True)  # uploaded, validating, processing, ready, rejected, failed
    provider: Mapped[str] = mapped_column(String(50), default="mock")
    provider_voice_id: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="voice_clones")
    voice: Mapped["Voice"] = relationship("Voice")

class Project(Base):
    __tablename__ = "projects"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    owner_user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="projects")
    documents: Mapped[List["ProjectDocument"]] = relationship("ProjectDocument", back_populates="project", cascade="all, delete-orphan")

class ProjectDocument(Base):
    __tablename__ = "project_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    project_id: Mapped[str] = mapped_column(String(36), ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(150), default="Untitled Script")
    content: Mapped[str] = mapped_column(Text, default="")
    language: Mapped[str] = mapped_column(String(20), default="en")
    voice_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("voices.id"), nullable=True)
    settings_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now)

    project: Mapped["Project"] = relationship("Project", back_populates="documents")

class Generation(Base):
    __tablename__ = "generations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    project_document_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    voice_id: Mapped[str] = mapped_column(String(36), ForeignKey("voices.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50), default="mock")
    model: Mapped[str] = mapped_column(String(100), default="standard-v1")
    input_text: Mapped[str] = mapped_column(Text)
    input_characters: Mapped[int] = mapped_column(Integer, default=0)
    estimated_audio_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    actual_audio_seconds: Mapped[float] = mapped_column(Float, default=0.0)
    format: Mapped[str] = mapped_column(String(10), default="mp3")  # mp3, wav
    status: Mapped[str] = mapped_column(String(50), default="queued", index=True)  # queued, processing, completed, failed, cancelled
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    storage_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    audio_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    provider_request_id: Mapped[Optional[str]] = mapped_column(String(150), nullable=True)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    idempotency_key: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, unique=True, index=True)
    settings_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="generations")
    voice: Mapped["Voice"] = relationship("Voice")

class UsageRecord(Base):
    __tablename__ = "usage_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    generation_id: Mapped[str] = mapped_column(String(36), ForeignKey("generations.id", ondelete="CASCADE"), index=True)
    usage_type: Mapped[str] = mapped_column(String(50), default="tts_generation")
    units: Mapped[int] = mapped_column(Integer, default=0)
    unit_type: Mapped[str] = mapped_column(String(20), default="characters")
    model: Mapped[str] = mapped_column(String(100))
    provider: Mapped[str] = mapped_column(String(50))
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

class CreditLedger(Base):
    __tablename__ = "credit_ledgers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    transaction_type: Mapped[str] = mapped_column(String(50), index=True)  # subscription_grant, generation_reservation, generation_debit, refund, admin_adjustment, promotional_grant
    units: Mapped[int] = mapped_column(Integer)  # positive for grants/refunds, negative for debits/reservations
    reference_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # generation, subscription, payment
    reference_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    description: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

    user: Mapped["User"] = relationship("User", back_populates="credit_ledgers")

class ApiKey(Base):
    __tablename__ = "api_keys"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    name: Mapped[str] = mapped_column(String(100), default="Default Key")
    key_prefix: Mapped[str] = mapped_column(String(16), index=True)
    key_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

    user: Mapped["User"] = relationship("User", back_populates="api_keys")

class ApiRequestLog(Base):
    __tablename__ = "api_request_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    api_key_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    request_id: Mapped[str] = mapped_column(String(100), index=True)
    endpoint: Mapped[str] = mapped_column(String(255))
    voice_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    model: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    input_characters: Mapped[int] = mapped_column(Integer, default=0)
    status_code: Mapped[int] = mapped_column(Integer)
    latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estimated_cost: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)

class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), index=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), default="mock")
    provider_payment_id: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    status: Mapped[str] = mapped_column(String(50), default="succeeded")
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=generate_uuid)
    actor_user_id: Mapped[Optional[str]] = mapped_column(String(36), index=True, nullable=True)
    organization_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource_type: Mapped[str] = mapped_column(String(100), index=True)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    ip_hash: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, index=True)
