import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("SECRET_KEY", "test")
os.environ.setdefault("DATABASE_URL", "sqlite:///test.db")
os.environ.setdefault("FIGMA_TOKEN", "dummy-token")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "api"))

import services.figma_fetcher as figma_fetcher


class _FakeResponse:
    status_code = 403
    text = '{"status":403,"err":"Token expired"}'

    headers = {"content-type": "application/json; charset=utf-8"}

    def json(self):
        return {"status": 403, "err": "Token expired"}


class _FakeClient:
    def __init__(self, *args, **kwargs):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, *args, **kwargs):
        return _FakeResponse()


class FigmaFetcherTests(unittest.TestCase):
    def test_extract_figma_file_name_from_encoded_url(self):
        url = (
            "https://www.figma.com/design/dXK1GXZQbfsGMyNccMUF8V/"
            "LIKELION-PBL---%EC%A0%95%EC%97%B0%EC%88%98?node-id=0-1"
        )

        self.assertEqual(
            figma_fetcher.extract_figma_file_name_from_url(url),
            "LIKELION-PBL---정연수",
        )

    def test_token_expired_is_system_error_not_share_permission_error(self):
        with patch.object(figma_fetcher.httpx, "Client", _FakeClient):
            result = figma_fetcher.fetch_figma_file(
                "https://www.figma.com/design/dXK1GXZQbfsGMyNccMUF8V/example",
                max_retries=1,
            )

        self.assertTrue(result["system_error"])
        self.assertIn("토큰", result["error"])


if __name__ == "__main__":
    unittest.main()
