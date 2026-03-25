import httpx

from config import GITHUB_TOKEN


def parse_github_url(url: str) -> tuple[str, str] | None:
    """GitHub URL에서 owner/repo를 추출"""
    url = url.rstrip("/")
    if "github.com/" not in url:
        return None
    parts = url.split("github.com/")[1].split("/")
    if len(parts) < 2:
        return None
    return parts[0], parts[1]


async def fetch_repo_tree(owner: str, repo: str) -> list[str] | None:
    """레포지토리 파일 트리를 가져옴"""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/git/trees/main?recursive=1",
            headers=headers,
        )
        if resp.status_code != 200:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/git/trees/master?recursive=1",
                headers=headers,
            )
        if resp.status_code != 200:
            return None

        tree = resp.json().get("tree", [])
        return [item["path"] for item in tree if item["type"] == "blob"]


async def fetch_file_content(owner: str, repo: str, path: str) -> str | None:
    """특정 파일 내용을 가져옴"""
    headers = {"Accept": "application/vnd.github.v3.raw"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"

    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.github.com/repos/{owner}/{repo}/contents/{path}",
            headers=headers,
        )
        if resp.status_code == 200:
            return resp.text
    return None
