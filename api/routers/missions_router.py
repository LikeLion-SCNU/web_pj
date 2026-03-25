from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_user
from database import get_db
from models import User, Mission, Submission

router = APIRouter(prefix="/api/missions", tags=["missions"])


@router.get("")
def list_missions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    missions = db.query(Mission).filter(Mission.track == user.track).order_by(Mission.number).all()

    result = []
    for m in missions:
        sub = (
            db.query(Submission)
            .filter(Submission.user_id == user.id, Submission.mission_id == m.id)
            .order_by(Submission.attempt.desc())
            .first()
        )
        result.append({
            "id": m.id,
            "track": m.track,
            "number": m.number,
            "title": m.title,
            "description": m.description,
            "submission_type": m.submission_type,
            "estimated_hours": m.estimated_hours,
            "my_status": sub.status if sub else None,
            "my_attempt": sub.attempt if sub else 0,
        })
    return result


@router.get("/{mission_id}")
def get_mission(mission_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(404, "미션을 찾을 수 없습니다")

    submissions = (
        db.query(Submission)
        .filter(Submission.user_id == user.id, Submission.mission_id == mission_id)
        .order_by(Submission.attempt.desc())
        .all()
    )

    return {
        "id": mission.id,
        "track": mission.track,
        "number": mission.number,
        "title": mission.title,
        "description": mission.description,
        "checklist": mission.checklist,
        "submission_type": mission.submission_type,
        "estimated_hours": mission.estimated_hours,
        "submissions": [
            {
                "id": s.id,
                "attempt": s.attempt,
                "status": s.status,
                "submitted_at": s.submitted_at.isoformat(),
                "github_url": s.github_url,
                "deploy_url": s.deploy_url,
                "figma_url": s.figma_url,
                "screenshot_path": s.screenshot_path,
                "review": {
                    "ai_score": s.review.ai_score,
                    "ai_summary": s.review.ai_summary,
                    "ai_feedback": s.review.ai_feedback,
                    "admin_approved": s.review.admin_approved,
                    "admin_comment": s.review.admin_comment,
                } if s.review else None,
            }
            for s in submissions
        ],
    }
