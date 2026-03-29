"""공유 유틸리티 함수"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """naive UTC datetime 반환 (DB DateTime 컬럼과 비교 호환용)

    DB 컬럼이 DateTime(timezone=False)이므로, aware datetime과 비교 시
    TypeError가 발생합니다. 이 함수는 timezone 정보를 제거한 naive UTC를 반환합니다.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
