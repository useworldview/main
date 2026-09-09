"""
Pydantic request/response models for the API.
"""

from pydantic import BaseModel, Field, HttpUrl
from typing import Optional
from enum import Enum


# ============================================================================
# Enums
# ============================================================================

class ResearchGoalType(str, Enum):
    TEMPLATE = "template"
    CUSTOM = "custom"


class StudyStatus(str, Enum):
    DRAFT = "draft"
    ANALYZING_SITE = "analyzing_site"
    AUDIENCE_READY = "audience_ready"
    PERSONAS_READY = "personas_ready"
    DEPLOYING = "deploying"
    RUNNING = "running"
    ANALYZING_RESULTS = "analyzing_results"
    COMPLETED = "completed"
    FAILED = "failed"


class SessionStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"


class SessionOutcome(str, Enum):
    COMPLETED = "completed"
    ABANDONED = "abandoned"
    ERROR = "error"


# ============================================================================
# Request Models
# ============================================================================

class ResearchGoal(BaseModel):
    type: ResearchGoalType
    value: str


class CreateStudyRequest(BaseModel):
    target_url: str
    research_goals: list[ResearchGoal] = Field(min_length=1)
    confirmed_authorized: bool = False


class GeneratePersonasRequest(BaseModel):
    segment_ids: list[str] = Field(min_length=1)
    personas_per_segment: int = Field(default=1, ge=1, le=5)


class RetryFailedSessionsRequest(BaseModel):
    pass


# ============================================================================
# Response Models
# ============================================================================

class HealthResponse(BaseModel):
    status: str = "ok"


class StudyResponse(BaseModel):
    id: str
    user_id: str
    title: Optional[str]
    research_goals: list
    target_url: str
    status: str
    step_budget_per_session: int
    max_pages: int
    site_context: Optional[dict]
    summary_metrics: Optional[dict]
    error_message: Optional[str]
    confirmed_authorized: bool
    created_at: str
    updated_at: str
    completed_at: Optional[str]


class MessageResponse(BaseModel):
    message: str
    study_id: Optional[str] = None
    job_id: Optional[str] = None
