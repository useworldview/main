"""
Job type constants and payload schemas.
"""

from enum import Enum
from pydantic import BaseModel
from typing import Optional


class JobType(str, Enum):
    ANALYZE_SITE = "analyze_site"
    GENERATE_PERSONAS = "generate_personas"
    RUN_AGENT_SESSION = "run_agent_session"
    ANALYZE_SESSION = "analyze_session"
    SYNTHESIZE_STUDY = "synthesize_study"


class AnalyzeSitePayload(BaseModel):
    study_id: str
    target_url: str
    research_goals: list[dict]


class GeneratePersonasPayload(BaseModel):
    study_id: str
    segment_ids: list[str]
    personas_per_segment: int = 1


class RunAgentSessionPayload(BaseModel):
    session_id: str
    study_id: str
    persona_id: str
    target_url: str
    step_budget: int = 40
    max_pages: int = 5


class AnalyzeSessionPayload(BaseModel):
    session_id: str
    study_id: str
    persona_id: str


class SynthesizeStudyPayload(BaseModel):
    study_id: str
