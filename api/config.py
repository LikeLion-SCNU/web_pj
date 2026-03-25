import os

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://likelion:password@db:5432/likelion_pbl")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days
ALGORITHM = "HS256"
MAX_SUBMISSIONS_PER_MISSION = 2
UPLOAD_DIR = "/app/uploads"
