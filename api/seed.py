"""미션 초기 데이터를 DB에 시드하는 스크립트"""
import json
import os

from database import engine, SessionLocal, Base
from models import Mission, User
from auth import hash_password


def seed_missions(db):
    if db.query(Mission).count() > 0:
        print("미션 데이터가 이미 존재합니다. 건너뜁니다.")
        return

    data_path = os.path.join(os.path.dirname(__file__), "missions.json")
    if not os.path.exists(data_path):
        print("missions.json 파일이 없습니다.")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        missions = json.load(f)

    for m in missions:
        mission = Mission(
            track=m["track"],
            number=m["number"],
            title=m["title"],
            description=m.get("description", ""),
            checklist=m.get("checklist", []),
            submission_type=m.get("submission_type", "github"),
            estimated_hours=m.get("estimated_hours", 20),
        )
        db.add(mission)

    db.commit()
    print(f"{len(missions)}개 미션이 시드되었습니다.")


def seed_admin(db):
    if db.query(User).filter(User.role == "admin").count() > 0:
        print("관리자 계정이 이미 존재합니다. 건너뜁니다.")
        return

    import os
    admin_pw = os.getenv("ADMIN_PASSWORD", "")
    if not admin_pw:
        import secrets
        admin_pw = secrets.token_urlsafe(12)
        print(f"[!] ADMIN_PASSWORD 미설정. 임시 비밀번호: {admin_pw}")
        print("[!] .env에 ADMIN_PASSWORD를 설정하세요.")

    admin = User(
        name="운영진",
        email="admin@likelion.org",
        password_hash=hash_password(admin_pw),
        track="backend",
        role="admin",
    )
    db.add(admin)
    db.commit()
    print("관리자 계정이 생성되었습니다. (admin@likelion.org)")


def run_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_missions(db)
        seed_admin(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
