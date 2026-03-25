import json
import traceback

from openai import OpenAI
from sqlalchemy.orm import Session

from config import OPENAI_API_KEY, DATABASE_URL
from database import SessionLocal
from models import Submission, Mission, Review


def get_review_prompt(mission: Mission, submission: Submission) -> str:
    checklist_text = "\n".join(f"- {item}" for item in (mission.checklist or []))

    urls = []
    if submission.github_url:
        urls.append(f"GitHub: {submission.github_url}")
    if submission.deploy_url:
        urls.append(f"배포 URL: {submission.deploy_url}")
    if submission.figma_url:
        urls.append(f"Figma: {submission.figma_url}")

    return f"""당신은 멋쟁이사자처럼 대학 동아리의 PBL 과제 리뷰어입니다.
아기사자(초보 개발자)가 제출한 과제를 검사합니다.

## 검사 기준
- 너무 깐깐하게 평가하지 마세요. 학습 목적의 과제이므로 격려와 피드백 위주로 평가합니다.
- 핵심 요구사항을 충족했는지 중심으로 평가하세요.
- 사소한 스타일 차이나 개인 취향은 감점하지 마세요.

## 미션 정보
- 트랙: {mission.track}
- 미션 {mission.number}: {mission.title}
- 설명: {mission.description}

## 체크리스트
{checklist_text}

## 제출물
{chr(10).join(urls)}
{f"설명: {submission.description}" if submission.description else ""}
{f"스크린샷 첨부됨" if submission.screenshot_path else ""}

## 응답 형식 (JSON)
{{
  "score": 0~100 점수,
  "summary": "전체 평가 요약 (2~3문장, 한국어)",
  "checklist_results": [
    {{
      "item": "체크리스트 항목",
      "passed": true/false,
      "comment": "코멘트 (한국어)"
    }}
  ]
}}

JSON만 응답하세요."""


def run_ai_review(submission_id: int):
    db: Session = SessionLocal()
    try:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            return

        mission = db.query(Mission).filter(Mission.id == submission.mission_id).first()
        if not mission:
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

        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = get_review_prompt(mission, submission)

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=2000,
        )

        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[1].rsplit("```", 1)[0].strip()

        result = json.loads(content)

        review = Review(
            submission_id=submission_id,
            ai_score=result.get("score", 0),
            ai_summary=result.get("summary", ""),
            ai_feedback=result.get("checklist_results", []),
        )
        db.add(review)

        if result.get("score", 0) >= 60:
            submission.status = "passed"
        else:
            submission.status = "pending"  # 운영진 확인 필요

        db.commit()

    except Exception:
        traceback.print_exc()
        try:
            submission = db.query(Submission).filter(Submission.id == submission_id).first()
            if submission:
                review = Review(
                    submission_id=submission_id,
                    ai_summary="AI 검사 중 오류가 발생했습니다. 운영진이 직접 평가합니다.",
                )
                db.add(review)
                submission.status = "pending"
                db.commit()
        except Exception:
            pass
    finally:
        db.close()
