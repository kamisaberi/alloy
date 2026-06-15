import json
from pathlib import Path
from typing import List, Optional

# Core & Low-Level API imports
from alloy.core.parser import Recipe, parse_recipe_string, RecipeParseError
from alloy.registry.api_client import AlloyAPIClient, LOCAL_INDEX_PATH
from alloy.registry.exceptions import RegistryError, APIConnectionError
from alloy.registry.models import RegistryIndex, PackageSummary


class RegistryClient:
    """
    The high-level manager that orchestrates interaction between local index caches,
    low-level API HTTP networking, and the core recipe validation engine.
    """

    def __init__(self, api_client: Optional[AlloyAPIClient] = None):
        # Allow injecting an API client (useful for mock testing)
        self.api_client = api_client or AlloyAPIClient()

    def get_recipe(self, package_name: str, force_update: bool = False) -> Recipe:
        """
        Retrieves and parses a package's validated Recipe object.
        Checks local cache first unless force_update is True.

        Raises:
            RegistryError / APIConnectionError: On network failures.
            RecipeParseError: If the retrieved YAML is corrupt or invalid.
        """
        # Step 1: Fetch the raw YAML string (from local cache or remote API)
        raw_yaml = self.api_client.fetch_recipe(package_name, use_cache=not force_update)

        # Step 2: Pass the YAML content to the core parser for validation
        try:
            return parse_recipe_string(raw_yaml)
        except RecipeParseError as e:
            raise RecipeParseError(
                f"Failed to parse recipe for '{package_name}' after downloading:\n  {e}"
            )

    def search_local(self, query: str) -> List[PackageSummary]:
        """
        Performs a lightning-fast offline search of the package index on disk.
        Does not make any network calls.

        Raises:
            RegistryError: If the local database index has not been initialized.
        """
        if not LOCAL_INDEX_PATH.is_file():
            raise RegistryError(
                "Local package index is missing. "
                "Please run 'alloy update' to sync with the remote registry."
            )

        try:
            # Load and validate local index from disk
            content = LOCAL_INDEX_PATH.read_text(encoding="utf-8")
            index_data = RegistryIndex.model_validate_json(content)

            # Simple substring search over package names and descriptions
            matches = []
            query_lower = query.lower().strip()

            for package in index_data.packages:
                name_match = query_lower in package.name.lower()
                desc_match = package.description and query_lower in package.description.lower()

                if name_match or desc_match:
                    matches.append(package)

            return matches

        except Exception as e:
            raise RegistryError(f"Failed to read or parse local package database: {e}")

    def update_registry(self) -> int:
        """
        Pulls down the latest lightweight package index from the remote API.

        Returns:
            int: The total count of package recipes updated in the index.
        """
        try:
            index_data = self.api_client.update_local_index()
            return len(index_data.packages)
        except APIConnectionError as e:
            raise RegistryError(f"Could not connect to the remote server to update index: {e}")
        except Exception as e:
            raise RegistryError(f"Index sync failed: {e}")


# ==========================================
# Self-Test Integration Block
# ==========================================
if __name__ == "__main__":
    import tempfile
    import httpx

    print("--- Running Registry Client Integration Test ---")

    # Mock YAML recipe payload
    mock_recipe_yaml = """
    package:
      name: "hypocv"
      version: "1.2.0"
    """


    # Mock Router that mimics a successful GET for 'hypocv/recipe'
    def mock_router(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v1/packages/hypocv/recipe":
            return httpx.Response(200, text=mock_recipe_yaml)
        return httpx.Response(404)


    # Inject Mock HTTP Transport into low-level client
    mock_transport = httpx.MockTransport(mock_router)
    api_client = AlloyAPIClient(transport=mock_transport)

    # Initialize high-level RegistryClient
    registry = RegistryClient(api_client=api_client)

    # Use tempfile context to avoid polluting user's ~/.alloy directory during local execution
    with tempfile.TemporaryDirectory() as tmp_dir:
        import alloy.registry.api_client
        import alloy.registry.client

        # Override paths temporarily to point to sandbox
        sandbox_path = Path(tmp_dir)
        alloy.registry.api_client.ALLOY_DIR = sandbox_path
        alloy.registry.api_client.LOCAL_INDEX_PATH = sandbox_path / "local_index.json"
        alloy.registry.api_client.RECIPE_CACHE_DIR = sandbox_path / "cache" / "recipes"

        try:
            # Test Case 1: End-to-end Fetch & Parse (Network -> Local Cache -> Recipe Object)
            print("⏳ Attempting to fetch and compile 'hypocv'...")
            recipe = registry.get_recipe("hypocv")
            print("✅ End-to-end recipe compilation succeeded!")
            print(f"   Compiled Name:    {recipe.package.name}")
            print(f"   Compiled Version: {recipe.package.version}")

            # Verify it was successfully cached locally in the sandbox
            cached_file = alloy.registry.api_client.RECIPE_CACHE_DIR / "hypocv.yaml"
            print(f"   Verified Cached:  {cached_file.is_file()}")

        except Exception as e:
            print(f"❌ Test Failed with exception: {e}")