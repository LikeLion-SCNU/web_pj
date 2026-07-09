import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

import services.github_fetcher as github_fetcher


MISSION10_FILES = [
    "src/Mission10/README.md",
    "src/Mission10/build.gradle",
    "src/Mission10/settings.gradle",
    "src/Mission10/src/main/java/com/likelion/mission10/Mission10Application.java",
    "src/Mission10/src/main/java/com/likelion/mission10/controller/AssignmentController.java",
    "src/Mission10/src/main/java/com/likelion/mission10/controller/MemberController.java",
    "src/Mission10/src/main/java/com/likelion/mission10/controller/TeamController.java",
    "src/Mission10/src/main/java/com/likelion/mission10/domain/Assignment.java",
    "src/Mission10/src/main/java/com/likelion/mission10/domain/Member.java",
    "src/Mission10/src/main/java/com/likelion/mission10/domain/Team.java",
    "src/Mission10/src/main/java/com/likelion/mission10/dto/AssignmentCreateRequest.java",
    "src/Mission10/src/main/java/com/likelion/mission10/dto/AssignmentResponse.java",
    "src/Mission10/src/main/java/com/likelion/mission10/dto/AssignmentUpdateRequest.java",
    "src/Mission10/src/main/java/com/likelion/mission10/dto/MemberCreateRequest.java",
    "src/Mission10/src/main/java/com/likelion/mission10/dto/MemberResponse.java",
    "src/Mission10/src/main/java/com/likelion/mission10/dto/MemberUpdateRequest.java",
    "src/Mission10/src/main/java/com/likelion/mission10/dto/TeamCreateRequest.java",
    "src/Mission10/src/main/java/com/likelion/mission10/dto/TeamResponse.java",
    "src/Mission10/src/main/java/com/likelion/mission10/dto/TeamUpdateRequest.java",
    "src/Mission10/src/main/java/com/likelion/mission10/exception/AssignmentNotFoundException.java",
    "src/Mission10/src/main/java/com/likelion/mission10/exception/BusinessException.java",
    "src/Mission10/src/main/java/com/likelion/mission10/exception/ErrorResponse.java",
    "src/Mission10/src/main/java/com/likelion/mission10/exception/GlobalExceptionHandler.java",
    "src/Mission10/src/main/java/com/likelion/mission10/exception/MemberNotFoundException.java",
    "src/Mission10/src/main/java/com/likelion/mission10/exception/TeamNotFoundException.java",
    "src/Mission10/src/main/java/com/likelion/mission10/repository/AssignmentRepository.java",
    "src/Mission10/src/main/java/com/likelion/mission10/repository/MemberRepository.java",
    "src/Mission10/src/main/java/com/likelion/mission10/repository/TeamRepository.java",
    "src/Mission10/src/main/java/com/likelion/mission10/service/AssignmentService.java",
    "src/Mission10/src/main/java/com/likelion/mission10/service/MemberService.java",
    "src/Mission10/src/main/java/com/likelion/mission10/service/TeamService.java",
    "src/Mission10/src/main/resources/application.properties",
    "src/Mission10/src/main/resources/static/app.js",
    "src/Mission10/src/main/resources/static/index.html",
    "src/Mission10/src/main/resources/static/style.css",
    "README.md",
]


class GithubFetcherTests(unittest.TestCase):
    def test_backend_selection_keeps_mission10_exception_service_and_static_files(self):
        selected = github_fetcher.select_key_files(MISSION10_FILES, "backend")

        self.assertLessEqual(len(selected), 24)
        self.assertIn("src/Mission10/src/main/java/com/likelion/mission10/exception/GlobalExceptionHandler.java", selected)
        self.assertIn("src/Mission10/src/main/java/com/likelion/mission10/exception/ErrorResponse.java", selected)
        self.assertIn("src/Mission10/src/main/java/com/likelion/mission10/service/MemberService.java", selected)
        self.assertIn("src/Mission10/src/main/resources/static/app.js", selected)
        self.assertIn("src/Mission10/src/main/resources/static/index.html", selected)

    def test_fetch_repo_code_retries_tree_url_with_slash_branch(self):
        calls = []

        def fake_fetch(owner, repo, track, branch=None, subpath=""):
            calls.append((branch, subpath))
            if branch == "feat/design-mission-00" and subpath == "src/Mission10":
                return {"owner": owner, "repo": repo, "branch": branch, "subpath": subpath}
            return {"error": "not found"}

        with patch.object(github_fetcher, "_fetch_repo_code_once", side_effect=fake_fetch):
            result = github_fetcher.fetch_repo_code(
                "https://github.com/example/likelion-pbl/tree/feat/design-mission-00/src/Mission10",
                "backend",
                max_retries=1,
            )

        self.assertEqual(result["branch"], "feat/design-mission-00")
        self.assertEqual(result["subpath"], "src/Mission10")
        self.assertIn(("feat", "design-mission-00/src/Mission10"), calls)


if __name__ == "__main__":
    unittest.main()
