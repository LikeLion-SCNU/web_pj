# 순천대학교 멋쟁이사자처럼

전국 80개 대학, 2,500명이 함께하는 국내 최대 규모 IT 창업 동아리
**순천대학교 멋쟁이사자처럼** 공식 웹사이트 + PBL 과제 시스템입니다.

> **운영 URL**: https://likelionscnu.site

## 시스템 구성

### 1. 메인 홈페이지 (`/`)

동아리 소개, 활동, 팀원 소개, 모집 안내 페이지

| 섹션 | 설명 |
|------|------|
| **Hero** | 메인 비주얼, 동아리 소개 문구, 지원하기 CTA |
| **About** | 동아리 소개 및 특징 (코드 에디터 스타일 UI) |
| **Activities** | 주요 활동 - 세션, 프로젝트, 스터디, 네트워킹 |
| **Team** | 기수별(12~14기) 팀원 소개 (탭 전환) |
| **Recruit** | 14기 아기사자 모집 안내 및 지원서 링크 |

### 2. PBL 과제 시스템 (`/pages/`)

4개 트랙(프론트엔드, 백엔드, 기획, 디자인) × 11개 미션의 과제 제출·검사 시스템

| 기능 | 설명 |
|------|------|
| **과제 제출** | GitHub URL, Figma URL, 배포 URL, 스크린샷(최대 3장) |
| **AI 자동 검사** | GPT-4o-mini 기반 체크리스트 자동 채점 (점수 + 피드백) |
| **운영진 검사** | AI 검사 후 운영진 합격/반려 + 이메일 알림 발송 |
| **제출 기회** | 미션당 최대 5회 (3회부터 경고 표시) |
| **GitHub 코드 분석** | 커밋, 브랜치, PR, 코드 파일 자동 수집 (재시도 지원) |
| **스크린샷 AI 분석** | Vision API로 디자인/기획 스크린샷 시각 분석 |
| **미제출 경고** | 2회 이상 미제출 학생 경고 목록 |

## 프로젝트 구조

```
scnu-likelion/
├── index.html                # 메인 홈페이지
├── css/style.css             # 홈페이지 스타일
├── js/script.js              # 홈페이지 인터랙션
├── images/                   # 로고, 팀원 사진, OG 이미지
│
├── pages/                    # PBL 과제 시스템 (프론트엔드)
│   ├── login.html            # 로그인/회원가입
│   ├── missions.html         # 미션 목록
│   ├── submit.html           # 미션 상세 + 과제 제출
│   ├── my.html               # 내 제출 현황
│   ├── admin/dashboard.html  # 운영진 대시보드
│   ├── css/pbl.css           # PBL 스타일
│   └── js/
│       ├── pbl.js            # PBL 공통 로직
│       └── admin-dashboard.js
│
├── api/                      # FastAPI 백엔드
│   ├── main.py               # 앱 진입점 (CORS, 보안 헤더)
│   ├── config.py             # 환경변수 설정
│   ├── models.py             # SQLAlchemy 모델
│   ├── database.py           # DB 연결
│   ├── auth.py               # JWT 인증
│   ├── seed.py               # 미션 시드 + 콘텐츠 동기화
│   ├── missions.json         # 4트랙 × 11미션 데이터
│   ├── routers/
│   │   ├── auth_router.py          # 회원가입, 로그인, 이메일 인증
│   │   ├── missions_router.py      # 미션 목록/상세
│   │   ├── submissions_router.py   # 과제 제출 (스크린샷 3장)
│   │   └── admin_router.py         # 운영진 관리
│   └── services/
│       ├── ai_reviewer.py          # AI 자동 채점
│       ├── prompts.py              # AI 프롬프트 + 트랙별 가이드
│       ├── submission_context.py   # 제출물 컨텍스트 조립
│       ├── github_fetcher.py       # GitHub API 코드 수집
│       ├── deploy_analyzer.py      # 배포 URL 분석 (SSRF 방어)
│       └── email_service.py        # 이메일 발송
│
├── nginx.conf                # Nginx (리버스 프록시, CSP, Rate Limit)
├── docker-compose.yml        # Docker Compose (web + api + db)
├── Dockerfile                # Nginx 컨테이너
└── api/Dockerfile            # FastAPI 컨테이너
```

