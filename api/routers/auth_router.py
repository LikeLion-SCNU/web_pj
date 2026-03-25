from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from auth import hash_password, verify_password, create_access_token, get_current_user
from database import get_db
from models import User
from schemas import UserRegister, UserLogin, UserResponse, Token

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if data.track not in ("planning", "design", "frontend", "backend"):
        raise HTTPException(400, "트랙은 planning, design, frontend, backend 중 하나여야 합니다")

    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(409, "이미 사용 중인 이메일입니다")

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        track=data.track,
        team=data.team,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(401, "이메일 또는 비밀번호가 올바르지 않습니다")

    token = create_access_token(user.id)
    return Token(access_token=token)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)):
    return user
