import json
import os
from pathlib import Path
from typing import Optional
import httpx
from pydantic import ValidationError

# Adjust imports to match your project structure
from alloy.registry.exceptions import (
    RegistryError,
    PackageNotFoundError,
    RateLimitExceededError,
    UnauthorizedError,
    APIServerError,
    APIConnectionError,
    APIValidationError
)
from alloy.registry.models import PackageDetails, SearchResponse, RegistryIndex, PackageSummary

# --- Path Configurations ---
HOME_DIR = Path.home()
ALLOY_DIR = HOME_DIR / ".alloy"
CACHE_DIR = ALLOY_DIR / "cache"
RECIPE_CACHE_DIR = CACHE_DIR / "recipes"
LOCAL_INDEX_PATH = ALLOY_DIR / "local_index.json"

DEFAULT_API_URL = "https://api.alloy.pm/v1"


class AlloyAPIClient:
    """
    An HTTP client for communicating with the remote Alloy Registry API.
    Handles data validation, error translation, and local caching.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0,
                 transport: Optional[httpx.BaseTransport] = None):
        # Allow overriding the API endpoint via environment variables or parameters
        self.base_url = base_url or os.environ.get("ALLOY_API_URL", DEFAULT_API_URL)
        self.timeout = timeout

        # Initialize the HTTPX client. Optionally accepts a mock transport for testing.
        self.client = httpx.Client(base_url=self.base_url, timeout=self.timeout, transport=transport)

    def fetch_recipe(self, package_name: str, use_cache: bool = True) -> str:
        """
        Retrieves the YAML recipe for a package.
        Checks local cache first. If missing, downloads from API and caches it.

        Raises:
            APIConnectionError: If network connection fails.
            RegistryError: On generic API errors.
        """
        cache_path = RECIPE_CACHE_DIR / f"{package_name}.yaml"

        # Step 1: Return from local cache if available and requested
        if use_cache and cache_path.is_file():
            return cache_path.read_text(encoding="utf-8")

        # Step 2: Fetch from remote registry
        try:
            response = self.client.get(f"/packages/{package_name}/recipe")
            self._handle_http_errors(response, package_name)
            yaml_content = response.text

            # Step 3: Cache the fetched recipe locally
            RECIPE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(yaml_content, encoding="utf-8")

            return yaml_content

        except httpx.RequestError as e:
            raise APIConnectionError(f"Network error while fetching recipe for '{package_name}': {e}")

    def fetch_package_details(self, package_name: str) -> PackageDetails:
        """
        Queries the API for detailed metadata on a specific package.
        """
        try:
            response = self.client.get(f"/packages/{package_name}")
            self._handle_http_errors(response, package_name)
            return PackageDetails.model_validate_json(response.text)

        except httpx.RequestError as e:
            raise APIConnectionError(f"Network error while fetching details for '{package_name}': {e}")
        except ValidationError as e:
            raise APIValidationError(f"Invalid JSON payload returned from registry server: {e}")

    def search_packages(self, query: str) -> SearchResponse:
        """
        Queries the API search endpoint to find matching packages.
        """
        try:
            response = self.client.get("/search", params={"q": query})
            self._handle_http_errors(response)
            return SearchResponse.model_validate_json(response.text)

        except httpx.RequestError as e:
            raise APIConnectionError(f"Network error during search for '{query}': {e}")
        except ValidationError as e:
            raise APIValidationError(f"Invalid JSON search results returned from registry server: {e}")

    def update_local_index(self) -> RegistryIndex:
        """
        Fetches the lightweight index from the API and updates the local
        ~/.alloy/local_index.json index cache for fast offline searches.
        """
        try:
            print("🔄 Syncing package index with remote registry...")
            response = self.client.get("/index")
            self._handle_http_errors(response)

            # Validate index schema structure
            index_data = RegistryIndex.model_validate_json(response.text)

            # Write index locally to disk
            ALLOY_DIR.mkdir(parents=True, exist_ok=True)
            LOCAL_INDEX_PATH.write_text(response.text, encoding="utf-8")

            return index_data

        except httpx.RequestError as e:
            raise APIConnectionError(f"Network error while updating package index: {e}")
        except ValidationError as e:
            raise APIValidationError(f"Invalid index payload returned from registry server: {e}")

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _handle_http_errors(self, response: httpx.Response, package_name: Optional[str] = None) -> None:
        """
        Intercepts unsuccessful HTTP responses and raises corresponding,
        named exceptions matching our custom exceptions.
        """
        if response.status_code == 200:
            return

        status = response.status_code
        if status == 404:
            raise PackageNotFoundError(package_name or "requested resource")
        elif status == 429:
            raise RateLimitExceededError()
        elif status in (401, 403):
            raise UnauthorizedError()
        elif status >= 500:
            raise APIServerError(status_code=status)
        else:
            raise RegistryError(
                f"Unexpected registry error. Server returned HTTP {status}",
                status_code=status
            )


# ==========================================
# Self-Test Block (Mock Transport)
# ==========================================
if __name__ == "__main__":
    print("--- Running API Client Mock Transport Test ---")


    # Define a mock transport that mimics a success JSON response for 'hypocv' details
    def mock_router(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/packages/hypocv":
            mock_payload = {
                "name": "hypocv",
                "latest_version": "1.2.0",
                "versions": ["1.1.0", "1.2.0"],
                "description": "Mocked visual descriptors.",
                "author": "Alloy Core Devs",
                "homepage": "https://github.com/alloy-pm/hypocv"
            }
            return httpx.Response(200, json=mock_payload)
        elif request.url.path == "/v1/packages/missing-package":
            return httpx.Response(404)
        return httpx.Response(500)


    # Initialize client injected with Mock transport
    mock_transport = httpx.MockTransport(mock_router)
    client = AlloyAPIClient(transport=mock_transport)

    try:
        # Test Case 1: Fetching valid package details (Success / Parsing)
        details = client.fetch_package_details("hypocv")
        print("✅ Mock API details parsed and validated successfully!")
        print(f"   Name: {details.name} (Latest: {details.latest_version})")

        # Test Case 2: Fetching nonexistent package (Error Translation)
        print("⏳ Testing expected failure for missing package...")
        client.fetch_package_details("missing-package")
        print("❌ Test Failed (Should have raised a PackageNotFoundError)")

    except PackageNotFoundError as e:
        print(f"✅ Successfully caught and mapped 404 to PackageNotFoundError:\n   -> {e}")
    except Exception as e:
        print(f"❌ Test Failed with unexpected exception: {e}")