"""GitHub 레포지토리에서 코드를 가져오는 서비스"""
import re
import time
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


def parse_github_url(url: str) -> tuple[str, str, str | None] | None:
    """GitHub URL에서 (owner, repo, branch) 추출 (SSRF 방어 포함).

    지원 형식:
      - https://github.com/{owner}/{repo}
      - https://github.com/{owner}/{repo}.git
      - https://github.com/{owner}/{repo}/tree/{branch}
      - https://github.com/{owner}/{repo}/tree/{branch}/...path
    branch가 명시되지 않으면 None 반환 — 호출자가 main/master를 시도.
    """
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
        branch = None
        # /tree/{branch} 또는 /tree/{branch}/path 형식 인식
        if len(parts) >= 4 and parts[2] == "tree":
            branch_candidate = parts[3].split("?")[0].split("#")[0]
            # 브랜치 이름 검증 — slash 허용(feature/x), 그러나 일단 단순 패턴만
            if _VALID_GITHUB_NAME.match(branch_candidate):
                branch = branch_candidate
        return owner, repo, branch
    except Exception:
        return None


def _get_headers():
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    return headers


def fetch_repo_tree(owner: str, repo: str, branch: str | None = None) -> tuple[list[str] | None, str | None]:
    """레포지토리 파일 트리를 가져옴 (동기). 성공 시 사용한 브랜치도 함께 반환.

    branch가 지정되면 그 브랜치만 시도. 없으면 main → master 순서로 시도.
    """
    headers = _get_headers()
    candidates = [branch] if branch else ["main", "master"]
    with httpx.Client(timeout=10) as client:
        for b in candidates:
            try:
                resp = client.get(
                    f"https://api.github.com/repos/{owner}/{repo}/git/trees/{b}?recursive=1",
                    headers=headers,
                )
                if resp.status_code == 200:
                    tree = resp.json().get("tree", [])
                    return [item["path"] for item in tree if item["type"] == "blob"], b
            except Exception:
                continue
    return None, None


def fetch_file_content(owner: str, repo: str, path: str, max_chars: int = 5000, branch: str | None = None) -> str | None:
    """특정 파일 내용을 가져옴 (동기). branch가 지정되면 해당 브랜치의 파일을 가져옴."""
    headers = _get_headers()
    headers["Accept"] = "application/vnd.github.v3.raw"
    params = {"ref": branch} if branch else None
    with httpx.Client(timeout=10) as client:
        try:
            resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
                headers=headers,
                params=params,
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


def fetch_repo_metadata(owner: str, repo: str) -> dict:
    """레포지토리의 커밋 수, 브랜치 목록, PR 목록을 가져옴"""
    headers = _get_headers()
    metadata = {"total_commits": 0, "branches": [], "pull_requests": []}

    with httpx.Client(timeout=10) as client:
        # 커밋 수 (모든 브랜치 포함, 최근 100개까지)
        try:
            resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/commits?per_page=100",
                headers=headers,
            )
            if resp.status_code == 200:
                commits = resp.json()
                metadata["total_commits"] = len(commits)
                metadata["recent_commits"] = [
                    {"message": c["commit"]["message"][:100], "date": c["commit"]["committer"]["date"]}
                    for c in commits[:10]
                ]
        except Exception:
            pass

        # 브랜치 목록
        try:
            resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/branches?per_page=30",
                headers=headers,
            )
            if resp.status_code == 200:
                metadata["branches"] = [b["name"] for b in resp.json()]
        except Exception:
            pass

        # PR 목록 (open + closed)
        try:
            resp = client.get(
                f"https://api.github.com/repos/{owner}/{repo}/pulls?state=all&per_page=10",
                headers=headers,
            )
            if resp.status_code == 200:
                metadata["pull_requests"] = [
                    {"title": pr["title"], "state": pr["state"],
                     "head": pr["head"]["ref"], "base": pr["base"]["ref"]}
                    for pr in resp.json()
                ]
        except Exception:
            pass

    return metadata


def _fetch_repo_code_once(owner: str, repo: str, track: str, branch: str | None = None) -> dict:
    """GitHub에서 코드를 한 번 시도하여 가져옴.

    branch가 명시되면 그 브랜치만, 없으면 main → master 순서로 fetch.
    학생이 /tree/{branch} URL을 제출하면 해당 브랜치의 코드가 평가 대상이 된다.
    """
    tree, used_branch = fetch_repo_tree(owner, repo, branch=branch)
    if not tree:
        suffix = f" (브랜치: {branch})" if branch else ""
        return {"error": f"레포지토리를 가져올 수 없습니다: {owner}/{repo}{suffix}"}

    config = TRACK_FILE_PATTERNS.get(track, TRACK_FILE_PATTERNS["frontend"])
    key_files = select_key_files(tree, track)

    files = {}
    for path in key_files:
        content = fetch_file_content(owner, repo, path, max_chars=config["max_file_size"], branch=used_branch)
        if content:
            files[path] = content

    # 커밋, 브랜치, PR 메타데이터 가져오기
    metadata = fetch_repo_metadata(owner, repo)

    return {
        "owner": owner,
        "repo": repo,
        "branch": used_branch,
        "total_files": len(tree),
        "file_tree": tree[:50],
        "code_files": files,
        "total_commits": metadata["total_commits"],
        "recent_commits": metadata.get("recent_commits", []),
        "branches": metadata["branches"],
        "pull_requests": metadata["pull_requests"],
    }


def fetch_repo_code(github_url: str, track: str, max_retries: int = 2) -> dict | None:
    """GitHub URL에서 트랙에 맞는 핵심 코드를 가져옴 (실패 시 재시도).

    URL이 /tree/{branch} 형식이면 해당 브랜치를 평가 대상으로 사용.
    """
    parsed = parse_github_url(github_url)
    if not parsed:
        return None

    owner, repo, branch = parsed

    # .git 접미사 제거
    if repo.endswith(".git"):
        repo = repo[:-4]

    last_result = None
    for attempt in range(max_retries):
        result = _fetch_repo_code_once(owner, repo, track, branch=branch)
        if "error" not in result:
            return result
        last_result = result
        if attempt < max_retries - 1:
            time.sleep(2)
            print(f"[GitHub] {owner}/{repo} fetch 재시도 ({attempt + 2}/{max_retries})")

    return last_result
