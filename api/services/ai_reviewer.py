"""AI 기반 과제 자동 검사 서비스 — 오케스트레이션"""
import json
import traceback

from openai import OpenAI
from sqlalchemy.orm import Session

from config import OPENAI_API_KEY, AI_MODEL, AI_MAX_TOKENS, AI_TEMPERATURE
from database import SessionLocal
from models import Submission, Mission, Review, User
from services.authorship_verifier import verify_figma_authorship, verify_github_authorship
from services.prompts import SYSTEM_PROMPT, TRACK_PROMPTS, RESPONSE_FORMAT, build_mission_context
from services.submission_context import build_submission_context, encode_screenshot


def validate_review_output(result: dict, checklist_count: int) -> dict:
    """AI 출력의 일관성을 검증하고 필요 시 보정"""
    original_score = min(100, max(0, int(result.get("score", 0))))
    score = original_score
    checklist_results = result.get("checklist_results", [])

    if not checklist_results:
        return {"score": score, "flags": [], "needs_manual": score >= 90}

    passed_count = sum(1 for cr in checklist_results if cr.get("passed"))
    total_items = len(checklist_results)
    pass_rate = passed_count / total_items if total_items > 0 else 0

    flags = []

    # 점수와 체크리스트 통과율 불일치 탐지
    if score >= 80 and pass_rate < 0.4:
        flags.append(f"점수({score})가 체크리스트 통과율({pass_rate:.0%})에 비해 과도하게 높음")
        score = int(pass_rate * 80)
    elif score <= 40 and pass_rate > 0.7:
        flags.append(f"점수({score})가 체크리스트 통과율({pass_rate:.0%})에 비해 과도하게 낮음")
        score = int(pass_rate * 85)

    # 만점 의심 — 원본 AI 점수 기준으로 판단
    if original_score == 100 and total_items >= 4 and pass_rate == 1.0:
        flags.append("만점 제출물 - 운영진 확인 필요")

    # 체크리스트 항목 수 불일치
    if checklist_count > 0 and abs(total_items - checklist_count) > 1:
        flags.append(f"체크리스트 항목 수 불일치 (기대: {checklist_count}, 실제: {total_items})")

    needs_manual = bool(flags) or score == 100

    return {"score": score, "flags": flags, "needs_manual": needs_manual}


