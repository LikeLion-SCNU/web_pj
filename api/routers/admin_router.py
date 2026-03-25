from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from auth import require_admin
from database import get_db
from models import User, Mission, Submission, Review
from schemas import AdminReviewUpdate
from services.email_service import send_approval_notification

router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    total_users = db.query(User).filter(User.role == "baby_lion").count()
    total_subs = db.query(Submission).count()
    passed = db.query(Submission).filter(Submission.status == "passed").count()
    rejected = db.query(Submission).filter(Submission.status == "rejected").count()
    reviewing = db.query(Submission).filter(Submission.status == "reviewing").count()
    pending = db.query(Submission).filter(Submission.status == "pending").count()

    track_stats = (
        db.query(User.track, func.count(User.id))
        .filter(User.role == "baby_lion")
        .group_by(User.track)
        .all()
    )

    return {
        "total_users": total_users,
        "total_submissions": total_subs,
        "passed_count": passed,
        "rejected_count": rejected,
        "reviewing_count": reviewing,
        "pending_count": pending,
        "track_stats": [{"track": t, "count": c} for t, c in track_stats],
    }


@router.get("/pending-users")
def pending_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """이메일 인증 완료 + 승인 대기 중인 사용자 목록"""
    users = (
        db.query(User)
        .filter(User.email_verified == True, User.approved == False, User.role == "baby_lion")
        .order_by(User.created_at.desc())
        .all()
    )
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "track": u.track,
            "team": u.team,
            "generation": u.generation,
            "created_at": u.created_at.isoformat(),
        }
        for u in users
    ]


@router.patch("/users/{user_id}/approve")
def approve_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다")

    user.approved = True
    db.commit()

    send_approval_notification(user.email, user.name, approved=True)
    return {"message": f"{user.name}님의 가입을 승인했습니다."}


@router.patch("/users/{user_id}/reject")
def reject_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다")

    send_approval_notification(user.email, user.name, approved=False)
    db.delete(user)
    db.commit()
    return {"message": f"{user.name}님의 가입을 거절했습니다."}


@router.get("/submissions")
def list_submissions(
    track: str = Query(None),
    mission_number: int = Query(None),
    status: str = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = db.query(Submission).join(Mission).join(User)

    if track:
        q = q.filter(Mission.track == track)
    if mission_number:
        q = q.filter(Mission.number == mission_number)
    if status:
        q = q.filter(Submission.status == status)

    subs = q.order_by(Submission.submitted_at.desc()).limit(100).all()

    return [
        {
            "id": s.id,
            "user_name": s.user.name,
            "user_email": s.user.email,
            "track": s.mission.track,
            "mission_number": s.mission.number,
            "mission_title": s.mission.title,
            "attempt": s.attempt,
            "status": s.status,
            "github_url": s.github_url,
            "deploy_url": s.deploy_url,
            "figma_url": s.figma_url,
            "screenshot_path": s.screenshot_path,
            "description": s.description,
            "submitted_at": s.submitted_at.isoformat(),
            "review": {
                "ai_score": s.review.ai_score,
                "ai_summary": s.review.ai_summary,
                "ai_feedback": s.review.ai_feedback,
                "admin_approved": s.review.admin_approved,
                "admin_comment": s.review.admin_comment,
            } if s.review else None,
        }
        for s in subs
    ]


@router.patch("/submissions/{submission_id}")
def review_submission(
    submission_id: int,
    data: AdminReviewUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    sub = db.query(Submission).filter(Submission.id == submission_id).first()
    if not sub:
        raise HTTPException(404, "제출을 찾을 수 없습니다")

    review = db.query(Review).filter(Review.submission_id == submission_id).first()
    if not review:
        review = Review(submission_id=submission_id)
        db.add(review)

    review.admin_approved = data.approved
    review.admin_comment = data.comment
    sub.status = "passed" if data.approved else "rejected"

    db.commit()
    return {"status": sub.status}