## 기술 스택

| 구분 | 기술 |
|------|------|
| **프론트엔드** | HTML5, CSS3, Vanilla JavaScript (ES6+) |
| **백엔드** | FastAPI, SQLAlchemy, Pydantic |
| **데이터베이스** | PostgreSQL 16 |
| **AI** | OpenAI GPT-4o-mini (Vision 멀티모달) |
| **인프라** | Docker Compose, Nginx, Uvicorn |
| **보안** | JWT (bcrypt), Cloudflare Turnstile, CSP, Rate Limiting |
| **이메일** | SMTP (Gmail App Password) |

## PBL 트랙 구성

| 트랙 | 미션 | 제출 방식 | AI 검사 |
|------|------|----------|---------|
| **백엔드** (Spring Boot) | 0~10 | GitHub URL | 코드 분석 |
| **프론트엔드** (React) | 0~10 | GitHub + 배포 URL | 코드 + HTML 분석 |
| **기획** (PM) | 0~10 | GitHub + Figma + 스크린샷 | 스크린샷 시각 분석 |
| **디자인** (Figma) | 0~10 | Figma URL + 스크린샷 | 스크린샷 시각 분석 |

## 배포

### Docker (운영 서버)

```bash
# 최초 배포
git clone https://github.com/LikeLion-SCNU/web_pj.git
cd web_pj && git checkout develop
cp .env.example .env  # 환경변수 설정 후 편집
sudo docker-compose up -d --build

# 업데이트 배포
git pull && sudo docker-compose down && sudo docker-compose up -d --build
sudo docker exec scnu-likelion-api python seed.py
```

### 환경변수 (.env)

`.env.example` 파일을 참고하세요. 주요 항목:

| 변수 | 설명 |
|------|------|
| `SECRET_KEY` | JWT 시크릿 키 |
| `DATABASE_URL` | PostgreSQL 연결 URL |
| `OPENAI_API_KEY` | GPT-4o-mini API 키 |
| `GITHUB_TOKEN` | GitHub API 토큰 (코드 분석용) |
| `SMTP_PASSWORD` | Gmail 앱 비밀번호 |
| `ADMIN_PASSWORD` | 초기 운영진 비밀번호 |
| `TURNSTILE_SECRET_KEY` | Cloudflare Turnstile 시크릿 |

### DB 마이그레이션

스키마 변경 시 수동 실행:
```bash
sudo docker exec scnu-likelion-db psql -U [USER] -d [DB] -c "ALTER TABLE ..."
```

## Git 브랜치 전략

```
main ─────────────────────── (배포 전용, 검증 완료된 코드)
  │
  └─ develop ─────────────── (통합 브랜치, default)
       ├─ feat/기능명 ────→ PR to develop
       ├─ fix/버그명 ─────→ PR to develop
       └─ hotfix/긴급 ───→ PR to main + develop
```

## 콘텐츠 수정 가이드

### 모집 기간 변경

`js/script.js`의 `checkRecruitmentStatus` 함수에서 날짜 수정

### 팀원 추가

`index.html`의 Team 섹션에 카드 추가:

```html
<div class="member-card">
    <div class="member-image">
        <img src="images/팀원사진.jpg" alt="이름">
    </div>
    <div class="member-info">
        <h3 class="member-name">이름</h3>
        <p class="member-role">역할</p>
        <p class="member-major">학과 학번</p>
    </div>
</div>
```

### 미션 수정

`api/missions.json`에서 체크리스트, 설명, 시간 등을 수정한 뒤 배포 시 `seed.py` 실행으로 DB 자동 동기화

## 문의

- 이메일: sunchon.univ@likelion.org
- 인스타그램: [@likelion_scnu](https://instagram.com/likelion_scnu)
- 오픈카톡: https://open.kakao.com/o/skAGSC1h
