import os
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, UploadFile, File, Form
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from auth import get_current_user
from config import MAX_SUBMISSIONS_PER_MISSION, MAX_UPLOAD_SIZE, UPLOAD_DIR
from utils import utcnow
from database import get_db
from models import User, Mission, Submission, Review, MissionDeadlineExtension
from services.ai_reviewer import run_ai_review

router = APIRouter(prefix="/api/submissions", tags=["submissions"])


def _save_screenshot(file: UploadFile) -> str | None:
    """스크린샷 파일을 검증하고 저장한 뒤 경로를 반환한다."""
    if not file or not file.filename:
        return None

    ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".gif", ".webp"}
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"허용된 이미지 형식: {', '.join(ALLOWED_EXTENSIONS)}")

    # 크기 제한: 청크 단위로 읽어 메모리 폭주 방지
    max_size = MAX_UPLOAD_SIZE
    chunks = []
    total = 0
    while True:
        chunk = file.file.read(64 * 1024)  # 64KB씩
        if not chunk:
            break
        total += len(chunk)
        if total > max_size:
            raise HTTPException(400, "스크린샷 파일은 5MB 이하여야 합니다")
        chunks.append(chunk)
    contents = b"".join(chunks)

    # Magic bytes로 실제 파일 타입 검증 (확장자 위조 방지)
    MAGIC_BYTES = {
        b"\x89PNG": ".png",
        b"\xff\xd8\xff": ".jpg",
        b"GIF87a": ".gif",
        b"GIF89a": ".gif",
        b"RIFF": ".webp",  # WebP: RIFF....WEBP (추가 검증 아래)
    }
    detected = False
    for magic, _ in MAGIC_BYTES.items():
        if contents[:len(magic)] == magic:
            # WebP: RIFF 컨테이너 중 WEBP인지 추가 확인
            if magic == b"RIFF" and contents[8:12] != b"WEBP":
                continue
            detected = True
            break
    if not detected:
        raise HTTPException(400, "파일 내용이 허용된 이미지 형식과 일치하지 않습니다")

    filename = f"{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(UPLOAD_DIR, filename)
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    with open(filepath, "wb") as f:
        f.write(contents)
    return f"/uploads/{filename}"


@router.post("", status_code=201)
def create_submission(
    background_tasks: BackgroundTasks,
    mission_id: int = Form(...),
    github_url: str = Form(None),
    deploy_url: str = Form(None),
    figma_url: str = Form(None),
    description: str = Form(None),
    screenshot: UploadFile = File(None),
    screenshot2: UploadFile = File(None),
    screenshot3: UploadFile = File(None),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # URL 형식 검증 (입력 경계에서 차단)
    for url_val, url_name in [(deploy_url, "배포"), (figma_url, "Figma"), (github_url, "GitHub")]:
        if url_val:
            parsed = urlparse(url_val)
            if parsed.scheme not in ("http", "https") or not parsed.hostname:
                raise HTTPException(400, f"유효한 {url_name} URL을 입력하세요 (http/https)")

    mission = db.query(Mission).filter(Mission.id == mission_id).first()
    if not mission:
        raise HTTPException(404, "미션을 찾을 수 없습니다")

    if mission.track != user.track and user.role not in ("admin", "tester"):
        raise HTTPException(400, "본인 트랙의 미션만 제출할 수 있습니다")

    if user.role not in ("admin", "tester"):
        now = utcnow()
        if mission.start_date and now < mission.start_date:
            start_str = mission.start_date.strftime("%m/%d")
            raise HTTPException(400, f"아직 제출 기간이 아닙니다. {start_str}부터 제출 가능합니다.")
        if mission.end_date and now > mission.end_date:
            # 운영진이 부여한 개별 마감 연장이 있고 그 기한 내라면 통과시킨다.
            ext = (
                db.query(MissionDeadlineExtension)
                .filter(
                    MissionDeadlineExtension.user_id == user.id,
                    MissionDeadlineExtension.mission_id == mission_id,
                )
                .first()
            )
            if not (ext and now <= ext.extended_until):
                end_str = mission.end_date.strftime("%m/%d")
                raise HTTPException(400, f"제출 기한이 마감되었습니다. (마감: {end_str})")

    existing = (
        db.query(Submission)
        .filter(
            Submission.user_id == user.id,
            Submission.mission_id == mission_id,
            Submission.status != "error",
        )
        .count()
    )
    if existing >= MAX_SUBMISSIONS_PER_MISSION and user.role not in ("admin", "tester"):
        raise HTTPException(400, f"미션당 최대 {MAX_SUBMISSIONS_PER_MISSION}번까지 제출할 수 있습니다")

    # 디자인/기획 미션은 스크린샷 최소 1장 필수 (admin/tester 제외)
    needs_screenshot = mission.submission_type in ("figma", "mixed")
    if needs_screenshot and user.role not in ("admin", "tester") and not any([screenshot, screenshot2, screenshot3]):
        raise HTTPException(400, "디자인/기획 미션은 스크린샷을 최소 1장 이상 첨부해야 합니다")

    screenshot_path = _save_screenshot(screenshot)
    screenshot_path2 = _save_screenshot(screenshot2)
    screenshot_path3 = _save_screenshot(screenshot3)

    max_attempt = (
        db.query(func.max(Submission.attempt))
        .filter(
            Submission.user_id == user.id,
            Submission.mission_id == mission_id,
            Submission.status != "error",
        )
        .scalar()
    ) or 0

    submission = Submission(
        user_id=user.id,
        mission_id=mission_id,
        attempt=max_attempt + 1,
        github_url=github_url,
        deploy_url=deploy_url,
        figma_url=figma_url,
        screenshot_path=screenshot_path,
        screenshot_path2=screenshot_path2,
        screenshot_path3=screenshot_path3,
        description=description,
        status="reviewing",
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    background_tasks.add_task(run_ai_review, submission.id)

    remaining = MAX_SUBMISSIONS_PER_MISSION - (existing + 1)
    result = {"id": submission.id, "status": submission.status, "attempt": submission.attempt, "remaining": remaining}
    if remaining <= 2:
        result["warning"] = f"⚠️ 남은 제출 기회가 {remaining}번입니다. 신중하게 제출하세요!"
    return result


@router.get("/my")
def my_submissions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    subs = (
        db.query(Submission)
        .options(joinedload(Submission.mission), joinedload(Submission.review))
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
