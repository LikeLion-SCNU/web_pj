import os

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL 환경변수가 설정되지 않았습니다. .env 파일을 확인하세요.")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN", "")
FIGMA_TOKEN = os.getenv("FIGMA_TOKEN", "")

# Figma API 베이스 URL — 기본은 직접 호출이지만, NAS 외부 IP가 Figma 인프라(AWS CloudFront WAF)에
# 차단된 경우 Cloudflare Worker 프록시 URL로 오버라이드한다.
# 예) https://scnufigma-proxy.<account>.workers.dev/v1
FIGMA_API_BASE = os.getenv("FIGMA_API_BASE", "https://api.figma.com/v1")
# Worker 프록시 사용 시 인증 헤더(X-Proxy-Auth)에 실릴 비밀값. Worker의 PROXY_SECRET과 동일해야 한다.
FIGMA_PROXY_SECRET = os.getenv("FIGMA_PROXY_SECRET", "")

# Figma fetch 설정
FIGMA_MAX_NODES_SAMPLED = 30   # 샘플링할 최대 프레임/컴포넌트 수
FIGMA_MAX_THUMBNAILS = 3       # Vision API 전달 최대 썸네일 수
FIGMA_MAX_FILE_DEPTH = 4       # 문서 트리 탐색 최대 깊이
FIGMA_MAX_NODES_VISITED = 2000 # 트리 순회 시 최대 방문 노드 수
FIGMA_REQUEST_TIMEOUT = 15     # 초

ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24시간
ALGORITHM = "HS256"
MAX_SUBMISSIONS_PER_MISSION = 5
UPLOAD_DIR = "/app/uploads"

# 파일 업로드 제한
MAX_UPLOAD_SIZE = 5 * 1024 * 1024       # 5MB (사용자 업로드)
MAX_SCREENSHOT_SIZE = 10 * 1024 * 1024  # 10MB (AI 비전 분석용)

# AI 리뷰 설정 — Google Gemini를 OpenAI 호환 엔드포인트로 호출 (SDK는 openai 유지)
AI_MODEL = "gemini-2.5-flash"
AI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
AI_MAX_TOKENS = 2500
AI_TEMPERATURE = 0.1
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

REGISTRATION_OPEN = os.getenv("REGISTRATION_OPEN", "false").lower() in ("1", "true", "yes")
