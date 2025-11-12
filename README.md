# 순천대학교 멋쟁이사자처럼 웹사이트

순천대학교 멋쟁이사자처럼 동아리의 소개 및 모집 웹사이트입니다.

## 프로젝트 구조

```
sunchon-likelion/
├── index.html          # 메인 페이지
├── css/
│   └── style.css       # 스타일시트
├── js/
│   └── script.js       # JavaScript 인터랙션
├── images/             # 이미지 파일 (로고, 팀원 사진 등)
└── assets/             # 기타 리소스
```

## 주요 기능

### 1. 반응형 네비게이션
- 데스크톱: 고정형 헤더 네비게이션
- 모바일: 햄버거 메뉴
- 스크롤 시 네비게이션 활성화 표시

### 2. 섹션 구성
- **Hero**: 메인 비주얼 및 CTA 버튼
- **About**: 동아리 소개 및 특징
- **Activities**: 주요 활동 소개 (세션, 프로젝트, 스터디, 네트워킹)
- **Team**: 기수별 팀원 소개
- **Recruit**: 신입 부원 모집 안내

### 3. 인터랙티브 요소
- 스크롤 애니메이션 (Fade In)
- 팀원 탭 전환 (기수별)
- 모집 기간 자동 확인
- 부드러운 스크롤 이동

### 4. 디자인
- 모던하고 미니멀한 디자인
- 멋쟁이사자처럼 브랜드 컬러 (오렌지 #FF7710)
- 완전 반응형 (모바일, 태블릿, 데스크톱)

## 사용 방법

### 로컬 실행
1. 웹 브라우저로 `index.html` 파일을 엽니다
2. 또는 Live Server를 사용하여 로컬 서버로 실행합니다

### 콘텐츠 수정

#### 팀원 정보 수정
`index.html`의 Team Section에서 팀원 카드를 추가/수정합니다:
```html
<div class="member-card">
    <div class="member-image">
        <img src="images/member-name.jpg" alt="이름">
    </div>
    <div class="member-info">
        <h3 class="member-name">이름</h3>
        <p class="member-role">역할 / 포지션</p>
        <p class="member-major">학과 학번</p>
    </div>
</div>
```

#### 모집 기간 수정
`js/script.js`의 `checkRecruitmentStatus` 함수에서 날짜를 수정합니다:
```javascript
const recruitmentStart = new Date('2025-03-01');
const recruitmentEnd = new Date('2025-03-15');
```

#### 지원서 링크 연결
`index.html`의 모집 섹션에서 지원 버튼의 링크를 수정합니다:
```html
<a href="https://forms.google.com/your-form" class="apply-button">지원서 작성하기</a>
```

#### 연락처 정보 수정
`index.html`의 Recruit Section에서 연락처를 수정합니다:
```html
<p>📧 이메일: your-email@example.com</p>
<p>📱 인스타그램: @your_instagram</p>
<p>💬 오픈카톡: [링크]</p>
```

### 이미지 추가
다음 이미지들을 `images/` 폴더에 추가하세요:
- `logo.png` - 멋쟁이사자처럼 로고
- `session.jpg` - 세션 활동 사진
- `project.jpg` - 프로젝트 활동 사진
- `study.jpg` - 스터디 활동 사진
- `networking.jpg` - 네트워킹 활동 사진
- `member-*.jpg` - 팀원 프로필 사진

이미지가 없어도 placeholder로 대체되어 표시됩니다.

## 배포

### GitHub Pages
1. GitHub 저장소 생성
2. 코드 업로드
3. Settings > Pages에서 배포 설정

### Netlify
1. Netlify에 로그인
2. "New site from Git" 선택
3. 저장소 연결 및 배포

### Vercel
1. Vercel에 로그인
2. "Import Project" 선택
3. 저장소 연결 및 배포

## 브라우저 호환성
- Chrome (최신)
- Firefox (최신)
- Safari (최신)
- Edge (최신)

## 기술 스택
- HTML5
- CSS3 (Grid, Flexbox, Animations)
- Vanilla JavaScript (ES6+)

## 커스터마이징

### 색상 변경
`css/style.css`의 `:root` 변수에서 색상을 변경할 수 있습니다:
```css
:root {
    --primary-color: #FF7710;     /* 메인 컬러 */
    --primary-dark: #E66600;      /* 메인 컬러 (어두움) */
    --primary-light: #FFA652;     /* 메인 컬러 (밝음) */
    /* ... */
}
```

### 폰트 변경
`css/style.css`의 `:root` 변수에서 폰트를 변경할 수 있습니다:
```css
:root {
    --font-primary: -apple-system, BlinkMacSystemFont, "Segoe UI", ...;
}
```

## 라이센스
이 프로젝트는 순천대학교 멋쟁이사자처럼을 위해 제작되었습니다.

## 문의
순천대학교 멋쟁이사자처럼
- 이메일: likelion.sunchon@example.com
- 인스타그램: @likelion_sunchon
