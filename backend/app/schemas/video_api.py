from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

class VideoProjectCreate(BaseModel):
    title: str = Field(min_length=1, max_length=150, default="Untitled Documentary")
    description: Optional[str] = ""
    aspect_ratio: str = Field(default="16:9")
    resolution: str = Field(default="1080p")
    fps: int = Field(default=30, ge=15, le=60)

    @field_validator('title')
    @classmethod
    def validate_title(cls, v: str) -> str:
        s = v.strip() if v else ""
        if not s:
            raise ValueError("Project title cannot be empty.")
        return s

    @field_validator('description', mode='before')
    @classmethod
    def normalize_description(cls, v: Any) -> str:
        if v is None:
            return ""
        return str(v).strip()

    @field_validator('resolution', mode='before')
    @classmethod
    def normalize_resolution(cls, v: Any) -> str:
        if not v:
            return "1080p"
        s = str(v).strip().lower()
        if s in ["1920x1080", "1080", "1080p", "full hd", "fhd"]:
            return "1080p"
        if s in ["2560x1440", "1440", "1440p", "2k", "qhd"]:
            return "1440p"
        if s in ["1280x720", "720", "720p", "hd"]:
            return "720p"
        if s in ["3840x2160", "4k", "2160", "2160p", "uhd"]:
            return "4k"
        if s in ["720p", "1080p", "1440p", "4k"]:
            return s
        raise ValueError(f"Invalid resolution '{v}'. Must be '720p', '1080p', '1440p', or '4k'.")

    @field_validator('aspect_ratio', mode='before')
    @classmethod
    def normalize_aspect_ratio(cls, v: Any) -> str:
        if not v:
            return "16:9"
        s = str(v).strip()
        if s in ["16:9", "9:16", "1:1"]:
            return s
        raise ValueError(f"Invalid aspect ratio '{v}'. Must be '16:9', '9:16', or '1:1'.")

    @field_validator('fps', mode='before')
    @classmethod
    def normalize_fps(cls, v: Any) -> int:
        if v is None or v == "":
            return 30
        try:
            val = int(v)
            if val < 15 or val > 60:
                raise ValueError("FPS must be between 15 and 60.")
            return val
        except (TypeError, ValueError) as e:
            if isinstance(e, ValueError) and "FPS must be between" in str(e):
                raise e
            raise ValueError(f"Invalid fps value: '{v}'. Must be an integer between 15 and 60.")

class VideoProjectUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    aspect_ratio: Optional[str] = None
    resolution: Optional[str] = None
    fps: Optional[int] = None

class VideoAssetResponse(BaseModel):
    id: str
    project_id: str
    asset_type: str
    filename: str
    url: str
    file_size: int
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    duration: Optional[float] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VoiceoverResponse(BaseModel):
    id: str
    project_id: str
    asset_id: str
    filename: str
    url: str
    duration: float
    sample_rate: int
    channels: int
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class TranscriptSegmentResponse(BaseModel):
    id: str
    segment_index: int
    text: str
    start_time: float
    end_time: float
    duration: float
    keywords_json: List[str] = []

    model_config = ConfigDict(from_attributes=True)

class SceneResponse(BaseModel):
    id: str
    project_id: str
    scene_index: int
    title: str
    narrative_text: str
    start_time: float
    end_time: float
    duration: float
    primary_asset_id: Optional[str] = None
    primary_asset: Optional[VideoAssetResponse] = None

    model_config = ConfigDict(from_attributes=True)

class TimelineClipResponse(BaseModel):
    id: str
    project_id: str
    scene_id: Optional[str] = None
    asset_id: str
    track_index: int
    clip_index: int
    start_time: float
    end_time: float
    duration: float
    motion_type: str
    scale_factor: float
    framing: str
    asset: Optional[VideoAssetResponse] = None

    model_config = ConfigDict(from_attributes=True)

class TimelineTransitionResponse(BaseModel):
    id: str
    project_id: str
    from_clip_id: Optional[str] = None
    to_clip_id: Optional[str] = None
    transition_type: str
    duration: float
    offset_time: float

    model_config = ConfigDict(from_attributes=True)

class ClipUpdateItem(BaseModel):
    id: str
    asset_id: str
    start_time: float
    end_time: float
    duration: float
    motion_type: str = "zoom_in"
    scale_factor: float = 1.15
    framing: str = "cover"

class TimelineUpdateRequest(BaseModel):
    clips: List[ClipUpdateItem]
    transitions: Optional[List[Dict[str, Any]]] = None

class RenderSubmitRequest(BaseModel):
    aspect_ratio: Optional[str] = "16:9"
    resolution: Optional[str] = "1080p"
    format: Optional[str] = "mp4"
    fps: Optional[int] = 30

    @field_validator('resolution', mode='before')
    @classmethod
    def normalize_res(cls, v: Any) -> str:
        if not v:
            return "1080p"
        s = str(v).strip().lower()
        if s in ["1920x1080", "1080", "1080p", "full hd", "fhd"]:
            return "1080p"
        if s in ["2560x1440", "1440", "1440p", "2k", "qhd"]:
            return "1440p"
        if s in ["3840x2160", "4k", "2160", "2160p", "uhd"]:
            return "4k"
        if s in ["1280x720", "720", "720p", "hd"]:
            return "720p"
        if s in ["720p", "1080p", "1440p", "4k"]:
            return s
        return "1080p"

    @field_validator('aspect_ratio', mode='before')
    @classmethod
    def normalize_ar(cls, v: Any) -> str:
        if not v:
            return "16:9"
        s = str(v).strip()
        if s in ["16:9", "9:16", "1:1"]:
            return s
        return "16:9"

    @field_validator('fps', mode='before')
    @classmethod
    def normalize_fps(cls, v: Any) -> int:
        if v is None or v == "":
            return 30
        try:
            return int(v)
        except Exception:
            return 30

class RenderJobResponse(BaseModel):
    id: str
    project_id: str
    status: str
    progress: float
    current_step: str
    error_message: Optional[str] = None
    resolution: str
    aspect_ratio: str
    fps: int
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class RenderOutputResponse(BaseModel):
    id: str
    project_id: str
    render_job_id: str
    filename: str
    download_url: str
    duration: float
    file_size: int
    format: str
    codec: str
    resolution: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VideoProjectSummaryResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    aspect_ratio: str
    resolution: str
    fps: int
    total_duration: float
    assets_count: int = 0
    scenes_count: int = 0
    thumbnail_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class VideoProjectDetailResponse(BaseModel):
    id: str
    title: str
    description: str
    status: str
    aspect_ratio: str
    resolution: str
    fps: int
    total_duration: float
    assets: List[VideoAssetResponse] = []
    voiceover: Optional[VoiceoverResponse] = None
    scenes: List[SceneResponse] = []
    timeline_clips: List[TimelineClipResponse] = []
    transitions: List[TimelineTransitionResponse] = []
    render_outputs: List[RenderOutputResponse] = []
    latest_render: Optional[RenderJobResponse] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
