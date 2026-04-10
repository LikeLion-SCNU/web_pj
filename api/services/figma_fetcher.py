"""Figma REST API로 파일 구조와 썸네일을 가져오는 서비스"""
import base64
import re
import time
from urllib.parse import urlparse

import httpx

from config import (
    FIGMA_TOKEN,
    FIGMA_MAX_NODES_SAMPLED,
    FIGMA_MAX_THUMBNAILS,
    FIGMA_MAX_FILE_DEPTH,
    FIGMA_MAX_NODES_VISITED,
    FIGMA_REQUEST_TIMEOUT,
)

FIGMA_API_BASE = "https://api.figma.com/v1"
_ALLOWED_FIGMA_HOSTS = {"www.figma.com", "figma.com"}
_VALID_FILE_KEY = re.compile(r"^[a-zA-Z0-9]{10,64}$")
_FIGMA_PATH_PATTERN = re.compile(r"^/(?:file|design|proto)/([a-zA-Z0-9]{10,64})(?:/|$)")
_VALID_NODE_ID = re.compile(r"^\d+:\d+$")


def parse_figma_url(url: str) -> str | None:
    """Figma URL에서 file_key를 추출 (SSRF 방어 포함).

    허용 형식:
      - https://www.figma.com/design/{fileKey}/...
      - https://www.figma.com/file/{fileKey}/...
      - https://www.figma.com/proto/{fileKey}/...
    """
    if not url:
        return None
    try:
        parsed = urlparse(url.strip())
        if parsed.scheme not in ("http", "https"):
            return None
        if parsed.hostname not in _ALLOWED_FIGMA_HOSTS:
            return None
        match = _FIGMA_PATH_PATTERN.match(parsed.path)
        if not match:
            return None
        file_key = match.group(1)
        if not _VALID_FILE_KEY.match(file_key):
            return None
        return file_key
    except Exception:
        return None


def _get_headers() -> dict:
    if not FIGMA_TOKEN:
        return {}
    return {"X-Figma-Token": FIGMA_TOKEN}


def _sanitize_error_message(msg: str) -> str:
    """에러 메시지에서 토큰이 포함될 가능성을 제거"""
    if not msg:
        return ""
    if FIGMA_TOKEN and FIGMA_TOKEN in msg:
        msg = msg.replace(FIGMA_TOKEN, "[REDACTED]")
    return msg[:200]


def validate_token() -> bool:
    """토큰이 유효한지 확인 (/v1/me 호출)"""
    if not FIGMA_TOKEN:
        return False
    try:
        with httpx.Client(timeout=FIGMA_REQUEST_TIMEOUT) as client:
            resp = client.get(f"{FIGMA_API_BASE}/me", headers=_get_headers())
            return resp.status_code == 200
    except Exception:
        return False


def _walk_nodes_count(node: dict, counts: dict, depth: int = 0) -> None:
    """노드 트리를 재귀적으로 순회하며 통계 수집"""
    if depth > FIGMA_MAX_FILE_DEPTH:
        counts["truncated"] = True
        return
    counts["nodes_visited"] += 1
    if counts["nodes_visited"] > FIGMA_MAX_NODES_VISITED:
        counts["truncated"] = True
        return

    node_type = node.get("type", "")

    if node_type == "FRAME":
        counts["total_frames"] += 1
    elif node_type == "COMPONENT":
        counts["total_components_in_tree"] += 1
    elif node_type == "COMPONENT_SET":
        counts["total_component_sets_in_tree"] += 1
    elif node_type == "TEXT":
        counts["text_layers"] += 1

    # Auto Layout 감지
    layout_mode = node.get("layoutMode")
    if layout_mode and layout_mode != "NONE":
        counts["auto_layout_count"] += 1

    # 자식 노드 재귀
    children = node.get("children", [])
    for child in children:
        _walk_nodes_count(child, counts, depth + 1)


