"""제출물 컨텍스트 조립 + 스크린샷 인코딩"""
import base64
import os
import re
from pathlib import Path

from config import UPLOAD_DIR, MAX_SCREENSHOT_SIZE
from models import Submission, Mission
from services.github_fetcher import fetch_repo_code
from services.deploy_analyzer import fetch_deploy_preview
from services.figma_fetcher import fetch_figma_file


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


def _sanitize_figma_text(text: str) -> str:
    """Figma 레이어/컴포넌트 이름의 프롬프트 인젝션 방어.

    학생이 레이어 이름으로 프롬프트 인젝션을 시도할 수 있으므로 강하게 방어:
    - XML/HTML 태그 제거
    - 마크다운 헤더(###) 제거
    - 역할 지시어(system:, assistant: 등) 제거
    - 제어 문자 제거
    - 길이 100자 제한
    """
    if not text:
        return ""
    # 1. student_submission 태그 탈출 방지
    text = re.sub(r'</?student_submission\s*>', '[제거됨]', text, flags=re.IGNORECASE)
    # 2. 다른 구조 태그 중화 (<, > → 전각 문자로 치환)
    text = text.replace('<', '＜').replace('>', '＞')
    # 3. 마크다운 헤더/구분선 중화 (# → 전각)
    text = re.sub(r'(?m)^[#\-=*]{2,}', '', text)
    # 4. 역할 지시어 중화 (대소문자 무관)
    text = re.sub(
        r'(?i)\b(system|assistant|user|instruction)\s*:',
        '[제거됨]:',
        text,
    )
    # 5. 인젝션 패턴 중화
    text = re.sub(
        r'(?i)(ignore\s+(all\s+)?previous|disregard\s+(all\s+)?(previous|instructions)|forget\s+everything)',
        '[제거됨]',
        text,
    )
    # 6. 제어 문자 및 줄바꿈 제거
    text = re.sub(r'[\x00-\x1f\x7f]', ' ', text)
    # 7. 길이 제한
    return text[:100]


