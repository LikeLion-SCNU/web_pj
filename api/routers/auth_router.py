from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import hash_password, verify_password, create_access_token, get_current_user
from config import CURRENT_GENERATION
from database import get_db
from models import User
from schemas import UserRegister, UserLogin, UserResponse, Token, EmailVerify
from services.email_service import generate_verification_code, send_verification_email

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
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
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    send_verification_email(data.email, data.name, code)

    return {"message": "인증 코드가 이메일로 전송되었습니다. 이메일을 확인해주세요."}


@router.post("/verify-email")
def verify_email(data: EmailVerify, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(404, "사용자를 찾을 수 없습니다")

    if user.email_verified:
        return {"message": "이미 이메일 인증이 완료되었습니다. 운영진 승인을 기다려주세요."}

    if user.verification_code != data.code:
        raise HTTPException(400, "인증 코드가 올바르지 않습니다")

    user.email_verified = True
    user.verification_code = None
    db.commit()

    return {"message": "이메일 인증이 완료되었습니다. 운영진의 승인을 기다려주세요."}


@router.post("/resend-code")
def resend_code(data: UserLogin, db: Session = Depends(get_db)):
    """이메일로 인증 코드 재전송 (비밀번호 확인 후)"""
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다")

    if user.email_verified:
        return {"message": "이미 이메일 인증이 완료되었습니다."}

    code = generate_verification_code()
    user.verification_code = code
    db.commit()

    send_verification_email(user.email, user.name, code)
    return {"message": "인증 코드가 재전송되었습니다."}


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
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
