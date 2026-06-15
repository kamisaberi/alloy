import json
import tempfile
import unittest
from pathlib import Path
import httpx
from pydantic import ValidationError

# Adjust imports to match your project structure
from alloy.registry.api_client import AlloyAPIClient
from alloy.registry.exceptions import (
    APIConnectionError,
    APIServerError,
    APIValidationError,
    PackageNotFoundError,
    RateLimitExceededError,
    UnauthorizedError
)
from alloy.registry.models import PackageDetails, SearchResponse, RegistryIndex


# ==========================================
# 1. Mock HTTP Router Definition
# ==========================================

def mock_router(request: httpx.Request) -> httpx.Response:
    """
    Acts as our mock local API server, returning structured payloads or specific
    HTTP failure codes depending on the requested path.
    """
    path = request.url.path

    if path == "/v1/packages/hypocv/recipe":
        return httpx.Response(200, text="package:\n  name: hypocv\n  version: 1.2.0")

    elif path == "/v1/packages/hypocv":
        details_payload = {
            "name": "hypocv",
            "latest_version": "1.2.0",
            "versions": ["1.1.0", "1.2.0"],
            "description": "Mocked computer vision bindings.",
            "author": "Alloy Core Team",
            "homepage": "https://github.com/alloy-pm/hypocv"
        }
        return httpx.Response(200, json=details_payload)

    elif path == "/v1/packages/corrupt-payload":
        # Missing required name and version parameters
        return httpx.Response(200, json={"description": "Missing vital keys"})

    elif path == "/v1/search":
        search_payload = {
            "query": "cv",
            "total_results": 1,
            "results": [{"name": "hypocv", "version": "1.2.0", "description": "Mocked computer vision bindings."}]
        }
        return httpx.Response(200, json=search_payload)

    elif path == "/v1/index":
        index_payload = {
            "last_updated": "2026-06-16T00:00:00Z",
            "packages": [{"name": "hypocv", "version": "1.2.0", "description": "Mocked computer vision bindings."}]
        }
        return httpx.Response(200, json=index_payload)

    # Mock specific HTTP error cases [8]
    elif path == "/v1/packages/missing-package/recipe" or path == "/v1/packages/missing-package":
        return httpx.Response(404)
    elif path == "/v1/packages/rate-limited":
        return httpx.Response(429)
    elif path == "/v1/packages/unauthorized":
        return httpx.Response(401)
    elif path == "/v1/packages/broken-server":
        return httpx.Response(500)

    return httpx.Response(404)


# ==========================================
# 2. API Client Unit Tests
# ==========================================

