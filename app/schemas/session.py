from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class SessionCreateResponse(BaseModel):
    session_id: UUID
    status: str


class SessionSubmit(BaseModel):
    street: str
    city: str
    state: str
    latitude: float
    longitude: float
    organization_name: Optional[str] = None
    organization_type: Optional[str] = None


class SessionResult(BaseModel):
    session_id: UUID
    status: str
    trust_score: Optional[int] = None
    verification_results: Optional[Dict[str, Any]] = None
    extracted_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    class Config:
        from_attributes = True
