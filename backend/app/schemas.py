from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel


class WebhookMessage(BaseModel):
    phone_number: str
    body: str
    timestamp: Optional[datetime] = None


class MessageOut(BaseModel):
    id: int
    phone_number: str
    body: str
    timestamp: datetime
    language: Optional[str]
    is_from_admin: bool

    class Config:
        from_attributes = True


class SendReplyIn(BaseModel):
    phone_number: str
    body: str


class MessagesResponse(BaseModel):
    messages: List[MessageOut]


# New schemas for tools and admin
class FeedbackIn(BaseModel):
    phone_number: str
    category: str
    message: Optional[str] = None
    location: Optional[str] = None
    zone: Optional[str] = None


class FeedbackOut(BaseModel):
    id: int
    phone_number: str
    category: str
    status: str
    location: Optional[str]
    zone: Optional[str]
    message: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class FeedbackListOut(BaseModel):
    items: List[FeedbackOut]


# Templates CRUD
class TemplateIn(BaseModel):
    key: str
    text: str


class TemplateOut(BaseModel):
    id: int
    key: str
    text: str

    class Config:
        from_attributes = True


class NoticeIn(BaseModel):
    message: str
    zones: Optional[List[str]] = None
    phone_numbers: Optional[List[str]] = None


class NoticeOut(BaseModel):
    id: int
    message: str
    zones: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class TranslateIn(BaseModel):
    text: str
    target_language: str


class TranslateOut(BaseModel):
    text: str
    detected_language: str
    target_language: str


# AI reply schemas
class AIReplyIn(BaseModel):
    text: str
    phone_number: Optional[str] = None
    send: bool = False


class AIReplyOut(BaseModel):
    reply: str
    raw: Optional[dict] = None


# Phase 1+: issue assignment / status update
class IssueStatusUpdateIn(BaseModel):
    id: int
    status: str  # new | in_progress | resolved


class IssueAssignIn(BaseModel):
    feedback_id: int
    assignee: str
    note: Optional[str] = None


class IssueAssignOut(BaseModel):
    id: int
    feedback_id: int
    assignee: str
    note: Optional[str]
    assigned_at: datetime

    class Config:
        from_attributes = True


# Phase 1+: contact metadata
class ContactUpdateIn(BaseModel):
    phone_number: str
    name: Optional[str] = None
    zone: Optional[str] = None
    language_pref: Optional[str] = None


class ContactOut(BaseModel):
    phone_number: str
    name: Optional[str]
    zone: Optional[str]
    language_pref: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# Phase 1+: classify intent
class ClassifyIn(BaseModel):
    text: str


class ClassifyOut(BaseModel):
    intent: str
    confidence: float
    reason: Optional[str] = None


# Phase 1+: summarize conversation
class SummarizeIn(BaseModel):
    phone_number: str
    max_messages: Optional[int] = 50


class SummarizeOut(BaseModel):
    summary: str


# Phase 1+: send media via Samwad
class SendMediaIn(BaseModel):
    phone_number: str
    image_url: str
    body: Optional[str] = None


# Phase 1+: escalate emergency
class EscalateIn(BaseModel):
    message: str
    phone_numbers: Optional[List[str]] = None
    severity: Optional[str] = None
    location: Optional[str] = None


# Location tools
class RequestLocationIn(BaseModel):
    phone_number: str
    body: Optional[str] = "Please share your location"


class SendLocationPinIn(BaseModel):
    phone_number: str
    latitude: float
    longitude: float
    name: Optional[str] = None
    address: Optional[str] = None


# Phase 1+: zone ETA config admin
class ZoneConfigIn(BaseModel):
    zone: str
    sanitation_eta_minutes: Optional[int] = None
    medical_eta_minutes: Optional[int] = None


class ZoneConfigOut(BaseModel):
    zone: str
    sanitation_eta_minutes: Optional[int]
    medical_eta_minutes: Optional[int]
    updated_at: datetime

    class Config:
        from_attributes = True


# Agent tools registry and approvals
class AgentToolOut(BaseModel):
    name: str
    risk: str  # low | medium | high
    description: str
    params: dict


class AgentInvokeIn(BaseModel):
    tool: str
    args: dict
    dry_run: bool = False


class AgentInvokeOut(BaseModel):
    status: str  # ok | pending | error
    approval_id: Optional[int] = None
    result: Optional[dict] = None
    error: Optional[str] = None


class ApprovalOut(BaseModel):
    id: int
    tool_name: str
    args: dict
    status: str
    result: Optional[dict]
    created_at: datetime
    decided_at: Optional[datetime]
    decided_by: Optional[str]

    class Config:
        from_attributes = True


class ApprovalDecisionIn(BaseModel):
    approve: bool
    actor: Optional[str] = None
    note: Optional[str] = None
