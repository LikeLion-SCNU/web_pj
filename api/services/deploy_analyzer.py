"""배포 URL에서 HTML을 가져와 구조를 분석하는 서비스"""
import re
import socket
from ipaddress import ip_address
from urllib.parse import urljoin, urlparse

import httpx


def _is_safe_ip(ip_str: str) -> bool:
    """IP 주소가 안전한지 검증 (private, loopback, link-local, reserved 차단)"""
    try:
        ip = ip_address(ip_str)
        if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
            return False
        # cloud metadata endpoint 차단 (169.254.169.254)
        if ip_str == "169.254.169.254":
            return False
        # IPv4-mapped IPv6 (::ffff:127.0.0.1 등)
        if hasattr(ip, "ipv4_mapped") and ip.ipv4_mapped:
            return _is_safe_ip(str(ip.ipv4_mapped))
        return True
    except ValueError:
        return False


def _resolve_and_validate(hostname: str) -> bool:
    """DNS 해석 후 실제 IP가 안전한지 검증 (DNS rebinding 방어)

    주의: TOCTOU gap이 존재합니다. 이 함수에서 DNS를 해석한 뒤 httpx가 다시 DNS를
    해석하므로, 악성 DNS 서버가 첫 번째는 안전한 IP, 두 번째는 내부 IP를 반환할 수 있습니다.
    학생이 제출하는 배포 URL은 Vercel/Netlify 등 잘 알려진 호스팅이므로 위험은 낮습니다.
    """
    try:
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        for family, _, _, _, sockaddr in results:
            ip_str = sockaddr[0]
            if not _is_safe_ip(ip_str):
                return False
        return bool(results)
    except socket.gaierror:
        return False


def _is_safe_url(url: str) -> bool:
    """SSRF 방어: DNS 해석 + IP 검증으로 내부 네트워크 접근 차단"""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return False
        hostname = parsed.hostname
        if not hostname:
            return False
        # localhost 변형 차단
        if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1"):
            return False
        # DNS 해석 후 실제 IP 검증
        return _resolve_and_validate(hostname)
    except Exception:
        return False


def _extract_tag_content(html: str, tag: str) -> list[str]:
    """HTML에서 특정 태그의 텍스트 내용을 추출 (정규식 기반)"""
    pattern = re.compile(rf"<{tag}[^>]*>(.*?)</{tag}>", re.IGNORECASE | re.DOTALL)
    return [re.sub(r"<[^>]+>", "", m.strip()) for m in pattern.findall(html) if m.strip()]


def _extract_meta_tags(html: str) -> dict[str, str]:
    """meta 태그에서 name/content 쌍을 추출"""
    result = {}
    pattern = re.compile(
        r'<meta\s+[^>]*?(?:name|property)\s*=\s*["\']([^"\']+)["\'][^>]*?content\s*=\s*["\']([^"\']*)["\']',
        re.IGNORECASE,
    )
    for name, content in pattern.findall(html):
        result[name.lower()] = content[:200]
    return result


def _count_tags(html: str, tags: list[str]) -> dict[str, int]:
    """특정 태그의 출현 횟수를 카운트"""
    counts = {}
    for tag in tags:
        pattern = re.compile(rf"<{tag}[\s>]", re.IGNORECASE)
        counts[tag] = len(pattern.findall(html))
    return counts


