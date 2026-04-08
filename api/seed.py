"""미션 초기 데이터를 DB에 시드하는 스크립트"""
import json
import os
from datetime import datetime

from config import IS_DEV
from database import engine, SessionLocal, Base
from models import Mission, User
from auth import hash_password

# 주차별 스케줄 (시험기간 제외)
# 미션 번호 → (시작일, 종료일)
MISSION_SCHEDULE = {
    0:  ("2026-03-30", "2026-04-10"),  # Git/GitHub 가이드
    1:  ("2026-04-06", "2026-04-11"),
    # 중간고사: 04/13 ~ 04/24
    2:  ("2026-04-27", "2026-05-02"),
    3:  ("2026-05-04", "2026-05-09"),
    4:  ("2026-05-11", "2026-05-16"),
    5:  ("2026-05-18", "2026-05-23"),
    6:  ("2026-05-25", "2026-05-30"),
    7:  ("2026-06-01", "2026-06-06"),
    # 기말고사: 06/08 ~ 06/19
    8:  ("2026-06-22", "2026-06-27"),
    9:  ("2026-06-29", "2026-07-04"),
    10: ("2026-07-06", "2026-07-11"),
}


def update_mission_schedule(db):
    """기존 미션의 시작일/종료일을 MISSION_SCHEDULE에 맞게 업데이트"""
    missions = db.query(Mission).all()
    updated = 0
    for m in missions:
        schedule = MISSION_SCHEDULE.get(m.number)
        if not schedule:
            continue
        start_date = datetime.strptime(schedule[0], "%Y-%m-%d")
        end_date = datetime.strptime(schedule[1], "%Y-%m-%d").replace(hour=23, minute=59, second=59)
        if m.start_date != start_date or m.end_date != end_date:
            m.start_date = start_date
            m.end_date = end_date
            updated += 1
    if updated:
        db.commit()
        print(f"{updated}개 미션 스케줄이 업데이트되었습니다.")


def seed_missions(db):
    if db.query(Mission).count() > 0:
        print("미션 데이터가 이미 존재합니다. 스케줄만 업데이트합니다.")
        update_mission_schedule(db)
        return

    data_path = os.path.join(os.path.dirname(__file__), "missions.json")
    if not os.path.exists(data_path):
        print("missions.json 파일이 없습니다.")
        return

    with open(data_path, "r", encoding="utf-8") as f:
        missions = json.load(f)

    for m in missions:
        schedule = MISSION_SCHEDULE.get(m["number"])
        start_date = datetime.strptime(schedule[0], "%Y-%m-%d") if schedule else None
        end_date = datetime.strptime(schedule[1], "%Y-%m-%d").replace(hour=23, minute=59, second=59) if schedule else None

        mission = Mission(
            track=m["track"],
            number=m["number"],
            title=m["title"],
            description=m.get("description", ""),
            checklist=m.get("checklist", []),
            submission_type=m.get("submission_type", "github"),
            estimated_hours=m.get("estimated_hours", 20),
            pbl_link=m.get("pbl_link"),
            start_date=start_date,
            end_date=end_date,
        )
        db.add(mission)

    db.commit()
    print(f"{len(missions)}개 미션이 시드되었습니다. (주차별 기한 포함)")


def seed_admin(db):
    if db.query(User).filter(User.role == "admin").count() > 0:
        print("관리자 계정이 이미 존재합니다. 건너뜁니다.")
        return

    admin_pw = os.getenv("ADMIN_PASSWORD", "")
    if not admin_pw:
        if not IS_DEV:
            raise RuntimeError(
                "ADMIN_PASSWORD 환경변수가 설정되지 않았습니다. "
                "프로덕션에서는 .env에 ADMIN_PASSWORD를 반드시 설정하세요."
            )
        import secrets
        admin_pw = secrets.token_urlsafe(12)
        print(f"[DEV] ADMIN_PASSWORD 미설정. 임시 비밀번호: {admin_pw}")

    admin_email = os.getenv("ADMIN_EMAIL", "sunchon.univ@likelion.org")

    admin = User(
        name="운영진",
        email=admin_email,
        password_hash=hash_password(admin_pw),
        track="backend",
        role="admin",
        email_verified=True,
        approved=True,
        generation=14,
    )
    db.add(admin)
    db.commit()
    print(f"관리자 계정이 생성되었습니다. ({admin_email})")


def seed_tester(db):
    if db.query(User).filter(User.role == "tester").count() > 0:
        print("테스터 계정이 이미 존재합니다. 건너뜁니다.")
        return

    tester_pw = os.getenv("TESTER_PASSWORD", "")
    if not tester_pw:
        import secrets
        tester_pw = secrets.token_urlsafe(12)
        print(f"[!] TESTER_PASSWORD 미설정. 임시 비밀번호 생성됨. .env에 TESTER_PASSWORD를 설정하세요.")
    tester_email = os.getenv("TESTER_EMAIL", "test@likelion.org")

    tester = User(
        name="테스트 아기사자",
        email=tester_email,
        password_hash=hash_password(tester_pw),
        track="frontend",
        role="tester",
        email_verified=True,
        approved=True,
        generation=14,
    )
    db.add(tester)
    db.commit()
    print(f"테스터 계정이 생성되었습니다. ({tester_email})")


def run_seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_missions(db)
        seed_admin(db)
        seed_tester(db)
    finally:
        db.close()


if __name__ == "__main__":
    run_seed()
