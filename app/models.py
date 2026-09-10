from datetime import datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class EventType(str, Enum):
    DEAL_CREATED = "DEAL_CREATED"
    MESSAGE_RECEIVED = "MESSAGE_RECEIVED"
    CALL_RECORD_READY = "CALL_RECORD_READY"
    DEAL_UPDATED = "DEAL_UPDATED"


class Event(BaseModel):
    event_id: str
    type: EventType
    deal_id: str
    timestamp: datetime
    source: str | None = None
    external_id: str | None = None
    payload: dict[str, Any] = Field(default_factory=dict)


class Client(BaseModel):
    name: str | None = None
    phone: str | None = None


class Message(BaseModel):
    id: str
    timestamp: datetime
    role: Literal["client", "manager", "unknown"]
    text: str
    source: str = "crm"


class Call(BaseModel):
    id: str
    timestamp: datetime
    duration_seconds: int
    transcript: str | None = None
    audio_url: str | None = None
    transcription_status: Literal["not_needed", "pending", "ready", "failed"] = "ready"


class LeadInput(BaseModel):
    deal_id: str
    title: str | None = None
    stage: str | None = None
    client: Client = Field(default_factory=Client)
    crm_fields: dict[str, Any] = Field(default_factory=dict)
    messages: list[Message] = Field(default_factory=list)
    calls: list[Call] = Field(default_factory=list)


class FieldSource(str, Enum):
    AI = "ai"
    MANAGER = "manager"
    SYSTEM = "system"


class QualificationField(BaseModel):
    value: Any = None
    source: FieldSource
    confidence: float | None = Field(default=None, ge=0, le=1)
    updated_at: datetime
    evidence: list[str] = Field(default_factory=list)


class QualificationState(BaseModel):
    fields: dict[str, QualificationField] = Field(default_factory=dict)
    ai_score: int | None = Field(default=None, ge=0, le=100)
    manager_score: int | None = Field(default=None, ge=0, le=100)
    manager_reason: str | None = None
    alerts: list[str] = Field(default_factory=list)


class AIFieldSuggestion(BaseModel):
    value: Any = None
    confidence: float = Field(ge=0, le=1)
    evidence: list[str] = Field(default_factory=list)


class AIAnalysis(BaseModel):
    fields: dict[str, AIFieldSuggestion] = Field(default_factory=dict)
    intent: str = "unknown"
    object_priority: str = "normal"
    client_summary: str = ""
    client_pain: str | None = None
    contractor_expectations: str | None = None
    red_flags: list[str] = Field(default_factory=list)
    next_step: str | None = None
    next_contact_date: str | None = None


class QualificationResult(BaseModel):
    deal_id: str
    score: int = Field(ge=0, le=100)
    intent_score: int = Field(default=0, ge=0, le=100)
    quality: Literal["high", "medium", "low", "insufficient_data"]
    intent: str
    object_priority: str
    client_summary: str
    fields: dict[str, QualificationField]
    red_flags: list[str]
    alerts: list[str]
    missing_data: list[str]
    next_step: str | None
    next_contact_date: str | None
    explanation: str
    manager_score: int | None = Field(default=None, ge=0, le=100)
    manager_reason: str | None = None
    final_score: int = Field(ge=0, le=100)
