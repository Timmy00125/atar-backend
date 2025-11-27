from pydantic import BaseModel, ConfigDict
from typing import Optional, List, Dict, Any, Generic, TypeVar
from uuid import UUID
from datetime import datetime

T = TypeVar("T")


class APIResponse(BaseModel, Generic[T]):
    success: bool
    message: str
    data: Optional[T] = None


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


class TrustScoreBreakdown(BaseModel):
    house_match_score: int = 0
    logistics_match_score: int = 0
    institutional_proofs_score: int = 0
    recency_score: int = 0
    model_config = ConfigDict(extra="allow")


class TrustScoreData(BaseModel):
    trust_score: int
    verdict: str
    breakdown: Optional[TrustScoreBreakdown] = None


class SessionResult(BaseModel):
    session_id: UUID
    status: str
    trust_score: Optional[int] = None
    trust_analysis: Optional[TrustScoreData] = None
    verification_results: Optional[Dict[str, Any]] = None
    extracted_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