def fetch_deploy_preview(url: str) -> str | None:
    """배포 URL에서 HTML을 가져와 구조 분석 결과를 반환"""
    if not url or not _is_safe_url(url):
        return None

    try:
        # follow_redirects=False: 리다이렉트로 내부 IP 우회 방지
        with httpx.Client(timeout=10, follow_redirects=False, verify=True) as client:
            resp = client.get(url, headers={
                "User-Agent": "LikeLion-PBL-Reviewer/1.0",
                "Accept": "text/html",
            })

        # 리다이렉트 시 대상 URL 재검증 (상대 경로 → 절대 경로 변환)
        if resp.status_code in (301, 302, 303, 307, 308):
            redirect_url = resp.headers.get("location", "")
            if redirect_url and not redirect_url.startswith(("http://", "https://")):
                redirect_url = urljoin(url, redirect_url)
            if not redirect_url or not _is_safe_url(redirect_url):
                return "배포 URL이 안전하지 않은 주소로 리다이렉트됩니다"
            with httpx.Client(timeout=10, follow_redirects=False, verify=True) as client:
                resp = client.get(redirect_url, headers={
                    "User-Agent": "LikeLion-PBL-Reviewer/1.0",
                    "Accept": "text/html",
                })

        if resp.status_code != 200:
            return f"HTTP {resp.status_code} 응답 (정상 접근 불가)"

        content_type = resp.headers.get("content-type", "")
        if "text/html" not in content_type:
            return f"HTML이 아닌 응답 (Content-Type: {content_type})"

        html = resp.text[:30000]  # 30KB까지만
        parts = []

        # 1. 제목
        titles = _extract_tag_content(html, "title")
        if titles:
            parts.append(f"- 페이지 제목: {titles[0][:100]}")

        # 2. 메타 태그
        metas = _extract_meta_tags(html)
        if metas.get("description"):
            parts.append(f"- 설명: {metas['description']}")
        if metas.get("og:title"):
            parts.append(f"- OG 제목: {metas['og:title']}")
        viewport = metas.get("viewport")
        if viewport:
            parts.append("- 반응형 메타태그: 있음 ✓")
        else:
            parts.append("- 반응형 메타태그: 없음 ✗")

        # 3. 구조 태그 카운트
        structure_tags = ["header", "nav", "main", "section", "article", "aside", "footer",
                          "div", "form", "input", "button", "a", "img", "table"]
        counts = _count_tags(html, structure_tags)

        semantic = {k: v for k, v in counts.items() if k in ("header", "nav", "main", "section", "article", "aside", "footer") and v > 0}
        if semantic:
            parts.append(f"- 시맨틱 태그: {', '.join(f'{k}({v})' for k, v in semantic.items())}")
        else:
            parts.append("- 시맨틱 태그: 없음 (div 위주 구조)")

        interactive = {k: v for k, v in counts.items() if k in ("form", "input", "button") and v > 0}
        if interactive:
            parts.append(f"- 인터랙티브 요소: {', '.join(f'{k}({v})' for k, v in interactive.items())}")

        parts.append(f"- 링크(a): {counts.get('a', 0)}개, 이미지(img): {counts.get('img', 0)}개")

        # 4. 제목 태그 (h1~h3)
        for h in ("h1", "h2", "h3"):
            headings = _extract_tag_content(html, h)
            if headings:
                items = [t[:60] for t in headings[:5]]
                parts.append(f"- {h} 태그: {', '.join(items)}")

        # 5. 외부 리소스 (CSS/JS 프레임워크 탐지)
        frameworks = []
        html_lower = html.lower()
        if "bootstrap" in html_lower:
            frameworks.append("Bootstrap")
        if "tailwind" in html_lower:
            frameworks.append("Tailwind CSS")
        if "react" in html_lower or "_next" in html_lower:
            frameworks.append("React/Next.js")
        if "vue" in html_lower:
            frameworks.append("Vue.js")
        if frameworks:
            parts.append(f"- 감지된 프레임워크: {', '.join(frameworks)}")

        # 6. CSS/JS 파일 수
        css_count = len(re.findall(r'<link[^>]+stylesheet', html, re.IGNORECASE))
        js_count = len(re.findall(r'<script[^>]+src=', html, re.IGNORECASE))
        parts.append(f"- 외부 CSS: {css_count}개, 외부 JS: {js_count}개")

        return "\n".join(parts) if parts else None

    except httpx.TimeoutException:
        return "배포 URL 접근 시간 초과 (10초)"
    except Exception as e:
        return f"배포 URL 분석 실패: {type(e).__name__}"
