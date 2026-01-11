# 시놀로지 NAS & Cloudflare 배포 가이드

이 가이드는 Docker("Container Manager")와 Cloudflare Tunnel을 사용하여 정적 웹사이트를 시놀로지 NAS에 배포하고 안전하게 외부에서 접속하도록 설정하는 방법을 설명합니다.

## 준비물

1.  **시놀로지 NAS**: 패키지 센터에서 "Container Manager" (구 Docker)가 설치되어 있어야 합니다.
2.  **Cloudflare 계정**: 무료 플랜이면 충분합니다.
3.  **도메인**: Cloudflare에서 구입했거나 Cloudflare로 네임서버가 연동된 도메인.

---

## 1단계: 도메인 및 Cloudflare 설정

아직 도메인이 없다면 Cloudflare에서 직접 구입하는 것이 가장 설정하기 쉽습니다.

1.  [Cloudflare 대시보드](https://dash.cloudflare.com/)에 로그인합니다.
2.  **도메인 구입** (없는 경우): **Domain Registration** > **Register Domain** 메뉴에서 원하는 도메인을 검색하고 구입합니다.
3.  **사이트 추가** (타사에서 구입한 경우): **Add a Site**를 클릭하고 도메인을 입력한 뒤 **Free** 플랜을 선택합니다. 그 후 도메인 등록 업체(가비아, 호스팅케이알 등)에서 네임서버를 Cloudflare가 알려주는 주소로 변경합니다.

---

## 2단계: NAS에 웹 서버 배포하기

NAS에 파일을 올리고 실행하는 방법은 두 가지가 있습니다. **Container Manager(GUI)** 를 사용하는 방법을 추천합니다.

### 방법 A: Container Manager 사용 (추천)

1.  **파일 업로드**:
    - 시놀로지 NAS의 "File Station"을 엽니다.
    - `docker` 폴더 안에 `scnu-likelion` 폴더를 새로 만듭니다.
    - 프로젝트의 모든 파일(`index.html`, `css/`, `js/`, `images/`, `Dockerfile`, `docker-compose.yml`)을 이 폴더에 업로드합니다.

2.  **프로젝트 생성**:
    - **Container Manager**를 실행합니다.
    - **프로젝트(Project)** 메뉴로 이동하여 **생성(Create)**을 클릭합니다.
    - **프로젝트 이름**: `scnu-likelion`.
    - **경로**: 방금 파일을 업로드한 폴더(`docker/scnu-likelion`)를 선택합니다.
    - **소스**: "기존 docker-compose.yml 사용"을 선택합니다.
    - **다음/완료**를 클릭하면 NAS가 스스로 이미지를 빌드하고 웹 서버를 실행합니다.

3.  **확인**:
    - 인터넷 브라우저 주소창에 `http://<NAS_내부IP>:8888` (예: `192.168.0.10:8888`)을 입력하여 사이트가 잘 뜨는지 확인합니다.

---

## 3단계: Cloudflare Tunnel로 외부 접속 설정 (포트포워딩 불필요)

이 방식은 공유기의 포트포워딩 설정이 필요 없어 보안상 매우 안전합니다.

1.  **Tunnel 생성**:
    - Cloudflare 대시보드 왼쪽 메뉴에서 **Zero Trust**를 클릭합니다 (처음이면 설정 진행).
    - **Networks** > **Tunnels**로 이동합니다.
    - **Create a Tunnel**을 클릭하고 **Cloudflared**를 선택합니다.
    - 이름은 아무거나 입력합니다 (예: `nas-tunnel`).

2.  **NAS에 커넥터 설치**:
    - "Install and run a connector" 화면에서 **Docker** 아이콘을 클릭합니다.
    - 아래에 나오는 긴 명령어(`docker run ... token ...`)를 복사해둡니다.
    - **시놀로지 NAS로 돌아와서**:
        - SSH를 사용할 줄 안다면 복사한 명령어를 터미널에 붙여넣기만 하면 끝입니다.
        - **SSH를 모른다면**:
            1. Container Manager > **레지스트리** > `cloudflare/cloudflared` 검색 및 다운로드(`latest`).
            2. **이미지** 탭 > 방금 받은 이미지 선택 > **실행**.
            3. 네트워크는 `bridge` 유지.
            4. **설정** 단계에서 "명령(Command)" 부분에 위에서 복사한 명령어 뒷부분(`tunnel run --token ...`)을 입력해야 하는데, 이 과정이 복잡할 수 있습니다.
            5. **가장 쉬운 방법**: 2단계처럼 **프로젝트(Project)** 메뉴에서 `cloudflare-tunnel` 폴더를 만들고 `docker-compose.yml` 파일을 하나 만듭니다.
               ```yaml
               version: '3'
               services:
                 tunnel:
                   image: cloudflare/cloudflared:latest
                   command: tunnel run --token <여기에_복사한_토큰을_붙여넣으세요>
                   restart: always
               ```
               이 파일을 업로드하고 프로젝트를 실행하면 연결됩니다.

3.  **공개 호스트네임(Public Hostname) 연결**:
    - Cloudflare 화면에서 커넥터 상태가 **Healthy(연결됨)** 로 바뀌면 **Next**를 누릅니다.
    - **Public Hostnames** 탭에서 **Add a Public Hostname**을 누릅니다.
    - **Subdomain**: 원하는 주소 (예: `www`. 루트 도메인을 원하면 비워둠).
    - **Domain**: 구입한 도메인 선택.
    - **Service**:
        - **Type**: `HTTP`
        - **URL**: `http://<NAS_내부IP>:8888` (예: `192.168.0.10:8888`).
    - **Save Tunnel**을 클릭합니다.

4.  **완료**:
    - 이제 주소창에 `https://yourdomain.com`을 입력하면 전 세계 어디서든 NAS에 있는 웹사이트에 접속할 수 있습니다.
