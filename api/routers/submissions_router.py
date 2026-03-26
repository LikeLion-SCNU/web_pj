import os
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy.orm import Session

from auth import get_current_user
from config import MAX_SUBMISSIONS_PER_MISSION, UPLOAD_DIR
from database import get_db
from models import User, Mission, Submission, Review
from schemas import SubmissionCreate
from services.ai_reviewer import run_ai_review

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


@router.post("", status_code=201)
def create_submission(
    background_tasks: BackgroundTasks,
    mission_id: int = Form(...),
    github_url: str = Form(None),
    deploy_url: str = Form(None),
    figma_url: str = Form(None),
    description: str = Form(None),
    screenshot: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(404, "미션을 찾을 수 없습니다")

    if mission.track != user.track and user.role not in ("admin", "tester"):
        raise HTTPException(400, "본인 트랙의 미션만 제출할 수 있습니다")

    if user.role not in ("admin", "tester"):
        now = datetime.utcnow()
        if mission.start_date and now < mission.start_date:
            start_str = mission.start_date.strftime("%m/%d")
            raise HTTPException(400, f"아직 제출 기간이 아닙니다. {start_str}부터 제출 가능합니다.")
        if mission.end_date and now > mission.end_date:
            end_str = mission.end_date.strftime("%m/%d")
            raise HTTPException(400, f"제출 기한이 마감되었습니다. (마감: {end_str})")

    existing = (
        db.query(Submission)
        .filter(Submission.user_id == user.id, Submission.mission_id == mission_id)
        .count()
    )
    if existing >= MAX_SUBMISSIONS_PER_MISSION:
        raise HTTPException(400, f"미션당 최대 {MAX_SUBMISSIONS_PER_MISSION}번까지 제출할 수 있습니다")

    screenshot_path = None
    if screenshot:
        ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
        ext = os.path.splitext(screenshot.filename)[1].lower() if screenshot.filename else ""
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(400, f"허용된 이미지 형식: {', '.join(ALLOWED_EXTENSIONS)}")

        contents = screenshot.file.read()
        if len(contents) > 5 * 1024 * 1024:  # 5MB
            raise HTTPException(400, "스크린샷 파일은 5MB 이하여야 합니다")

        filename = f"{uuid.uuid4().hex}{ext}"
        filepath = os.path.join(UPLOAD_DIR, filename)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(contents)
        screenshot_path = f"/uploads/{filename}"

    submission = Submission(
        user_id=user.id,
        mission_id=mission_id,
        attempt=existing + 1,
        github_url=github_url,
        deploy_url=deploy_url,
        figma_url=figma_url,
        screenshot_path=screenshot_path,
        description=description,
        status="reviewing",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    background_tasks.add_task(run_ai_review, submission.id)

    return {"id": submission.id, "status": submission.status, "attempt": submission.attempt}


@router.get("/my")
def my_submissions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subs = (
        db.query(Submission)
        .filter(Submission.user_id == user.id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )
    return [
        {
            "id": s.id,
            "mission_id": s.mission_id,
            "mission_title": s.mission.title if s.mission else None,
            "mission_number": s.mission.number if s.mission else None,
            "attempt": s.attempt,
            "status": s.status,
            "submitted_at": s.submitted_at.isoformat(),
            "review": {
                "ai_score": s.review.ai_score,
                "ai_summary": s.review.ai_summary,
                "admin_approved": s.review.admin_approved,
            } if s.review else None,
        }
        for s in subs
    ]
