from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

# --- Common ---
class StandardResponse(BaseModel):
    data: Any
    request_id: Optional[str] = None

class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None

class ErrorResponse(BaseModel):
    error: ErrorDetail
    request_id: Optional[str] = None

# --- Auth ---
class UserSignup(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(default="Creator")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: Dict[str, Any]

class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    avatar_url: Optional[str] = None
    role: str
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Voice Settings & Presets ---
class VoiceSettings(BaseModel):
    speed: float = Field(default=1.0, ge=0.25, le=4.0)
    pitch: float = Field(default=0.0, ge=-20.0, le=20.0)
    stability: float = Field(default=0.5, ge=0.0, le=1.0)
    similarity: float = Field(default=0.75, ge=0.0, le=1.0)
    style: float = Field(default=0.0, ge=0.0, le=1.0)
    language: str = "en"
    format: str = "mp3"

# --- Voices ---
class VoiceResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    language: str
    locale: str
    accent: str
    gender: str
    style: str
    styles: List[str] = Field(default_factory=list)
    tier: str  # free, standard, premium, ultra, custom
    provider: Optional[str] = "mock"
    type: str = "library"  # cloned, library
    voice_type: str = "library"  # library, clone
    preview_audio_url: Optional[str] = None
    is_public: bool
    commercial_use_allowed: bool
    owner_user_id: Optional[str] = None
    provider_voice_id: Optional[str] = None
    model: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VoiceCloneCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: Optional[str] = ""
    language: str = "en"
    gender: str = "neutral"
    consent_confirmed: bool
    rights_confirmed: bool

# --- Generations ---
class GenerationCreate(BaseModel):
    text: str = Field(min_length=1, max_length=50000)
    voice_id: str
    voice_type: Optional[str] = None  # "cloned" or "library"
    format: str = Field(default="mp3", pattern="^(mp3|wav)$")
    speed: Optional[float] = 1.0
    pitch: Optional[float] = 0.0
    stability: Optional[float] = 0.5
    similarity: Optional[float] = 0.75
    style: Optional[float] = 0.0
    project_document_id: Optional[str] = None

class GenerationResponse(BaseModel):
    id: str
    user_id: str
    voice_id: str
    voice_name: Optional[str] = None
    model: str
    provider: str
    input_characters: int
    estimated_audio_seconds: float
    actual_audio_seconds: float
    format: str
    status: str
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    audio_url: Optional[str] = None
    estimated_cost: float
    settings_json: Dict[str, Any]
    created_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class GenerationListResponse(BaseModel):
    items: List[GenerationResponse]
    total: int
    page: int
    page_size: int

# --- Projects ---
class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    description: Optional[str] = ""

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class ProjectDocumentCreate(BaseModel):
    title: str = "Untitled Script"
    content: str = ""
    language: str = "en"
    voice_id: Optional[str] = None
    settings_json: Optional[Dict[str, Any]] = None

class ProjectDocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
    voice_id: Optional[str] = None
    settings_json: Optional[Dict[str, Any]] = None

class ProjectDocumentResponse(BaseModel):
    id: str
    project_id: str
    title: str
    content: str
    language: str
    voice_id: Optional[str] = None
    settings_json: Dict[str, Any]
    version: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class ProjectResponse(BaseModel):
    id: str
    owner_user_id: str
    name: str
    description: str
    documents: List[ProjectDocumentResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

# --- Billing & Usage ---
class PlanResponse(BaseModel):
    id: str
    name: str
    slug: str
    description: str
    monthly_price: float
    currency: str
    included_characters: int
    included_seconds: int
    allow_cloning: bool
    allow_premium_voices: bool
    allow_api: bool
    allow_commercial_use: bool
    fair_use_limit: int

    model_config = ConfigDict(from_attributes=True)

class SubscriptionResponse(BaseModel):
    id: str
    plan: PlanResponse
    status: str
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool

class UsageSummaryResponse(BaseModel):
    plan_name: str
    plan_slug: str
    characters_used: int
    characters_limit: int
    characters_remaining: int
    seconds_used: float
    generations_count: int
    fair_use_status: str  # healthy, warning, throttled
    can_clone: bool
    can_use_premium: bool
    can_use_api: bool

# --- API Keys ---
class ApiKeyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)

class ApiKeyResponse(BaseModel):
    id: str
    name: str
    key_prefix: str
    last_used_at: Optional[datetime] = None
    created_at: datetime
    revoked_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)

class ApiKeyCreatedResponse(ApiKeyResponse):
    raw_key: str  # ONLY RETURNED ONCE!

# --- Admin ---
class AdminStatsResponse(BaseModel):
    total_users: int
    total_generations: int
    total_characters_generated: int
    total_audio_seconds: float
    active_subscriptions: int
    total_revenue_estimate: float
    provider_cost_estimate: float
    failed_jobs_count: int
