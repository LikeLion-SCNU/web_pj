import hmac
import httpx
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import hash_password, verify_password, verify_password_dummy, create_access_token, get_current_user
from config import CURRENT_GENERATION, IS_DEV, REGISTRATION_OPEN, TURNSTILE_SECRET_KEY
from utils import utcnow
from database import get_db
from models import User
from schemas import UserRegister, UserLogin, UserResponse, Token, EmailVerify
from services.email_service import generate_verification_code, send_verification_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

VERIFY_CODE_EXPIRE_MINUTES = 15
# 누적 최대 시도 (재전송 + 잘못된 코드 입력 합산). 정상 사용자는 보통 1~3회 내 완료.
MAX_TOTAL_VERIFY_ATTEMPTS = 15


def _increment_verification_attempts(db: Session, user_id: int) -> None:
    """원자적으로 verification_attempts를 1 증가 (race condition 방지).

    ORM의 read-modify-write는 동시 요청 시 increment를 잃을 수 있어
    SQL UPDATE 표현식으로 직접 증가시킨다.
    """
    db.query(User).filter(User.id == user_id).update(
        {"verification_attempts": User.verification_attempts + 1},
        synchronize_session=False,
    )


def verify_turnstile(token: str) -> bool:
    """Cloudflare Turnstile 토큰 검증"""
    if not TURNSTILE_SECRET_KEY:
        if IS_DEV:
            return True  # 개발 환경에서만 검증 건너뜀
        return False  # 프로덕션에서 키 미설정 시 검증 실패
    try:
        resp = httpx.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={"secret": TURNSTILE_SECRET_KEY, "response": token},
            timeout=5,
        )
        return resp.json().get("success", False)
    except Exception:
        return False


