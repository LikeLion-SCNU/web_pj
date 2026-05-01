"""제출물 작성자 검증 — 다른 사람의 작업물 제출(부정행위) 방지.

검증 규칙:
- Figma 미션: figma_data['file_name']에 학생 본인 이름이 포함되어야 함.
  예) "LIKELION PBL - [홍길동]" / "Mission2_홍길동" 등 어떤 형태든 substring 포함.
- GitHub 미션: README 본문에 학생 본인 이름이 포함되어야 함.

매칭은 결정적(substring) — 공백 제거 + (영문) 대소문자 무시.
admin/tester 역할은 호출 측에서 우회한다.
"""
import re


def _normalize(s: str) -> str:
    """검증용 정규화: 모든 공백 제거 + 소문자.

    한글은 대소문자 개념이 없어 영향이 없고, 영문 이름은 대소문자 무시 매칭이 된다.
    """
    if not s:
        return ""
    return re.sub(r"\s+", "", s).lower()


def contains_name(haystack: str, name: str) -> bool:
    """haystack 안에 name이 포함되는지 (정규화 후 substring) 검사."""
    if not haystack or not name:
        return False
    return _normalize(name) in _normalize(haystack)


def verify_figma_authorship(file_name: str, user_name: str) -> tuple[bool, str | None]:
    """Figma 파일명에 학생 본인 이름이 포함되는지 검사.

    Returns:
        (통과 여부, 실패 시 학생에게 노출될 안내 메시지)
    """
    if contains_name(file_name, user_name):
        return True, None
    current = file_name or "(파일명 없음)"
    msg = (
        f"본인 확인 실패 — Figma 파일명에 본인 이름 '{user_name}'이 포함되어야 합니다. "
        f"Figma 좌측 상단의 파일명을 'LIKELION PBL - [홍길동]' 같은 형태로 변경한 후 다시 제출해주세요. "
        f"(현재 파일명: '{current}') "
        f"이 제출은 횟수에 포함되지 않습니다."
    )
    return False, msg


def verify_github_authorship(readme_content: str, user_name: str) -> tuple[bool, str | None]:
    """GitHub README에 학생 본인 이름이 포함되는지 검사.

    Returns:
        (통과 여부, 실패 시 학생에게 노출될 안내 메시지)
    """
    if contains_name(readme_content, user_name):
        return True, None
    if not readme_content:
        msg = (
            f"본인 확인 실패 — README.md 파일이 레포지토리에 없거나 비어있습니다. "
            f"README.md를 만들고 본인 이름 '{user_name}'을 포함시킨 후 다시 제출해주세요. "
            f"(예: '작성자: 홍길동') 이 제출은 횟수에 포함되지 않습니다."
        )
    else:
        msg = (
            f"본인 확인 실패 — GitHub README.md에 본인 이름 '{user_name}'이 포함되어야 합니다. "
            f"README 상단에 작성자 이름(예: '작성자: 홍길동')을 명시한 후 다시 제출해주세요. "
            f"이 제출은 횟수에 포함되지 않습니다."
        )
    return False, msg