def build_submission_context(submission: Submission, mission: Mission, user_name: str = "") -> tuple[str, dict]:
    """제출물 정보를 AI에게 전달할 컨텍스트로 구성.

    Args:
        submission: 제출 레코드
        mission: 미션 레코드
        user_name: 제출자(학생) 이름 — AI가 본인 확인 체크리스트를 평가할 때 사용

    Returns:
        (context_str, fetch_status):
        - context_str: AI에 전달할 텍스트
        - fetch_status: {
            "github_ok": bool,   # GitHub URL 없으면 True
            "figma_ok": bool,    # Figma URL 없으면 True
            "figma_images": list # Vision API에 전달할 Figma 썸네일 이미지
            "figma_file_name": str  # 작성자 검증용 (원본 파일명)
            "github_readme": str    # 작성자 검증용 (README 본문)
          }
    """
    parts = ["<student_submission>"]
    if user_name:
        parts.append(f"\n### 제출자 정보\n제출자 이름: {_sanitize_student_input(user_name)}")
        parts.append(
            "(체크리스트에 '본인 이름 포함' 항목이 있으면, 위 제출자 이름이 "
            "Figma 파일명 또는 README 본문에 실제로 포함되었는지 확인하여 판정)"
        )
    fetch_status = {
        "github_ok": True,
        "figma_ok": True,
        "figma_images": [],
        # 작성자 검증용 surface (authorship_verifier에서 사용)
        "figma_file_name": "",
        "github_readme": "",
    }

    if submission.github_url:
        parts.append(f"\n### GitHub 레포지토리\nURL: {_sanitize_student_input(submission.github_url)}")
        repo_data = fetch_repo_code(submission.github_url, mission.track)
        if repo_data and "error" not in repo_data:
            parts.append(f"총 파일 수: {repo_data['total_files']}개")
            parts.append(f"총 커밋 수: {repo_data.get('total_commits', '?')}개")

            # 브랜치 정보
            branches = repo_data.get("branches", [])
            if branches:
                parts.append(f"브랜치 목록: {', '.join(branches)} ({len(branches)}개)")

            # PR 정보
            prs = repo_data.get("pull_requests", [])
            if prs:
                parts.append(f"\n### Pull Requests ({len(prs)}개)")
                for pr in prs:
                    parts.append(f"- [{pr['state']}] {pr['title']} ({pr['head']} → {pr['base']})")

            # 최근 커밋 메시지
            recent = repo_data.get("recent_commits", [])
            if recent:
                parts.append(f"\n### 최근 커밋 ({len(recent)}개)")
                for c in recent[:5]:
                    parts.append(f"- {c['message']}")

            parts.append(f"\n파일 트리 (상위 {len(repo_data['file_tree'])}개):")
            for f in repo_data["file_tree"]:
                parts.append(f"  {f}")

            if repo_data["code_files"]:
                parts.append("\n### 핵심 코드 파일")
                for path, content in repo_data["code_files"].items():
                    parts.append(f"\n--- {path} ---")
                    parts.append(content)
                # 작성자 검증용 — README 내용을 fetch_status에 노출 (대소문자 변형 키 모두 시도)
                code_files = repo_data["code_files"]
                for k in ("README.md", "readme.md", "Readme.md", "README"):
                    if k in code_files:
                        fetch_status["github_readme"] = code_files[k] or ""
                        break
        else:
            fetch_status["github_ok"] = False
            error_msg = repo_data["error"] if repo_data else "GitHub API 접근 실패"
            parts.append(f"⚠️ {error_msg}")

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
        figma_data = fetch_figma_file(submission.figma_url)
        if figma_data and "error" not in figma_data:
            # 파일명은 _summarize_document에서 이미 200자로 제한됨
            file_name_raw = figma_data.get('file_name', '')
            # 작성자 검증용 — 원본 파일명(sanitize 전)을 fetch_status에 노출
            fetch_status["figma_file_name"] = file_name_raw or ""
            parts.append(f"파일명: {_sanitize_figma_text(file_name_raw)}")
            parts.append(f"최종 수정일: {_sanitize_figma_text(figma_data.get('last_modified', '?'))}")
            # 용어 명확화: Figma의 'Page'(=Canvas)와 학생/체크리스트 용어 '화면(페이지)'(=Frame)가
            # 자주 혼동됨. AI가 page_count(보통 1)만 보고 "10페이지 미만"이라 잘못 판정하는 사례가 있어
            # 라벨을 분리하고 어느 값을 기준으로 평가해야 하는지 명시한다.
            parts.append(f"Figma 캔버스(파일 내 Page/Canvas) 수: {figma_data.get('page_count', 0)}개")
            parts.append(f"화면(스크린/Frame) 수: {figma_data.get('total_frames', 0)}개")
            parts.append(
                "(중요: 체크리스트에서 '화면 수' / '페이지 수' / '스크린 수'를 평가할 때는 위의 "
                "**화면(스크린/Frame) 수**를 기준으로 하세요. Figma의 'Page'(Canvas)는 파일 내부 분할 "
                "단위일 뿐이고, 학생이 만든 개별 화면은 모두 Frame입니다. Canvas 1개 안에 Frame이 14개면 "
                "'화면 수 = 14개'입니다.)"
            )
            parts.append(f"텍스트 레이어: {figma_data.get('text_layers', 0)}개")
            parts.append(f"컴포넌트: {figma_data.get('total_components', 0)}개")
            parts.append(f"컴포넌트 세트(Variants): {figma_data.get('total_component_sets', 0)}개")
            parts.append(f"Auto Layout 사용: {'예' if figma_data.get('has_auto_layout') else '아니오'} ({figma_data.get('auto_layout_count', 0)}개 노드)")

            style_counts = figma_data.get("style_counts", {})
            parts.append(
                f"로컬 스타일 — 색상:{style_counts.get('FILL', 0)}, "
                f"텍스트:{style_counts.get('TEXT', 0)}, "
                f"효과:{style_counts.get('EFFECT', 0)}, "
                f"그리드:{style_counts.get('GRID', 0)}"
            )

            # 페이지 목록
            pages = figma_data.get("pages", [])
            if pages:
                parts.append(f"\n### 페이지 목록 ({len(pages)}개)")
                for p in pages[:15]:
                    page_name = _sanitize_figma_text(p.get("name", ""))
                    parts.append(f"- {page_name} (프레임 {p.get('frame_count', 0)}개)")

            # 샘플 프레임
            sampled = figma_data.get("sampled_frames", [])
            if sampled:
                parts.append(f"\n### 주요 프레임 샘플 (상위 {min(len(sampled), 15)}개)")
                parts.append(
                    "(체크리스트에서 특정 종류의 화면(예: 로그인/회원가입/설정/오류/알림/마이페이지/검색 등) "
                    "포함 여부를 평가할 때는 아래 프레임 이름 목록을 근거로 판단하세요. 이름에 해당 키워드가 "
                    "있으면 포함된 것으로 간주합니다.)"
                )
                for fr in sampled[:15]:
                    fr_name = _sanitize_figma_text(fr.get("name", ""))
                    parts.append(
                        f"- {fr_name} [{fr.get('page', '')}] "
                        f"{fr.get('width', 0)}x{fr.get('height', 0)} "
                        f"자식 {fr.get('children_count', 0)}개"
                    )

            # 썸네일은 별도로 Vision API에 전달
            fetch_status["figma_images"] = figma_data.get("thumbnails_encoded", [])
            if fetch_status["figma_images"]:
                parts.append(f"\n(Figma 주요 화면 {len(fetch_status['figma_images'])}장이 이미지로 첨부되어 시각 분석 가능)")
        else:
            fetch_status["figma_ok"] = False
            error_msg = figma_data["error"] if figma_data else "Figma URL 형식이 올바르지 않거나 파싱에 실패했습니다."
            parts.append(f"⚠️ {error_msg}")

    screenshot_paths = [p for p in [submission.screenshot_path, submission.screenshot_path2, submission.screenshot_path3] if p]
    if screenshot_paths:
        count = len(screenshot_paths)
        parts.append(f"\n### 스크린샷 ({count}장)\n첨부된 스크린샷 {count}장을 시각적으로 분석하세요. "
                     "디자인/기획 트랙의 경우 스크린샷이 핵심 평가 자료입니다.")

    if submission.description:
        parts.append(f"\n### 학생 설명\n{_sanitize_student_input(submission.description)}")

    parts.append("\n</student_submission>")
    return "\n".join(parts), fetch_status
