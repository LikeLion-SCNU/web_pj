import hmac
import httpx
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import hash_password, verify_password, create_access_token, get_current_user
from config import CURRENT_GENERATION, TURNSTILE_SECRET_KEY
from database import get_db
from models import User
from schemas import UserRegister, UserLogin, UserResponse, Token, EmailVerify
from services.email_service import generate_verification_code, send_verification_email

router = APIRouter(prefix="/api/auth", tags=["auth"])

VERIFY_CODE_EXPIRE_MINUTES = 15
MAX_VERIFY_ATTEMPTS = 5
MAX_TOTAL_VERIFY_ATTEMPTS = 15  # 재전송 포함 누적 최대 시도


def verify_turnstile(token: str) -> bool:
    """Cloudflare Turnstile 토큰 검증"""
    if not TURNSTILE_SECRET_KEY:
        return True  # 키 미설정 시 검증 건너뜀
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
    if TURNSTILE_SECRET_KEY and not verify_turnstile(data.turnstile_token or ""):
        raise HTTPException(400, "봇 검증에 실패했습니다. 다시 시도해주세요.")

    if data.track not in ("planning", "design", "frontend", "backend"):
        raise HTTPException(400, "트랙은 planning, design, frontend, backend 중 하나여야 합니다")

    if db.query(User).filter(User.email == data.email).first():
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
        verification_expires_at=datetime.now(timezone.utc) + timedelta(minutes=VERIFY_CODE_EXPIRE_MINUTES),
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

    if user.verification_attempts >= MAX_TOTAL_VERIFY_ATTEMPTS:
        raise HTTPException(429, "인증 시도 횟수를 초과했습니다. 운영진에게 문의해주세요.")

    if user.verification_expires_at and datetime.now(timezone.utc) > user.verification_expires_at:
        raise HTTPException(400, "인증 코드가 만료되었습니다. 인증 코드를 재전송해주세요.")

    if not hmac.compare_digest(user.verification_code or "", data.code):
        user.verification_attempts += 1
        db.commit()
        remaining = MAX_TOTAL_VERIFY_ATTEMPTS - user.verification_attempts
        if remaining <= 0:
            raise HTTPException(429, "인증 시도 횟수를 초과했습니다. 운영진에게 문의해주세요.")
        raise HTTPException(400, f"인증 코드가 올바르지 않습니다. (남은 시도: {remaining}회)")

    user.email_verified = True
    user.verification_code = None
    user.verification_attempts = 0
    user.verification_expires_at = None
    db.commit()

    return {"message": "이메일 인증이 완료되었습니다. 운영진의 승인을 기다려주세요."}


@router.post("/resend-code")
def resend_code(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다")

    if user.email_verified:
        return {"message": "이미 이메일 인증이 완료되었습니다."}

    if user.verification_attempts >= MAX_TOTAL_VERIFY_ATTEMPTS:
        raise HTTPException(429, "인증 시도 횟수를 초과했습니다. 운영진에게 문의해주세요.")

    # 재전송 쿨다운: 마지막 코드 발급 후 60초 이내 재전송 방지
    if user.verification_expires_at:
        code_issued_at = user.verification_expires_at - timedelta(minutes=VERIFY_CODE_EXPIRE_MINUTES)
        if datetime.now(timezone.utc) < code_issued_at + timedelta(seconds=60):
            raise HTTPException(429, "인증 코드 재전송은 60초 후에 가능합니다.")

    code = generate_verification_code()
    user.verification_code = code
    # 시도 횟수는 유지 (누적 추적), 새 코드로만 리프레시
    user.verification_expires_at = datetime.now(timezone.utc) + timedelta(minutes=VERIFY_CODE_EXPIRE_MINUTES)
    db.commit()

    send_verification_email(user.email, user.name, code)
    return {"message": "인증 코드가 재전송되었습니다."}


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    if TURNSTILE_SECRET_KEY and not verify_turnstile(data.turnstile_token or ""):
        raise HTTPException(400, "봇 검증에 실패했습니다. 다시 시도해주세요.")

    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
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
