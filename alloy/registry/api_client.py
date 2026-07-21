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

# Default fallback to your GitHub Pages URL structure
DEFAULT_API_URL = "https://yourusername.github.io/alloy-registry/v1"


class AlloyAPIClient:
    """
    An HTTP client modified to fetch static files from a GitHub Pages registry.
    Handles client-side search logic and file-extension mappings.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 10.0,
                 transport: Optional[httpx.BaseTransport] = None):
        self.base_url = base_url or os.environ.get("ALLOY_API_URL", DEFAULT_API_URL)
        self.timeout = timeout
        self.client = httpx.Client(base_url=self.base_url, timeout=self.timeout, transport=transport)

    def fetch_recipe(self, package_name: str, use_cache: bool = True) -> str:
        """
        Retrieves the YAML recipe for a package.
        Checks local cache first. If missing, downloads from static host and caches it.
        """
        cache_path = RECIPE_CACHE_DIR / f"{package_name}.yaml"

        if use_cache and cache_path.is_file():
            return cache_path.read_text(encoding="utf-8")

        try:
            # 🛠️ STATIC ADJUSTMENT: Appends '/recipe.yaml' explicitly [15]
            response = self.client.get(f"/packages/{package_name}/recipe.yaml")
            self._handle_http_errors(response, package_name)
            yaml_content = response.text

            RECIPE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
            cache_path.write_text(yaml_content, encoding="utf-8")

            return yaml_content

        except httpx.RequestError as e:
            raise APIConnectionError(f"Network error while fetching recipe for '{package_name}': {e}")

    def fetch_package_details(self, package_name: str) -> PackageDetails:
        """
        Queries the static host for metadata on a specific package.
        """
        try:
            # 🛠️ STATIC ADJUSTMENT: Appends '.json' to target the static file [15]
            response = self.client.get(f"/packages/{package_name}.json")
            self._handle_http_errors(response, package_name)
            return PackageDetails.model_validate_json(response.text)

        except httpx.RequestError as e:
            raise APIConnectionError(f"Network error while fetching details for '{package_name}': {e}")
        except ValidationError as e:
            raise APIValidationError(f"Invalid JSON payload returned from registry server: {e}")

    def search_packages(self, query: str) -> SearchResponse:
        """
        Performs a search query.
        Since static hosts cannot process '?q=query' parameter routes, this automatically
        downloads the global index.json and processes the query on the client-side [14].
        """
        try:
            # 1. Download/sync the index [15]
            index_data = self.update_local_index()

            # 2. Filter matches locally in-memory [14]
            matches = []
            query_lower = query.lower().strip()
            for pkg in index_data.packages:
                name_match = query_lower in pkg.name.lower()
                desc_match = pkg.description and query_lower in pkg.description.lower()

                if name_match or desc_match:
                    matches.append(pkg)

            return SearchResponse(
                query=query,
                total_results=len(matches),
                results=matches
            )

        except Exception as e:
            raise RegistryError(f"Failed to perform client-side search: {e}")

    def update_local_index(self) -> RegistryIndex:
        """
        Fetches the lightweight index from the static server and updates local cache.
        """
        try:
            print("🔄 Syncing package index with GitHub Registry...")
            # 🛠️ STATIC ADJUSTMENT: Targets '/index.json' explicitly [15]
            response = self.client.get("/index.json")
            self._handle_http_errors(response)

            index_data = RegistryIndex.model_validate_json(response.text)

            ALLOY_DIR.mkdir(parents=True, exist_ok=True)
            LOCAL_INDEX_PATH.write_text(response.text, encoding="utf-8")

            return index_data

        except httpx.RequestError as e:
            raise APIConnectionError(f"Network error while updating package index: {e}")
        except ValidationError as e:
            raise APIValidationError(f"Invalid index payload returned from registry server: {e}")

    def _handle_http_errors(self, response: httpx.Response, package_name: Optional[str] = None) -> None:
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