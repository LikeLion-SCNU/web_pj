"""공유 유틸리티 함수"""
from datetime import datetime, timezone


def utcnow() -> datetime:
    """naive UTC datetime 반환 (DB DateTime 컬럼과 비교 호환용)

    DB 컬럼이 DateTime(timezone=False)이므로, aware datetime과 비교 시
    TypeError가 발생합니다. 이 함수는 timezone 정보를 제거한 naive UTC를 반환합니다.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def iso_utc(dt: datetime | None) -> str | None:
    """UTC naive datetime을 'Z' suffix가 있는 ISO 8601로 반환.

    extended_until, reviewed_at처럼 UTC naive로 저장되는 datetime의 JSON 응답에 사용.
    naive datetime을 isoformat()만 호출하면 timezone marker가 없어 JS의 `new Date()`가
    브라우저 로컬 시각으로 해석 → 9시간 어긋남. 'Z' suffix로 UTC임을 명시해 정확한
    로컬 변환을 보장한다.

    주의: mission.start_date / end_date는 seed.py에서 KST 의미로 naive 저장되므로
    이 함수를 사용하지 말 것 (별도 이슈).
    """
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    return dt.isoformat() + "Z"