def run_ai_review(submission_id: int):
    """백그라운드에서 AI 리뷰를 실행"""
    db: Session = SessionLocal()
    try:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            return

        mission = db.query(Mission).filter(Mission.id == submission.mission_id).first()
        if not mission:
            return

        existing = db.query(Review).filter(Review.submission_id == submission_id).first()
        if existing:
            return

        if not OPENAI_API_KEY:
            review = Review(
                submission_id=submission_id,
                ai_score=None,
                ai_summary="AI API 키가 설정되지 않아 자동 검사를 건너뛰었습니다. 운영진이 직접 평가합니다.",
                ai_feedback=None,
            )
            db.add(review)
            submission.status = "pending"
            db.commit()
            return

        # 제출자 정보 조회 — 작성자 검증 + AI 컨텍스트 주입에 사용
        user = db.query(User).filter(User.id == submission.user_id).first()
        user_name = user.name if user else ""

        # 프롬프트 조립 — 제출자 이름을 컨텍스트에 주입해 체크리스트 평가에 활용
        track_guide = TRACK_PROMPTS.get(mission.track, "")
        mission_context = build_mission_context(mission)
        submission_context, fetch_status = build_submission_context(submission, mission, user_name=user_name)

        # GitHub 제출인데 코드를 못 가져왔으면 AI 호출 없이 에러 처리
        needs_github = mission.submission_type in ("github", "mixed") and submission.github_url
        if needs_github and not fetch_status["github_ok"]:
            review = Review(
                submission_id=submission_id,
                ai_score=None,
                ai_summary="GitHub 레포지토리 정보를 가져올 수 없어 검사를 진행하지 못했습니다. "
                           "레포지토리가 Public인지 확인 후 다시 제출해주세요. "
                           "이 제출은 횟수에 포함되지 않습니다.",
                ai_feedback=None,
            )
            db.add(review)
            submission.status = "error"
            db.commit()
            print(f"[AI Review] Submission #{submission_id}: GitHub fetch 실패 → error 처리")
            return

        # Figma 제출인데 API로 가져오지 못한 경우
        # - submission_type="figma": 하드 에러 (Figma가 제출물의 전부)
        # - submission_type="mixed": 경고만 (GitHub/스크린샷으로 보완 평가 가능)
        needs_figma_strict = mission.submission_type == "figma" and submission.figma_url
        if needs_figma_strict and not fetch_status["figma_ok"]:
            review = Review(
                submission_id=submission_id,
                ai_score=None,
                ai_summary="Figma 파일 정보를 가져올 수 없어 검사를 진행하지 못했습니다. "
                           "Figma 파일의 공유 설정을 '링크가 있는 모든 사람 - 볼 수 있음'으로 "
                           "변경한 후 다시 제출해주세요. 이 제출은 횟수에 포함되지 않습니다.",
                ai_feedback=None,
            )
            db.add(review)
            submission.status = "error"
            db.commit()
            print(f"[AI Review] Submission #{submission_id}: Figma fetch 실패 → error 처리")
            return

        # 작성자 검증 — 본인 작업물인지 Figma 파일명/GitHub README에 학생 이름 포함 여부 확인.
        # admin/tester는 우회. fetch 실패한 채널은 위에서 이미 처리됐으므로 여기선 fetch 성공한
        # 채널만 검증 가능. 실패 시 status="error" + attempt 미차감.
        if user and user.role not in ("admin", "tester"):
            auth_msg = None
            # Figma 파일명 검증 — figma URL이 있고 fetch 성공한 경우만
            if submission.figma_url and fetch_status.get("figma_ok"):
                ok, msg = verify_figma_authorship(
                    fetch_status.get("figma_file_name", ""), user.name
                )
                if not ok:
                    auth_msg = msg
            # GitHub README 검증 — github URL이 있고 fetch 성공한 경우만 (Figma가 통과했어도 둘 다 검사)
            if not auth_msg and submission.github_url and fetch_status.get("github_ok"):
                ok, msg = verify_github_authorship(
                    fetch_status.get("github_readme", ""), user.name
                )
                if not ok:
                    auth_msg = msg
            if auth_msg:
                review = Review(
                    submission_id=submission_id,
                    ai_score=None,
                    ai_summary=auth_msg,
                    ai_feedback=None,
                )
                db.add(review)
                submission.status = "error"
                db.commit()
                print(f"[AI Review] Submission #{submission_id}: 작성자 검증 실패 → error 처리 (user={user.name})")
                return

        user_prompt = f"{mission_context}\n\n{submission_context}\n\n{RESPONSE_FORMAT}"
        system_content = SYSTEM_PROMPT + "\n\n" + track_guide

        # 메시지 조립 (스크린샷 + Figma 썸네일 → Vision 멀티모달)
        user_content_parts = [{"type": "text", "text": user_prompt}]
        # 학생이 업로드한 스크린샷
        for path in [submission.screenshot_path, submission.screenshot_path2, submission.screenshot_path3]:
            screenshot_data = encode_screenshot(path)
            if screenshot_data:
                user_content_parts.append(screenshot_data)
        # Figma API에서 가져온 프레임 썸네일
        for figma_image in fetch_status.get("figma_images", []):
            user_content_parts.append(figma_image)

        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content_parts},
        ]

        # OpenAI API 호출
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=messages,
            temperature=AI_TEMPERATURE,
            max_tokens=AI_MAX_TOKENS,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(content)

        # 출력 검증
        checklist_count = len(mission.checklist) if mission.checklist else 0
        validation = validate_review_output(result, checklist_count)
        score = validation["score"]

        # 리뷰 요약 조립
        summary = result.get("summary", "")
        tips = result.get("improvement_tips", [])
        if tips:
            summary += "\n\n💡 개선 팁:\n" + "\n".join(f"• {t}" for t in tips)

        if validation["flags"]:
            summary += "\n\n⚠️ 자동 검증 알림:\n" + "\n".join(f"• {f}" for f in validation["flags"])

        review = Review(
            submission_id=submission_id,
            ai_score=score,
            ai_summary=summary,
            ai_feedback=result.get("checklist_results", []),
        )
        db.add(review)

        # 자동합격: 80점 이상 + 체크리스트 60% 이상 통과 + 검증 플래그 없음
        checklist_results = result.get("checklist_results", [])
        passed_count = sum(1 for cr in checklist_results if cr.get("passed"))
        total_items = len(checklist_results)
        pass_rate = passed_count / total_items if total_items > 0 else 0

        if 80 <= score < 100 and pass_rate >= 0.6 and not validation["needs_manual"]:
            submission.status = "passed"
        else:
            submission.status = "pending"

        db.commit()
        print(f"[AI Review] Submission #{submission_id}: {score}점 → {submission.status}"
              + (f" (flags: {validation['flags']})" if validation["flags"] else ""))

    except Exception:
        traceback.print_exc()
        try:
            db.rollback()
            submission = db.query(Submission).filter(Submission.id == submission_id).first()
            if submission:
                existing = db.query(Review).filter(Review.submission_id == submission_id).first()
                if not existing:
                    review = Review(
                        submission_id=submission_id,
                        ai_summary="AI 검사 중 오류가 발생했습니다. "
                                   "다시 제출해주세요. 이 제출은 횟수에 포함되지 않습니다.",
                    )
                    db.add(review)
                submission.status = "error"
                db.commit()
        except Exception:
            traceback.print_exc()
    finally:
        db.close()
