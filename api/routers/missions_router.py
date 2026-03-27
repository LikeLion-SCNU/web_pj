from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from auth import get_current_user
from database import get_db
from models import User, Mission, Submission

router = APIRouter(prefix="/api/missions", tags=["missions"])


def _utcnow():
    """naive UTC datetime (DB DateTime 컬럼과 비교 호환용)"""
    from datetime import timezone
    return datetime.now(timezone.utc).replace(tzinfo=None)


@router.get("")
def list_missions(track: str = None, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 운영진/테스터는 트랙 선택 가능, 일반 사용자는 본인 트랙만
    selected_track = track if (user.role in ("admin", "tester") and track) else user.track
    missions = db.query(Mission).filter(Mission.track == selected_track).order_by(Mission.number).all()

    # N+1 방지: 사용자의 모든 제출을 한 번에 조회
    mission_ids = [m.id for m in missions]
    user_subs = (
        db.query(Submission)
        .filter(Submission.user_id == user.id, Submission.mission_id.in_(mission_ids))
        .all()
    ) if mission_ids else []
    # mission_id → 최신 시도 매핑
    sub_by_mission = {}
    for s in user_subs:
        if s.mission_id not in sub_by_mission or s.attempt > sub_by_mission[s.mission_id].attempt:
            sub_by_mission[s.mission_id] = s

    result = []
    for m in missions:
        sub = sub_by_mission.get(m.id)
        now = _utcnow()
        if user.role in ("admin", "tester"):
            period_status = "open"
        elif m.start_date and now < m.start_date:
            period_status = "upcoming"
        elif m.end_date and now > m.end_date:
            period_status = "closed"
        else:
            period_status = "open"

        result.append({
            "id": m.id,
            "track": m.track,
            "number": m.number,
            "title": m.title,
            "description": m.description,
            "submission_type": m.submission_type,
            "estimated_hours": m.estimated_hours,
            "pbl_link": m.pbl_link,
            "start_date": m.start_date.isoformat() if m.start_date else None,
            "end_date": m.end_date.isoformat() if m.end_date else None,
            "period_status": period_status,
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
        .options(joinedload(Submission.review))
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
        "pbl_link": mission.pbl_link,
        "start_date": mission.start_date.isoformat() if mission.start_date else None,
        "end_date": mission.end_date.isoformat() if mission.end_date else None,
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
