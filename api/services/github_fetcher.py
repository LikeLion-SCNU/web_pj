"""GitHub 레포지토리에서 코드를 가져오는 서비스"""
import re
from urllib.parse import urlparse

import httpx

from config import GITHUB_TOKEN

_VALID_GITHUB_NAME = re.compile(r"^[a-zA-Z0-9._-]+$")

# 트랙별 관심 파일 패턴
TRACK_FILE_PATTERNS = {
    "frontend": {
        "extensions": {".html", ".css", ".js", ".jsx", ".ts", ".tsx", ".json"},
        "exclude": {"node_modules", ".next", "dist", "build", "package-lock.json", ".git"},
        "priority": ["index.html", "App.jsx", "App.tsx", "App.js", "style.css", "index.js", "index.tsx",
                     "package.json", "tsconfig.json", "README.md"],
        "max_files": 10,
        "max_file_size": 5000,  # chars
    },
    "backend": {
        "extensions": {".java", ".xml", ".properties", ".yml", ".yaml", ".gradle"},
        "exclude": {".gradle", "build", "target", ".idea", ".git", "gradlew", "gradlew.bat"},
        "priority": ["Main.java", "Application.java", "build.gradle", "pom.xml",
                     "application.properties", "application.yml", "README.md"],
        "max_files": 10,
        "max_file_size": 5000,
    },
    "design": {
        "extensions": {".md", ".txt", ".json"},
        "exclude": {".git"},
        "priority": ["README.md"],
        "max_files": 3,
        "max_file_size": 3000,
    },
    "planning": {
        "extensions": {".md", ".txt", ".json"},
        "exclude": {".git"},
        "priority": ["README.md"],
        "max_files": 3,
        "max_file_size": 3000,
    },
}


def parse_github_url(url: str) -> tuple[str, str] | None:
    """GitHub URL에서 owner/repo를 추출 (SSRF 방어 포함)"""
    if not url:
        return None
    try:
        parsed = urlparse(url.strip())
        if parsed.hostname != "github.com":
            return None
        parts = parsed.path.strip("/").split("/")
        if len(parts) < 2:
            return None
        owner, repo = parts[0], parts[1].split("?")[0].split("#")[0]
        if not _VALID_GITHUB_NAME.match(owner) or not _VALID_GITHUB_NAME.match(repo):
            return None
        return owner, repo
    except Exception:
        return None


def _get_headers():
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def fetch_repo_tree(owner: str, repo: str) -> list[str] | None:
    """레포지토리 파일 트리를 가져옴 (동기)"""
    headers = _get_headers()
    with httpx.Client(timeout=10) as client:
        for branch in ["main", "master"]:
            try:
                resp = client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
                    headers=headers,
                )
                if resp.status_code == 200:
                    tree = resp.json().get("tree", [])
                    return [item["path"] for item in tree if item["type"] == "blob"]
            except Exception:
                continue
    return None


def fetch_file_content(owner: str, repo: str, path: str, max_chars: int = 5000) -> str | None:
    """특정 파일 내용을 가져옴 (동기)"""
    headers = _get_headers()
    headers["Accept"] = "application/vnd.github.v3.raw"
    with httpx.Client(timeout=10) as client:
        try:
            resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                headers=headers,
            )
            if resp.status_code == 200:
                text = resp.text
                if len(text) > max_chars:
                    return text[:max_chars] + f"\n... (truncated, {len(text)} chars total)"
                return text
        except Exception:
            pass
    return None


def select_key_files(file_paths: list[str], track: str) -> list[str]:
    """트랙에 맞는 핵심 파일을 선별"""
    config = TRACK_FILE_PATTERNS.get(track, TRACK_FILE_PATTERNS["frontend"])
    extensions = config["extensions"]
    exclude = config["exclude"]
    priority_names = config["priority"]
    max_files = config["max_files"]

    # 제외 경로 필터링
    filtered = []
    for p in file_paths:
        skip = False
        for ex in exclude:
            if ex in p.split("/"):
                skip = True
                break
        if not skip:
            ext = "." + p.rsplit(".", 1)[-1] if "." in p else ""
            if ext in extensions or p.split("/")[-1] in priority_names:
                filtered.append(p)

    # 우선순위 파일 먼저
    priority = []
    others = []
    for p in filtered:
        filename = p.split("/")[-1]
        if filename in priority_names:
            priority.append(p)
        else:
            others.append(p)

    return (priority + others)[:max_files]


def fetch_repo_code(github_url: str, track: str) -> dict | None:
    """GitHub URL에서 트랙에 맞는 핵심 코드를 가져옴"""
    parsed = parse_github_url(github_url)
    if not parsed:
        return None

    owner, repo = parsed
    tree = fetch_repo_tree(owner, repo)
    if not tree:
        return {"error": f"레포지토리를 가져올 수 없습니다: {owner}/{repo}"}

    config = TRACK_FILE_PATTERNS.get(track, TRACK_FILE_PATTERNS["frontend"])
    key_files = select_key_files(tree, track)

    files = {}
    for path in key_files:
        content = fetch_file_content(owner, repo, path, max_chars=config["max_file_size"])
        if content:
            files[path] = content

    return {
        "owner": owner,
        "repo": repo,
        "total_files": len(tree),
        "file_tree": tree[:50],  # 전체 트리 (최대 50개)
        "code_files": files,
    }
