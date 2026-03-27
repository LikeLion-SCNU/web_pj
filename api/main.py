import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from database import engine, Base
from routers import auth_router, missions_router, submissions_router, admin_router
from seed import run_seed

IS_DEV = os.getenv("ENV", "production") == "development"


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
    allow_origins=["https://likelionscnu.site", "http://localhost:8888"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/uploads", StaticFiles(directory="/app/uploads"), name="uploads")

app.include_router(auth_router.router)
app.include_router(missions_router.router)
app.include_router(submissions_router.router)
app.include_router(admin_router.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
