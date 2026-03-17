# 순천대학교 멋쟁이사자처럼

전국 80개 대학, 2,500명이 함께하는 국내 최대 규모 IT 창업 동아리
**순천대학교 멋쟁이사자처럼** 공식 웹사이트입니다.

## 프로젝트 구조

```
scnu-likelion/
├── index.html          # 메인 페이지 (SPA)
├── css/
│   └── style.css       # 스타일시트 (다크 테마)
├── js/
│   └── script.js       # 인터랙션 및 모집 상태 관리
├── images/             # 로고, 팀원 사진, OG 이미지
├── Dockerfile          # Docker 빌드 설정
└── docker-compose.yml  # Docker Compose 배포 설정
```

## 섹션 구성

| 섹션 | 설명 |
|------|------|
| **Hero** | 메인 비주얼, 동아리 소개 문구, 지원하기 CTA |
| **About** | 동아리 소개 및 특징 (코드 에디터 스타일 UI) |
| **Activities** | 주요 활동 - 세션, 프로젝트, 스터디, 네트워킹 |
| **Team** | 기수별(12~14기) 팀원 소개 (탭 전환) |
| **Recruit** | 14기 아기사자 모집 안내 및 지원서 링크 |

## 주요 기능

- **반응형 디자인**: 모바일 / 태블릿 / 데스크톱 완전 대응
- **다크 테마**: IT 감성의 다크 배경 + 오렌지(#FF7710) 브랜드 컬러
- **모집 기간 자동 관리**: `js/script.js`에서 날짜 기반으로 지원 버튼 활성화/비활성화
- **스크롤 애니메이션**: Intersection Observer 기반 Fade In
- **기수별 팀원 탭**: 12기 ~ 14기 팀원 전환
- **긴급 공지 팝업**: 필요 시 바텀시트 스타일 공지 표시 (모바일 반응형)

## 배포

### Docker (운영 서버)

```bash
git fetch origin && git reset --hard origin/main
sudo docker-compose down && sudo docker-compose up -d --build
```

### 로컬 개발

브라우저에서 `index.html`을 열거나 Live Server로 실행합니다.

## 콘텐츠 수정 가이드

### 모집 기간 변경

`js/script.js`의 `checkRecruitmentStatus` 함수:

```javascript
const recruitmentEnd = new Date(2026, 2, 13, 23, 59, 59); // 월은 0부터 시작 (2 = 3월)
```

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

### 색상 커스터마이징

`css/style.css`의 `:root` 변수:

```css
:root {
    --primary-color: #FF7710;
    --primary-dark: #E66600;
    --primary-light: #FFA652;
}
```

## 기술 스택

- HTML5 / CSS3 (Grid, Flexbox, CSS Variables)
- Vanilla JavaScript (ES6+)
- Docker + Nginx
- Font Awesome 6

## 문의

- 이메일: sunchon.univ@likelion.org
- 인스타그램: [@likelion_scnu](https://instagram.com/likelion_scnu)
- 오픈카톡: https://open.kakao.com/o/skAGSC1h
