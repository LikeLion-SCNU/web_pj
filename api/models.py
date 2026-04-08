from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, UniqueConstraint
)
from sqlalchemy.orm import relationship

from database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    track = Column(String(20), nullable=False)  # planning, design, frontend, backend
    team = Column(Integer, nullable=True)  # 1~5팀
    generation = Column(Integer, default=14)  # 기수 (14기, 15기...)
    role = Column(String(20), default="baby_lion")  # baby_lion, admin
    email_verified = Column(Boolean, default=False)
    approved = Column(Boolean, default=False)
    verification_code = Column(String(6), nullable=True)
    verification_attempts = Column(Integer, default=0)
    verification_expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    submissions = relationship("Submission", back_populates="user")


class Mission(Base):
    __tablename__ = "missions"

    id = Column(Integer, primary_key=True, index=True)
    track = Column(String(20), nullable=False)
    number = Column(Integer, nullable=False)  # 1~10
    title = Column(String(200), nullable=False)
    description = Column(Text)
    checklist = Column(JSON, nullable=False)  # AI 검사 기준
    submission_type = Column(String(20), nullable=False)  # github, figma, deploy, mixed
    estimated_hours = Column(Integer, default=20)
    pbl_link = Column(String(500), nullable=True)
    start_date = Column(DateTime, nullable=True)
    end_date = Column(DateTime, nullable=True)

    submissions = relationship("Submission", back_populates="mission")

    __table_args__ = (UniqueConstraint("track", "number"),)


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    mission_id = Column(Integer, ForeignKey("missions.id"), nullable=False)
    attempt = Column(Integer, default=1)  # 1~5
    github_url = Column(String(500))
    deploy_url = Column(String(500))
    figma_url = Column(String(500))
    screenshot_path = Column(String(500))
    screenshot_path2 = Column(String(500))
    screenshot_path3 = Column(String(500))
    description = Column(Text)
    status = Column(String(20), default="pending")  # pending, reviewing, passed, rejected
    submitted_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    user = relationship("User", back_populates="submissions")
    mission = relationship("Mission", back_populates="submissions")
    review = relationship("Review", back_populates="submission", uselist=False)


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, index=True)
    submission_id = Column(Integer, ForeignKey("submissions.id"), unique=True, nullable=False)
    ai_score = Column(Integer)  # 0~100
    ai_feedback = Column(JSON)  # 체크리스트별 결과
    ai_summary = Column(Text)
    admin_approved = Column(Boolean)
    admin_comment = Column(Text)
    reviewed_at = Column(DateTime, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))

    submission = relationship("Submission", back_populates="review")
