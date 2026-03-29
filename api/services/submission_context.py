"""제출물 컨텍스트 조립 + 스크린샷 인코딩"""
import base64
import os
import re
from pathlib import Path

from config import UPLOAD_DIR, MAX_SCREENSHOT_SIZE
from models import Submission, Mission
from services.github_fetcher import fetch_repo_code
from services.deploy_analyzer import fetch_deploy_preview


def encode_screenshot(screenshot_path: str) -> dict | None:
    """업로드된 스크린샷을 base64로 인코딩하여 Vision API용 포맷 반환"""
    if not screenshot_path:
        return None

    full_path = Path(UPLOAD_DIR) / os.path.basename(screenshot_path)
    full_path = full_path.resolve()
    if not str(full_path).startswith(str(Path(UPLOAD_DIR).resolve())):
        return None
    if not full_path.exists():
        return None

    try:
        if full_path.stat().st_size > MAX_SCREENSHOT_SIZE:
            return None

        with open(full_path, "rb") as f:
            data = f.read()

        ext = screenshot_path.rsplit(".", 1)[-1].lower()
        mime_map = {
            "png": "image/png",
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "gif": "image/gif",
            "webp": "image/webp",
        }
        mime = mime_map.get(ext, "image/png")
        b64 = base64.b64encode(data).decode("utf-8")

        return {
            "type": "image_url",
            "image_url": {
                "url": f"data:{mime};base64,{b64}",
                "detail": "low",
            },
        }
    except Exception:
        return None


def _sanitize_student_input(text: str) -> str:
    """학생 입력에서 XML 태그 탈출 시도를 방지 (대소문자/공백 변형 포함)"""
    if not text:
        return text
    return re.sub(r'</?student_submission\s*>', '[태그 제거됨]', text, flags=re.IGNORECASE)


def build_submission_context(submission: Submission, mission: Mission) -> str:
    """제출물 정보를 AI에게 전달할 컨텍스트로 구성"""
    parts = ["<student_submission>"]

    if submission.github_url:
        parts.append(f"\n### GitHub 레포지토리\nURL: {_sanitize_student_input(submission.github_url)}")
        repo_data = fetch_repo_code(submission.github_url, mission.track)
        if repo_data and "error" not in repo_data:
            parts.append(f"총 파일 수: {repo_data['total_files']}개")
            parts.append(f"\n파일 트리 (상위 {len(repo_data['file_tree'])}개):")
            for f in repo_data["file_tree"]:
                parts.append(f"  {f}")

            if repo_data["code_files"]:
                parts.append("\n### 핵심 코드 파일")
                for path, content in repo_data["code_files"].items():
                    parts.append(f"\n--- {path} ---")
                    parts.append(content)
        elif repo_data and "error" in repo_data:
            parts.append(f"⚠️ {repo_data['error']}")
            parts.append("GitHub 코드를 가져올 수 없어 URL과 설명만으로 평가합니다.")

    if submission.deploy_url:
        parts.append(f"\n### 배포 URL\n{_sanitize_student_input(submission.deploy_url)}")
        deploy_info = fetch_deploy_preview(submission.deploy_url)
        if deploy_info:
            parts.append("\n### 배포 사이트 분석 결과")
            parts.append(deploy_info)
        else:
            parts.append("(배포 URL에 접근할 수 없거나 분석에 실패했습니다)")

    if submission.figma_url:
        parts.append(f"\n### Figma URL\n{_sanitize_student_input(submission.figma_url)}")
        parts.append("(Figma 내용은 직접 확인할 수 없으므로 URL 존재 여부와 설명을 참고)")

    if submission.screenshot_path:
        parts.append("\n### 스크린샷\n첨부된 스크린샷 이미지를 시각적으로 분석하세요. "
                     "디자인/기획 트랙의 경우 스크린샷이 핵심 평가 자료입니다.")

    if submission.description:
        parts.append(f"\n### 학생 설명\n{_sanitize_student_input(submission.description)}")

    parts.append("\n</student_submission>")
    return "\n".join(parts)
