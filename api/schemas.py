from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# Auth
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(..., min_length=8)
    track: str  # planning, design, frontend, backend
    team: Optional[int] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    track: str
    team: Optional[int]
    role: str
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


# Mission
class MissionResponse(BaseModel):
    id: int
    track: str
    number: int
    title: str
    description: Optional[str]
    checklist: list
    submission_type: str
    estimated_hours: int
    my_status: Optional[str] = None  # 내 제출 상태

    class Config:
        from_attributes = True


# Submission
class SubmissionCreate(BaseModel):
    mission_id: int
    github_url: Optional[str] = None
    deploy_url: Optional[str] = None
    figma_url: Optional[str] = None
    description: Optional[str] = None


class SubmissionResponse(BaseModel):
    id: int
    user_id: int
    mission_id: int
    attempt: int
    github_url: Optional[str]
    deploy_url: Optional[str]
    figma_url: Optional[str]
    screenshot_path: Optional[str]
    description: Optional[str]
    status: str
    submitted_at: datetime
    user_name: Optional[str] = None
    mission_title: Optional[str] = None
    review: Optional["ReviewResponse"] = None

    class Config:
        from_attributes = True


# Review
class ReviewResponse(BaseModel):
    id: int
    ai_score: Optional[int]
    ai_feedback: Optional[list]
    ai_summary: Optional[str]
    admin_approved: Optional[bool]
    admin_comment: Optional[str]
    reviewed_at: datetime

    class Config:
        from_attributes = True


class AdminReviewUpdate(BaseModel):
    approved: bool
    comment: Optional[str] = None


# Dashboard
class DashboardStats(BaseModel):
    total_users: int
    total_submissions: int
    passed_count: int
    rejected_count: int
    pending_count: int
    track_stats: list
