import os

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://likelion:password@db:5432/likelion_pbl")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간
ALGORITHM = "HS256"
MAX_SUBMISSIONS_PER_MISSION = 2
UPLOAD_DIR = "/app/uploads"

# SMTP (Gmail App Password)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "sunchon.univ@likelion.org")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
CURRENT_GENERATION = int(os.getenv("CURRENT_GENERATION", "14"))