def _summarize_document(file_data: dict) -> dict:
    """Figma API 응답을 요약 구조로 변환"""
    document = file_data.get("document", {})
    pages = document.get("children", [])

    counts = {
        "nodes_visited": 0,
        "total_frames": 0,
        "total_components_in_tree": 0,
        "total_component_sets_in_tree": 0,
        "text_layers": 0,
        "auto_layout_count": 0,
        "truncated": False,
    }

    page_summaries = []
    sampled_frames = []
    top_frame_ids = []

    for page in pages:
        if page.get("type") != "CANVAS":
            continue
        page_name = page.get("name", "Untitled")
        page_children = page.get("children", [])
        page_frame_count = sum(1 for c in page_children if c.get("type") == "FRAME")

        page_summaries.append({
            "id": page.get("id", ""),
            "name": page_name[:100],
            "frame_count": page_frame_count,
        })

        # 최상위 프레임 샘플링 (썸네일용 + 프롬프트용)
        for child in page_children:
            if child.get("type") != "FRAME":
                continue
            if len(sampled_frames) < FIGMA_MAX_NODES_SAMPLED:
                bbox = child.get("absoluteBoundingBox") or {}
                sampled_frames.append({
                    "id": child.get("id", ""),
                    "name": (child.get("name") or "")[:100],
                    "page": page_name[:50],
                    "width": int(bbox.get("width", 0)),
                    "height": int(bbox.get("height", 0)),
                    "children_count": len(child.get("children", [])),
                })
            if len(top_frame_ids) < FIGMA_MAX_THUMBNAILS and child.get("id"):
                top_frame_ids.append(child["id"])

        # 전체 트리 통계
        _walk_nodes_count(page, counts)

    # 파일 수준 컴포넌트/스타일
    components = file_data.get("components") or {}
    component_sets = file_data.get("componentSets") or {}
    styles = file_data.get("styles") or {}

    # Figma API는 camelCase(styleType)와 snake_case(style_type) 모두 존재한 이력 → 양쪽 체크
    style_counts = {"FILL": 0, "TEXT": 0, "EFFECT": 0, "GRID": 0}
    for style in styles.values():
        style_type = (style.get("styleType") or style.get("style_type") or "").upper()
        if style_type in style_counts:
            style_counts[style_type] += 1

    return {
        "file_name": (file_data.get("name") or "")[:200],
        "last_modified": file_data.get("lastModified", ""),
        "version": file_data.get("version", ""),
        "thumbnail_url": file_data.get("thumbnailUrl", ""),
        "page_count": len(page_summaries),
        "pages": page_summaries[:20],
        "total_frames": counts["total_frames"],
        "total_components": len(components),
        "total_component_sets": len(component_sets),
        "text_layers": counts["text_layers"],
        "has_auto_layout": counts["auto_layout_count"] > 0,
        "auto_layout_count": counts["auto_layout_count"],
        "style_counts": style_counts,
        "total_styles": sum(style_counts.values()),
        "sampled_frames": sampled_frames,
        "top_frame_ids": top_frame_ids,
        "truncated": counts["truncated"],
    }


def _fetch_file_once(file_key: str) -> dict:
    """Figma 파일 정보를 한 번 시도하여 가져옴.

    Returns:
        성공: {...summary...}
        실패: {"error": "...", "retriable": bool}
    """
    headers = _get_headers()
    try:
        with httpx.Client(timeout=FIGMA_REQUEST_TIMEOUT, follow_redirects=False) as client:
            resp = client.get(
                f"{FIGMA_API_BASE}/files/{file_key}",
                headers=headers,
                params={"depth": FIGMA_MAX_FILE_DEPTH},
            )
            if resp.status_code == 200:
                return _summarize_document(resp.json())
            elif resp.status_code == 403:
                return {
                    "error": "Figma 파일 접근 권한이 없습니다. 공유 설정에서 '링크가 있는 모든 사람 - 볼 수 있음'으로 변경해주세요.",
                    "retriable": False,
                }
            elif resp.status_code == 404:
                return {
                    "error": "Figma 파일을 찾을 수 없습니다. URL을 다시 확인해주세요.",
                    "retriable": False,
                }
            elif resp.status_code == 429:
                return {
                    "error": "Figma API 요청 한도 초과. 잠시 후 다시 시도해주세요.",
                    "retriable": True,
                }
            elif 500 <= resp.status_code < 600:
                return {
                    "error": f"Figma API 일시적 오류 (HTTP {resp.status_code})",
                    "retriable": True,
                }
            else:
                return {
                    "error": f"Figma API 오류 (HTTP {resp.status_code})",
                    "retriable": False,
                }
    except httpx.TimeoutException:
        return {"error": "Figma API 응답 시간 초과", "retriable": True}
    except Exception as e:
        return {
            "error": _sanitize_error_message(f"Figma API 호출 실패: {type(e).__name__}"),
            "retriable": True,
        }


def _fetch_thumbnails_once(file_key: str, node_ids: list[str]) -> dict[str, str]:
    """특정 노드들의 렌더링 이미지 URL을 가져옴"""
    # 노드 ID 형식 검증 (defense in depth)
    valid_ids = [nid for nid in node_ids if nid and _VALID_NODE_ID.match(nid)]
    if not valid_ids:
        return {}
    headers = _get_headers()
    try:
        with httpx.Client(timeout=FIGMA_REQUEST_TIMEOUT, follow_redirects=False) as client:
            resp = client.get(
                f"{FIGMA_API_BASE}/images/{file_key}",
                headers=headers,
                params={
                    "ids": ",".join(valid_ids),
                    "format": "png",
                    "scale": "1",
                },
            )
            if resp.status_code != 200:
                return {}
            data = resp.json()
            images = data.get("images") or {}
            # {node_id: url or null} → {node_id: url} (null 제외)
            return {k: v for k, v in images.items() if v}
    except Exception:
        return {}


