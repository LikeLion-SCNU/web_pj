from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session, contains_eager, joinedload

from auth import require_admin
from database import get_db
from models import User, Mission, Submission, Review
from schemas import AdminReviewUpdate, SetRoleRequest
from services.email_service import send_approval_notification
from utils import utcnow

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _get_user_or_404(db: Session, user_id: int) -> User:
    """유저를 조회하고, 없으면 404 반환"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다")
    return user


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    total_users = db.query(User).filter(User.role.in_(["baby_lion", "tester"])).count()

    # N+1 방지: 단일 쿼리로 모든 상태별 카운트 조회
    sub_stats = db.query(
        func.count(Submission.id),
        func.count(case((Submission.status == "passed", 1))),
        func.count(case((Submission.status == "rejected", 1))),
        func.count(case((Submission.status == "reviewing", 1))),
        func.count(case((Submission.status == "pending", 1))),
    ).first()

    track_stats = (
        db.query(User.track, func.count(User.id))
        .filter(User.role.in_(["baby_lion", "tester"]))
        .group_by(User.track)
        .all()
    )

    return {
        "total_users": total_users,
        "total_submissions": sub_stats[0],
        "passed_count": sub_stats[1],
        "rejected_count": sub_stats[2],
        "reviewing_count": sub_stats[3],
        "pending_count": sub_stats[4],
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
def approve_user(user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = _get_user_or_404(db, user_id)
    if user.approved:
        raise HTTPException(400, "이미 승인된 사용자입니다")
    if not user.email_verified:
        raise HTTPException(400, "이메일 인증이 완료되지 않은 사용자입니다")

    user.approved = True
    db.commit()

    background_tasks.add_task(send_approval_notification, user.email, user.name, True)
    return {"message": f"{user.name}님의 가입을 승인했습니다."}


@router.patch("/users/{user_id}/reject")
def reject_user(user_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = _get_user_or_404(db, user_id)
    if user.approved:
        raise HTTPException(400, "이미 승인된 사용자는 거절할 수 없습니다")

    email, name = user.email, user.name
    db.delete(user)
    db.commit()

    background_tasks.add_task(send_approval_notification, email, name, False)
    return {"message": f"{name}님의 가입을 거절했습니다."}


@router.patch("/users/{user_id}/set-role")
def set_user_role(user_id: int, data: SetRoleRequest, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = _get_user_or_404(db, user_id)
    if user.id == admin.id and data.role != "admin":
        raise HTTPException(400, "자기 자신의 운영진 권한은 변경할 수 없습니다")
    old_role = user.role
    user.role = data.role
    db.commit()
    ROLE_LABELS = {"baby_lion": "아기사자", "admin": "운영진", "tester": "테스터"}
    return {"message": f"{user.name}님의 역할을 {ROLE_LABELS.get(old_role, old_role)} → {ROLE_LABELS.get(data.role, data.role)}(으)로 변경했습니다."}


@router.patch("/submissions/{submission_id}")
def admin_review_submission(
    submission_id: int,
    data: AdminReviewUpdate,
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(404, "제출을 찾을 수 없습니다")

    review = db.query(Review).filter(Review.submission_id == submission_id).first()
    if not review:
        review = Review(submission_id=submission_id)
        db.add(review)

    review.admin_approved = data.approved
    review.admin_comment = data.comment
    review.reviewed_at = utcnow()
    submission.status = "passed" if data.approved else "rejected"
    db.commit()

    return {"message": "합격 처리 완료" if data.approved else "반려 처리 완료"}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    user = _get_user_or_404(db, user_id)
    if user.id == admin.id:
        raise HTTPException(400, "자기 자신은 삭제할 수 없습니다")
    if user.role == "admin":
        raise HTTPException(400, "운영진 계정은 먼저 강등 후 삭제해주세요")
    name = user.name
    # 관련 리뷰 → 제출 → 사용자 순서로 삭제
    for sub in user.submissions:
        db.query(Review).filter(Review.submission_id == sub.id).delete()
    db.query(Submission).filter(Submission.user_id == user_id).delete()
    db.delete(user)
    db.commit()
    return {"message": f"{name}님의 계정이 삭제되었습니다."}


@router.get("/users")
def list_all_users(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    users = db.query(User).filter(User.approved == True).order_by(User.role.desc(), User.name).all()
    return [
        {
            "id": u.id,
            "name": u.name,
            "email": u.email,
            "track": u.track,
            "team": u.team,
            "generation": u.generation,
            "role": u.role,
        }
        for u in users
    ]


@router.get("/submissions")
def list_submissions(
    track: str = Query(None),
    mission_number: int = Query(None),
    status: str = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    q = (
        db.query(Submission)
        .join(Mission).join(User)
        .options(contains_eager(Submission.mission), contains_eager(Submission.user), joinedload(Submission.review))
    )

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
            "screenshot_paths": [p for p in [s.screenshot_path, s.screenshot_path2, s.screenshot_path3] if p],
            "description": s.description,
            "team": s.user.team,
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




@router.get("/progress-matrix")
def progress_matrix(
    track: str = Query(None),
    db: Session = Depends(get_db),
    admin: User = Depends(require_admin),
):
    """전체 사용자 과제 현황 매트릭스 (N+1 최적화)"""
    user_q = db.query(User).filter(User.role.in_(["baby_lion", "tester"]), User.approved == True)
    if track:
        user_q = user_q.filter(User.track == track)
    users = user_q.order_by(User.track, User.team, User.name).all()

    if not users:
        return []

    # 모든 관련 트랙의 미션을 한 번에 조회
    tracks = list(set(u.track for u in users))
    all_missions = db.query(Mission).filter(Mission.track.in_(tracks)).order_by(Mission.number).all()
    missions_by_track = {}
    for m in all_missions:
        missions_by_track.setdefault(m.track, []).append(m)

    # 모든 관련 사용자의 제출을 한 번에 조회
    user_ids = [u.id for u in users]
    mission_ids = [m.id for m in all_missions]
    all_subs = db.query(Submission).filter(
        Submission.user_id.in_(user_ids),
        Submission.mission_id.in_(mission_ids),
    ).all()

    # (user_id, mission_id) → 최신 제출 매핑 (error 제외)
    sub_map = {}
    for s in all_subs:
        if s.status == "error":
            continue
        key = (s.user_id, s.mission_id)
        if key not in sub_map or s.attempt > sub_map[key].attempt:
            sub_map[key] = s

    now = utcnow()
    result = []
    for u in users:
        missions = missions_by_track.get(u.track, [])
        mission_statuses = []
        missed_count = 0
        for m in missions:
            sub = sub_map.get((u.id, m.id))
            if sub:
                status = sub.status
            elif m.end_date and now > m.end_date:
                status = "missed"
                missed_count += 1
            elif m.start_date and now >= m.start_date:
                status = "open"
            else:
                status = "upcoming"
            mission_statuses.append({"number": m.number, "status": status})

        result.append({
            "user_id": u.id, "name": u.name, "track": u.track,
            "team": u.team, "generation": u.generation,
            "missions": mission_statuses, "missed_count": missed_count,
        })

    return result


@router.get("/warnings")
def get_warnings(db: Session = Depends(get_db), admin: User = Depends(require_admin)):
    """2회 이상 미제출 사용자 경고 목록 (N+1 최적화)"""
    now = utcnow()
    users = db.query(User).filter(User.role.in_(["baby_lion", "tester"]), User.approved == True).all()

    if not users:
        return []

    # 마감된 미션을 트랙별로 한 번에 조회
    expired_missions = db.query(Mission).filter(Mission.end_date < now).all()
    expired_by_track = {}
    for m in expired_missions:
        expired_by_track.setdefault(m.track, []).append(m)

    # 모든 관련 제출을 한 번에 조회
    user_ids = [u.id for u in users]
    mission_ids = [m.id for m in expired_missions]
    if not mission_ids:
        return []

    submitted = db.query(Submission.user_id, Submission.mission_id).filter(
        Submission.user_id.in_(user_ids),
        Submission.mission_id.in_(mission_ids),
        Submission.status != "error",
    ).distinct().all()
    submitted_set = set((s.user_id, s.mission_id) for s in submitted)

    warnings = []
    for u in users:
        missions = expired_by_track.get(u.track, [])
        missed = [m.number for m in missions if (u.id, m.id) not in submitted_set]
        if len(missed) >= 2:
            warnings.append({
                "user_id": u.id, "name": u.name, "email": u.email,
                "track": u.track, "team": u.team,
                "missed_missions": missed, "missed_count": len(missed),
            })

    return sorted(warnings, key=lambda w: -w["missed_count"])
