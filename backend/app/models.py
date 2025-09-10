from __future__ import annotations
from datetime import datetime
from typing import Optional
from sqlmodel import Field, SQLModel


class Message(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone_number: str
    body: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    language: Optional[str] = None
    is_from_admin: bool = False


class ReplyTemplate(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    key: str
    text: str


# New domain models
class Feedback(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    phone_number: str
    category: str  # sanitation | emergency | info | other
    status: str = "new"  # new | in_progress | resolved
    location: Optional[str] = None
    zone: Optional[str] = None
    message: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AdminNotice(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    message: str
    zones: Optional[str] = None  # comma-separated zones
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Phase 1+: Contact metadata
class Contact(SQLModel, table=True):
    phone_number: str = Field(primary_key=True)
    name: Optional[str] = None
    zone: Optional[str] = None
    language_pref: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


# Phase 1+: Assignment for feedback (separate table to avoid altering Feedback)
class FeedbackAssignment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    feedback_id: int
    assignee: str
    note: Optional[str] = None
    assigned_at: datetime = Field(default_factory=datetime.utcnow)


# Phase 1+: Per-zone ETA configuration
class ZoneConfig(SQLModel, table=True):
    zone: str = Field(primary_key=True)
    sanitation_eta_minutes: Optional[int] = None
    medical_eta_minutes: Optional[int] = None
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# Agent approvals for high-risk actions
class Approval(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    tool_name: str
    args_json: str  # stored as JSON string
    status: str = "pending"  # pending | approved | denied
    result_json: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    decided_at: Optional[datetime] = None
    decided_by: Optional[str] = None
