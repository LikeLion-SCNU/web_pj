import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from config import SECRET_KEY, ALGORITHM, ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_db
from models import User

# bcrypt rounds를 명시적으로 고정 — 더미 해시와 실제 해시의 비용이 항상 동일하도록 보장
# (rounds 변경 시 이 상수와 _DUMMY_PASSWORD_HASH도 동시에 갱신해야 함)
_BCRYPT_ROUNDS = 12
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=_BCRYPT_ROUNDS)
security = HTTPBearer()

# 미존재 사용자 분기에서도 bcrypt 비용을 동일하게 소모하기 위한 더미 해시
# (사용자 enumeration timing attack 방어)
_DUMMY_PASSWORD_HASH = pwd_context.hash("not_a_real_password_just_for_timing_equalization")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def verify_password_dummy() -> None:
    """사용자가 존재하지 않을 때 호출. 실제 verify와 동일한 시간을 소모해 enumeration 방어."""
    pwd_context.verify("dummy", _DUMMY_PASSWORD_HASH)


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "exp": expire,
        "iat": now,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        sub = payload.get("sub")
        if sub is None:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다")
        user_id = int(sub)
    except (JWTError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="유효하지 않은 토큰입니다")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="사용자를 찾을 수 없습니다")

    if not user.email_verified or (not user.approved and user.role != "admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="계정이 비활성화되었습니다")

    return user


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="운영진 권한이 필요합니다")
    return user
