"""AI 기반 과제 자동 검사 서비스 — 오케스트레이션"""
import json
import traceback

from openai import OpenAI
from sqlalchemy.orm import Session

from config import OPENAI_API_KEY, AI_MODEL, AI_MAX_TOKENS, AI_TEMPERATURE
from database import SessionLocal
from models import Submission, Mission, Review
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

        # 프롬프트 조립
        track_guide = TRACK_PROMPTS.get(mission.track, "")
        mission_context = build_mission_context(mission)
        submission_context = build_submission_context(submission, mission)

        user_prompt = f"{mission_context}\n\n{submission_context}\n\n{RESPONSE_FORMAT}"
        system_content = SYSTEM_PROMPT + "\n\n" + track_guide

        # 메시지 조립 (스크린샷이 있으면 Vision 멀티모달)
        user_content_parts = [{"type": "text", "text": user_prompt}]
        screenshot_data = encode_screenshot(submission.screenshot_path)
        if screenshot_data:
            user_content_parts.append(screenshot_data)

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

        if 80 <= score < 100 and not validation["needs_manual"]:
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
                        ai_summary="AI 검사 중 오류가 발생했습니다. 운영진이 직접 평가합니다.",
                    )
                    db.add(review)
                submission.status = "pending"
                db.commit()
        except Exception:
            traceback.print_exc()
    finally:
        db.close()