# Figma가 반환하는 썸네일 이미지 URL의 허용 호스트
_FIGMA_CDN_HOST_SUFFIXES = (
    ".figma.com",
    ".figma-alpha-api.s3.us-west-2.amazonaws.com",
    ".s3.amazonaws.com",
    ".s3-us-west-2.amazonaws.com",
)


def _is_safe_figma_cdn(url: str) -> bool:
    """썸네일 URL이 Figma CDN 허용 호스트인지 확인 (SSRF 방어)"""
    try:
        parsed = urlparse(url)
        if parsed.scheme != "https":
            return False
        host = parsed.hostname or ""
        return any(host == s.lstrip(".") or host.endswith(s) for s in _FIGMA_CDN_HOST_SUFFIXES)
    except Exception:
        return False


def _download_thumbnail_as_base64(url: str) -> str | None:
    """썸네일 이미지를 다운로드하여 base64 data URL로 변환 (Vision API용).

    보안:
    - 호스트 allowlist 확인 (_is_safe_figma_cdn)
    - 스트리밍 다운로드 + 2MB 초과 시 즉시 중단
    - Content-Length 사전 체크
    - 매직 바이트로 PNG 확인
    """
    if not url or not _is_safe_figma_cdn(url):
        return None
    max_size = 2 * 1024 * 1024  # 2MB
    try:
        with httpx.Client(timeout=FIGMA_REQUEST_TIMEOUT, follow_redirects=False) as client:
            with client.stream("GET", url) as resp:
                if resp.status_code != 200:
                    return None
                # Content-Length 사전 체크 (있으면)
                cl = resp.headers.get("content-length")
                if cl and cl.isdigit() and int(cl) > max_size:
                    return None
                # 스트리밍 다운로드 — 2MB 초과 시 즉시 중단
                chunks = []
                total = 0
                for chunk in resp.iter_bytes(chunk_size=64 * 1024):
                    total += len(chunk)
                    if total > max_size:
                        return None
                    chunks.append(chunk)
                content = b"".join(chunks)

        # PNG 매직 바이트 확인 (Figma가 format=png로 반환하므로)
        if not content.startswith(b"\x89PNG\r\n\x1a\n"):
            return None

        b64 = base64.b64encode(content).decode("utf-8")
        return f"data:image/png;base64,{b64}"
    except Exception:
        return None


def fetch_figma_file(figma_url: str, max_retries: int = 2) -> dict | None:
    """Figma URL에서 파일 구조와 썸네일을 가져옴 (재시도 지원).

    Returns:
        성공: {file_name, page_count, total_frames, ..., thumbnails: [...]}
        실패: {"error": "..."}
        URL 파싱 실패: None
    """
    file_key = parse_figma_url(figma_url)
    if not file_key:
        return None

    if not FIGMA_TOKEN:
        return {"error": "Figma API 토큰이 설정되지 않아 분석할 수 없습니다."}

    # 파일 정보: retriable 에러만 재시도
    summary = None
    result = {"error": "Figma API 호출 실패", "retriable": False}
    for attempt in range(max_retries):
        result = _fetch_file_once(file_key)
        if "error" not in result:
            summary = result
            break
        if not result.get("retriable", False):
            break  # 403/404 등은 재시도 무의미
        if attempt < max_retries - 1:
            print(f"[Figma] {file_key} fetch 재시도 ({attempt + 2}/{max_retries})")
            time.sleep(1)  # 짧은 backoff

    if summary is None:
        # retriable 플래그 제거 후 반환 (외부 호출자는 에러 메시지만 필요)
        return {"error": result.get("error", "Figma API 호출 실패")}

    summary["file_key"] = file_key

    # 썸네일 수집 (best-effort, 실패해도 요약은 반환)
    thumbnails = []
    top_ids = summary.get("top_frame_ids", [])[:FIGMA_MAX_THUMBNAILS]
    if top_ids:
        image_urls = _fetch_thumbnails_once(file_key, top_ids)
        for node_id, url in image_urls.items():
            data_url = _download_thumbnail_as_base64(url)
            if data_url:
                thumbnails.append({
                    "type": "image_url",
                    "image_url": {
                        "url": data_url,
                        "detail": "low",
                    },
                })

    summary["thumbnails_encoded"] = thumbnails
    return summary