@router.post("/register", status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if not REGISTRATION_OPEN:
        raise HTTPException(403, "현재 회원가입이 마감되었습니다. 운영진에게 문의해주세요.")

    if TURNSTILE_SECRET_KEY and not verify_turnstile(data.turnstile_token or ""):
        raise HTTPException(400, "봇 검증에 실패했습니다. 다시 시도해주세요.")

    if data.track not in ("planning", "design", "frontend", "backend"):
        raise HTTPException(400, "트랙은 planning, design, frontend, backend 중 하나여야 합니다")

    if db.query(User).filter(User.email == data.email).first():
        # 중복 이메일 분기에서도 bcrypt 비용 동일 소모 (timing enumeration 부분 완화)
        # 완전 차단은 IP rate limit + 응답 통일이 필요 — 별도 후속 작업
        verify_password_dummy()
        raise HTTPException(409, "이미 사용 중인 이메일입니다")

    code = generate_verification_code()

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        track=data.track,
        team=data.team,
        generation=data.generation or CURRENT_GENERATION,
        email_verified=False,
        approved=False,
        verification_code=code,
        verification_attempts=0,
        verification_expires_at=utcnow() + timedelta(minutes=VERIFY_CODE_EXPIRE_MINUTES),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    success = send_verification_email(data.email, data.name, code)
    if not success:
        return {"message": "계정이 생성되었지만 이메일 발송에 실패했습니다. 인증 코드 재전송을 시도해주세요."}

    return {"message": "인증 코드가 이메일로 전송되었습니다. 이메일을 확인해주세요."}


@router.post("/verify-email")
def verify_email(data: EmailVerify, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다")

    if user.email_verified:
        return {"message": "이미 이메일 인증이 완료되었습니다. 운영진 승인을 기다려주세요."}

    if user.verification_expires_at and utcnow() > user.verification_expires_at:
        raise HTTPException(400, "인증 코드가 만료되었습니다. 인증 코드를 재전송해주세요.")

    # 정확한 코드는 시도 횟수와 무관하게 항상 통과시킨다.
    # (재전송 누적으로 카운터가 한도에 닿아도 발급된 유효 코드는 사용 가능해야 함)
    if hmac.compare_digest(user.verification_code or "", data.code):
        user.email_verified = True
        user.verification_code = None
        user.verification_attempts = 0
        user.verification_expires_at = None
        db.commit()
        return {"message": "이메일 인증이 완료되었습니다. 운영진의 승인을 기다려주세요."}

    # 잘못된 코드 — 시도 한도 검사 후 카운터 증가
    if user.verification_attempts >= MAX_TOTAL_VERIFY_ATTEMPTS:
        raise HTTPException(429, "인증 시도 횟수를 초과했습니다. 운영진에게 문의해주세요.")

    _increment_verification_attempts(db, user.id)
    db.commit()
    db.refresh(user)
    remaining = MAX_TOTAL_VERIFY_ATTEMPTS - user.verification_attempts
    if remaining <= 0:
        raise HTTPException(429, "인증 시도 횟수를 초과했습니다. 운영진에게 문의해주세요.")
    raise HTTPException(400, f"인증 코드가 올바르지 않습니다. (남은 시도: {remaining}회)")


@router.post("/resend-code")
def resend_code(data: UserLogin, db: Session = Depends(get_db)):
    if not REGISTRATION_OPEN:
        raise HTTPException(403, "현재 회원가입이 마감되어 인증 코드 재전송이 불가합니다. 운영진에게 문의해주세요.")

    # NOTE: Turnstile은 이 엔드포인트에 미적용. frontend(login.html handleResendCode)에서
    # 토큰을 보내지 않으며, Turnstile 토큰은 단일 사용이라 가입 시 토큰 재사용 불가.
    # 후속 작업으로 verify-step 페이지에 별도 Turnstile 위젯 추가 후 활성화 예정.
    # 현재 방어: REGISTRATION_OPEN 게이트 + (email, password) 인증 + 60s 쿨다운 + 15회 누적 한도.

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # 미존재 사용자에 대해서도 bcrypt 비용 동일 소모 (timing enumeration 방어)
        verify_password_dummy()
        raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다")

    if user.email_verified:
        return {"message": "이미 이메일 인증이 완료되었습니다."}

    if user.verification_attempts >= MAX_TOTAL_VERIFY_ATTEMPTS:
        raise HTTPException(429, "인증 시도 횟수를 초과했습니다. 운영진에게 문의해주세요.")

    # 재전송 쿨다운: 마지막 코드 발급 후 60초 이내 재전송 방지
    if user.verification_expires_at:
        code_issued_at = user.verification_expires_at - timedelta(minutes=VERIFY_CODE_EXPIRE_MINUTES)
        if utcnow() < code_issued_at + timedelta(seconds=60):
            raise HTTPException(429, "인증 코드 재전송은 60초 후에 가능합니다.")

    code = generate_verification_code()
    # 재전송도 시도 횟수에 포함하여 SMTP 무한 발송 방지.
    # 재전송 후 카운터가 한도에 도달해도 /verify-email은 정확한 코드는 통과시키므로
    # 정상 사용자는 이메일 받은 코드로 정상 인증 가능.
    _increment_verification_attempts(db, user.id)
    user.verification_code = code
    user.verification_expires_at = utcnow() + timedelta(minutes=VERIFY_CODE_EXPIRE_MINUTES)
    db.commit()

    success = send_verification_email(user.email, user.name, code)
    if not success:
        raise HTTPException(500, "이메일 발송에 실패했습니다. 운영진에게 문의해주세요.")
    return {"message": "인증 코드가 재전송되었습니다."}


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    if TURNSTILE_SECRET_KEY and not verify_turnstile(data.turnstile_token or ""):
        raise HTTPException(400, "봇 검증에 실패했습니다. 다시 시도해주세요.")

    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        # 미존재 사용자에 대해서도 bcrypt 비용 동일 소모 (timing enumeration 방어)
        verify_password_dummy()
        raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다")
    if not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다")

    if not user.email_verified:
        raise HTTPException(403, "이메일 인증이 필요합니다. 이메일을 확인해주세요.")

    if not user.approved and user.role != "admin":
        raise HTTPException(403, "운영진의 승인을 기다리고 있습니다. 승인 후 로그인할 수 있습니다.")

    token = create_access_token(user.id)
    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
