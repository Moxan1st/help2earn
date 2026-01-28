"""
Pydantic models for API request/response schemas.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ============ Facility Schemas ============

class FacilityBase(BaseModel):
    """Base facility model."""
    type: str = Field(..., description="Facility type: ramp, toilet, elevator, wheelchair")
    latitude: float = Field(..., ge=-90, le=90, description="Latitude coordinate")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude coordinate")


class FacilityCreate(FacilityBase):
    """Request model for creating a facility."""
    image_url: Optional[str] = None
    ai_analysis: Optional[str] = None
    contributor_address: str = Field(..., description="Contributor's wallet address")


class FacilityResponse(FacilityBase):
    """Response model for a facility."""
    id: str
    image_url: str
    ai_analysis: Optional[str] = None
    contributor_address: str
    distance: Optional[float] = Field(None, description="Distance from query point in meters")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FacilityListResponse(BaseModel):
    """Response model for facility list."""
    facilities: List[FacilityResponse]
    count: int


# ============ Upload Schemas ============

class UploadRequest(BaseModel):
    """Request model for facility upload."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    wallet_address: str = Field(..., min_length=42, max_length=42)


class UploadResponse(BaseModel):
    """Response model for upload result."""
    success: bool
    message: str
    facility_id: Optional[str] = None
    facility_type: Optional[str] = None
    condition: Optional[str] = None
    reward_amount: Optional[int] = None
    tx_hash: Optional[str] = None
    reason: Optional[str] = None


# ============ Reward Schemas ============

class RewardRecord(BaseModel):
    """Model for a single reward record."""
    id: str
    facility_id: str
    facility_type: Optional[str] = None
    amount: int
    tx_hash: Optional[str] = None
    created_at: datetime


class UserRewardsResponse(BaseModel):
    """Response model for user rewards."""
    wallet_address: str
    rewards: List[RewardRecord]
    total_earned: int
    contribution_count: int


# ============ Query Schemas ============

class NearbyQuery(BaseModel):
    """Query parameters for nearby facilities."""
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    radius: int = Field(default=200, ge=10, le=5000, description="Search radius in meters")
    facility_type: Optional[str] = Field(None, description="Filter by type")


# ============ Vision Analysis Schemas ============

class VisionAnalysis(BaseModel):
    """Model for vision analysis result."""
    is_valid: bool
    facility_type: Optional[str] = None
    condition: Optional[str] = None
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    details: Optional[dict] = None


# ============ Fraud Check Schemas ============

class FraudCheckResult(BaseModel):
    """Model for fraud check result."""
    is_fraud: bool
    reward_amount: int
    reason: str
    existing_facility_id: Optional[str] = None


class RateLimitResult(BaseModel):
    """Model for rate limit check result."""
    allowed: bool
    reason: str
    hourly_count: Optional[int] = None
    daily_count: Optional[int] = None
    remaining_hourly: Optional[int] = None
    remaining_daily: Optional[int] = None
    wait_minutes: Optional[int] = None


# ============ Health Check Schemas ============

class HealthCheck(BaseModel):
    """Health check response."""
    status: str = "ok"
    version: str = "1.0.0"
    services: dict = Field(default_factory=dict)


# ============ Error Schemas ============

class ErrorResponse(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None
