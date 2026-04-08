import re
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


# Auth
class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    track: str  # planning, design, frontend, backend
    team: Optional[int] = None
    generation: Optional[int] = None  # 기수 (없으면 현재 기수)
    turnstile_token: Optional[str] = None

    @field_validator("password")
    @classmethod
    def password_complexity(cls, v: str) -> str:
        if not re.search(r"[A-Za-z]", v):
            raise ValueError("비밀번호에 영문자를 포함해야 합니다")
        if not re.search(r"\d", v):
            raise ValueError("비밀번호에 숫자를 포함해야 합니다")
        return v


class EmailVerify(BaseModel):
    email: EmailStr
    code: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)
    turnstile_token: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    track: str
    team: Optional[int]
    generation: int
    role: str
    email_verified: bool
    approved: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class AdminReviewUpdate(BaseModel):
    approved: bool
    comment: Optional[str] = None


class SetRoleRequest(BaseModel):
    role: str

    @field_validator("role")
    @classmethod
    def validate_role(cls, v: str) -> str:
        allowed = ("baby_lion", "admin", "tester")
        if v not in allowed:
            raise ValueError(f"역할은 {', '.join(allowed)} 중 하나여야 합니다")
        return v