class TestAlloyAPIClient(unittest.TestCase):

    def setUp(self):
        """
        Redirects filesystem writes to an isolated temporary sandbox
        and configures the HTTPX Client with a MockTransport router [8].
        """
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.sandbox_path = Path(self.tmp_dir.name)

        # Override module-level paths in the target api_client to isolate cache writes [2]
        import alloy.registry.api_client
        self.orig_alloy_dir = alloy.registry.api_client.ALLOY_DIR
        self.orig_cache_dir = alloy.registry.api_client.RECIPE_CACHE_DIR
        self.orig_index_path = alloy.registry.api_client.LOCAL_INDEX_PATH

        alloy.registry.api_client.ALLOY_DIR = self.sandbox_path
        alloy.registry.api_client.RECIPE_CACHE_DIR = self.sandbox_path / "cache" / "recipes"
        alloy.registry.api_client.LOCAL_INDEX_PATH = self.sandbox_path / "local_index.json"

        # Instantiate the client injected with the Mock Transport
        self.mock_transport = httpx.MockTransport(mock_router)
        self.client = AlloyAPIClient(transport=self.mock_transport)

    def tearDown(self):
        """Restores original module-level paths and clears temp files."""
        import alloy.registry.api_client
        alloy.registry.api_client.ALLOY_DIR = self.orig_alloy_dir
        alloy.registry.api_client.RECIPE_CACHE_DIR = self.orig_cache_dir
        alloy.registry.api_client.LOCAL_INDEX_PATH = self.orig_index_path

        self.tmp_dir.cleanup()

    def test_fetch_recipe_downloads_and_caches_to_disk(self):
        """Verifies fetch_recipe hits the API, downloads the recipe, caches it, and reuses it on repeat calls."""
        import alloy.registry.api_client
        cache_file = alloy.registry.api_client.RECIPE_CACHE_DIR / "hypocv.yaml"
        self.assertFalse(cache_file.is_file())

        # 1. Trigger fresh download via the mock server [8]
        recipe_yaml = self.client.fetch_recipe("hypocv")
        self.assertIn("package:\n  name: hypocv", recipe_yaml)

        # Verify it has saved the file locally inside the sandbox [2]
        self.assertTrue(cache_file.is_file())
        self.assertEqual(cache_file.read_text(encoding="utf-8"), recipe_yaml)

        # 2. Force transport disconnect. A second call should read directly from disk cache [3]
        self.client.client.transport = None
        cached_yaml = self.client.fetch_recipe("hypocv")
        self.assertEqual(cached_yaml, recipe_yaml)

    def test_fetch_package_details_parses_json_schema_correctly(self):
        """Verifies that package details are correctly parsed into the PackageDetails schema."""
        details = self.client.fetch_package_details("hypocv")

        self.assertEqual(details.name, "hypocv")
        self.assertEqual(details.latest_version, "1.2.0")
        self.assertEqual(details.author, "Alloy Core Team")
        self.assertEqual(details.homepage, "https://github.com/alloy-pm/hypocv")

    def test_fetch_package_details_throws_validation_error_on_corrupt_payload(self):
        """Verifies that structurally invalid server JSON structures trigger an APIValidationError."""
        with self.assertRaises(APIValidationError):
            self.client.fetch_package_details("corrupt-payload")

    def test_search_packages_parses_search_results(self):
        """Verifies search queries fetch and parse SearchResponse datasets."""
        results = self.client.search_packages("cv")

        self.assertEqual(results.query, "cv")
        self.assertEqual(results.total_results, 1)
        self.assertEqual(results.results[0].name, "hypocv")

    def test_update_local_index_writes_index_file_locally(self):
        """Verifies update_local_index fetches index data and successfully writes 'local_index.json' to disk."""
        import alloy.registry.api_client
        self.assertFalse(alloy.registry.api_client.LOCAL_INDEX_PATH.is_file())

        index_data = self.client.update_local_index()
        self.assertEqual(len(index_data.packages), 1)
        self.assertEqual(index_data.packages[0].name, "hypocv")

        # Assert file was created on disk
        self.assertTrue(alloy.registry.api_client.LOCAL_INDEX_PATH.is_file())

    def test_http_error_mappings_raise_proper_custom_exceptions(self):
        """Verifies that raw HTTP status failure codes are correctly translated to named exceptions."""
        # 1. HTTP 404 -> PackageNotFoundError
        with self.assertRaises(PackageNotFoundError):
            self.client.fetch_recipe("missing-package")

        # 2. HTTP 429 -> RateLimitExceededError
        with self.assertRaises(RateLimitExceededError):
            self.client.fetch_package_details("rate-limited")

        # 3. HTTP 401 -> UnauthorizedError
        with self.assertRaises(UnauthorizedError):
            self.client.fetch_package_details("unauthorized")

        # 4. HTTP 500 -> APIServerError
        with self.assertRaises(APIServerError):
            self.client.fetch_package_details("broken-server")

    def test_connection_failure_maps_to_api_connection_error(self):
        """Verifies that standard network-level timeouts or DNS errors map directly to APIConnectionError."""

        def broken_network_router(req: httpx.Request):
            raise httpx.ConnectTimeout("Connection timed out")

        # Instantiate a client injected with a failing transport
        broken_client = AlloyAPIClient(transport=httpx.MockTransport(broken_network_router))

        with self.assertRaises(APIConnectionError):
            broken_client.fetch_recipe("hypocv")


if __name__ == "__main__":
    unittest.main()