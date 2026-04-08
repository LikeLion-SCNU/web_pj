import os

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간
ALGORITHM = "HS256"
MAX_SUBMISSIONS_PER_MISSION = 5
UPLOAD_DIR = "/app/uploads"

# 파일 업로드 제한
MAX_UPLOAD_SIZE = 5 * 1024 * 1024       # 5MB (사용자 업로드)
MAX_SCREENSHOT_SIZE = 10 * 1024 * 1024  # 10MB (AI 비전 분석용)

# AI 리뷰 설정
AI_MODEL = "gpt-4o-mini"
AI_MAX_TOKENS = 2500
AI_TEMPERATURE = 0.3
MAX_HTML_FETCH_SIZE = 30_000  # 배포 URL HTML 최대 문자 수

# SMTP (Gmail App Password)
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "sunchon.univ@likelion.org")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
CURRENT_GENERATION = int(os.getenv("CURRENT_GENERATION", "14"))

# Cloudflare Turnstile
TURNSTILE_SECRET_KEY = os.getenv("TURNSTILE_SECRET_KEY", "")

# 사이트 URL
SITE_URL = os.getenv("SITE_URL", "https://likelionscnu.site")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "https://likelionscnu.site,http://localhost:8888").split(",")

IS_DEV = (
    os.getenv("ENV", "production") == "development"
    or os.getenv("IS_DEV", "").lower() in ("1", "true", "yes")
)
