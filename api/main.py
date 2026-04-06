import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from auth import get_current_user
from config import CORS_ORIGINS, IS_DEV, UPLOAD_DIR
from database import engine, Base
from routers import auth_router, missions_router, submissions_router, admin_router
from seed import run_seed


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    run_seed()
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
    return {"status": "ok"}
