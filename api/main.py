import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from auth import get_current_user
from config import CORS_ORIGINS, IS_DEV, REGISTRATION_OPEN, UPLOAD_DIR
from database import engine, Base
from routers import auth_router, missions_router, submissions_router, admin_router
from seed import run_seed


def _validate_track_progression() -> None:
    """missions.json의 모든 (track, number)에 대응하는 TRACK_PROGRESSION 엔트리가 있는지 검사.

    누락 시 startup에서 명시적으로 경고 — 미션 추가/순서 변경으로 인한 silent
    드리프트를 즉시 발견하여 AI 평가 품질 저하를 예방. 검증은 advisory이며,
    파일 손상/형식 오류로 인해 서버 기동을 막지 않는다.
    """
    try:
        from services.prompts import TRACK_PROGRESSION

        missions_path = Path(__file__).parent / "missions.json"
        if not missions_path.exists():
            print("[STARTUP] missions.json을 찾을 수 없어 progression 검증을 건너뜁니다.")
            return

        with open(missions_path, encoding="utf-8") as f:
            missions = json.load(f)

        missing = [
            f"{m['track']}/{m['number']}"
            for m in missions
            if not TRACK_PROGRESSION.get(m["track"], {}).get(m["number"])
        ]
        if missing:
            print(
                f"[STARTUP WARNING] TRACK_PROGRESSION 누락 ({len(missing)}개): {missing}\n"
                f"  → api/services/prompts.py의 TRACK_PROGRESSION에 누락 항목 추가 필요. "
                f"AI 평가 시 해당 미션의 학습 맥락이 비어 평가 품질 저하 가능."
            )
        else:
            print(f"[STARTUP] TRACK_PROGRESSION 검증 OK ({len(missions)}개 미션 모두 매칭)")
    except (json.JSONDecodeError, KeyError, OSError, ImportError) as e:
        print(f"[STARTUP WARNING] TRACK_PROGRESSION 검증 실패 (advisory, 무시하고 진행): {type(e).__name__}: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"[STARTUP] REGISTRATION_OPEN={REGISTRATION_OPEN}")
    Base.metadata.create_all(bind=engine)
    run_seed()
    _validate_track_progression()
    yield


app = FastAPI(
    title="LIKELION SCNU PBL API",
    lifespan=lifespan,
    docs_url="/docs" if IS_DEV else None,
    redoc_url="/redoc" if IS_DEV else None,
    openapi_url="/openapi.json" if IS_DEV else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/uploads/{filename}")
def serve_upload(filename: str, user=Depends(get_current_user)):
    """인증된 사용자만 업로드 파일에 접근 가능"""
    safe_name = os.path.basename(filename)
    file_path = Path(UPLOAD_DIR) / safe_name
    file_path = file_path.resolve()
    if not str(file_path).startswith(str(Path(UPLOAD_DIR).resolve())):
        raise HTTPException(403, "접근이 거부되었습니다")
    if not file_path.exists():
        raise HTTPException(404, "파일을 찾을 수 없습니다")
    return FileResponse(
        file_path,
        headers={"Content-Disposition": f'inline; filename="{safe_name}"'},
    )

app.include_router(auth_router.router)
app.include_router(missions_router.router)
app.include_router(submissions_router.router)
app.include_router(admin_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "registration_open": REGISTRATION_OPEN}
