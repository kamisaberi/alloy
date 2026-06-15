import os
import yaml
from pathlib import Path
from typing import Optional, Dict, Any

# Subsystem Component Imports
from alloy.registry.api_client import AlloyAPIClient, ALLOY_DIR, DEFAULT_API_URL
from alloy.registry.cache import CacheManager, DEFAULT_CACHE_DIR
from alloy.registry.client import RegistryClient

# --- Global Config Path ---
CONFIG_FILE = ALLOY_DIR / "config.yaml"


class AlloyRegistryManager:
    """
    A unified manager that reads the global config.yaml, bootstraps
    CacheManager, AlloyAPIClient, and RegistryClient with the correct settings,
    and exposes them under a single, easily accessible interface.
    """

    def __init__(self, config_path: Optional[Path] = None):
        self.config_path = config_path or CONFIG_FILE
        self.config = self._load_config()

        # Bootstrap 1: Extract cache settings & instantiate CacheManager
        cache_dir_str = self.config.get("cache_dir")
        cache_dir = Path(cache_dir_str).expanduser() if cache_dir_str else DEFAULT_CACHE_DIR
        ttl_seconds = int(self.config.get("recipe_ttl_seconds", 86400))  # Default: 24 hours

        self.cache = CacheManager(cache_dir=cache_dir, recipe_ttl_seconds=ttl_seconds)

        # Bootstrap 2: Extract API settings & instantiate AlloyAPIClient
        api_url = self.config.get("api_url") or os.environ.get("ALLOY_API_URL", DEFAULT_API_URL)
        timeout = float(self.config.get("timeout", 10.0))

        self.api_client = AlloyAPIClient(base_url=api_url, timeout=timeout)

        # Bootstrap 3: Wrap API client in the high-level RegistryClient
        self.registry = RegistryClient(api_client=self.api_client)

    def get_config_value(self, key: str, default: Any = None) -> Any:
        """Retrieves a specific configuration setting from the parsed config.yaml."""
        return self.config.get(key, default)

    def write_default_config(self) -> None:
        """
        Scaffolds a standard default config.yaml file if one does not exist.
        Useful on the first execution of Alloy.
        """
        if self.config_path.is_file():
            return

        default_settings = {
            "api_url": DEFAULT_API_URL,
            "timeout": 10.0,
            "recipe_ttl_seconds": 86400,
            "cache_dir": str(DEFAULT_CACHE_DIR)
        }

        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(default_settings, f, default_flow_style=False)
            self.config = default_settings
        except OSError:
            # Silently pass if permission constraints prevent writing local configs
            pass

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _load_config(self) -> Dict[str, Any]:
        """
        Safely attempts to read and parse the local config.yaml file.
        Returns an empty dictionary on parse failures or missing files.
        """
        if not self.config_path.is_file():
            return {}

        try:
            content = self.config_path.read_text(encoding="utf-8")
            parsed = yaml.safe_load(content)
            return parsed if isinstance(parsed, dict) else {}
        except (yaml.YAMLError, OSError):
            # Gracefully fall back to standard defaults if the YAML file is corrupt
            return {}


# ==========================================
# Self-Test Block (Sandbox Bootstrapping)
# ==========================================
if __name__ == "__main__":
    import tempfile

    print("--- Running AlloyRegistryManager Bootstrapping Test ---")

    # Set up a mock config file in a temporary sandbox directory
    mock_settings = {
        "api_url": "https://custom-enterprise-registry.internal/v1",
        "timeout": 15.0,
        "recipe_ttl_seconds": 3600,  # Custom 1-hour cache expiration
        "cache_dir": "~/custom_alloy_cache"
    }

    with tempfile.TemporaryDirectory() as tmp_dir:
        sandbox_path = Path(tmp_dir)
        sandbox_config = sandbox_path / "config.yaml"

        # 1. Write the custom configuration to the sandbox
        with open(sandbox_config, "w", encoding="utf-8") as f:
            yaml.safe_dump(mock_settings, f)

        # 2. Instantiate the manager pointing to the sandbox configuration
        manager = AlloyRegistryManager(config_path=sandbox_config)

        # 3. Assert that all component parameters correctly inherited the config overrides
        print("✅ Verifying configuration inheritance...")

        # Verify API Base URL
        print(
            f"   API Endpoint:    {manager.api_client.base_url} (Matches custom: {manager.api_client.base_url == mock_settings['api_url']})")

        # Verify HTTP Timeout
        print(
            f"   HTTP Timeout:    {manager.api_client.client.timeout.read}s (Matches custom: {manager.api_client.client.timeout.read == mock_settings['timeout']})")

        # Verify Cache Expiration TTL
        print(
            f"   Recipe TTL:      {manager.cache.recipe_ttl}s (Matches custom: {manager.cache.recipe_ttl == mock_settings['recipe_ttl_seconds']})")

        # Verify Custom Cache Path expansion
        expected_cache_path = Path(mock_settings["cache_dir"]).expanduser()
        print(
            f"   Resolved Cache:  {manager.cache.cache_dir} (Matches custom: {manager.cache.cache_dir == expected_cache_path})")

        # 4. Verify default config writing
        new_config_path = sandbox_path / "defaults_config.yaml"
        test_manager = AlloyRegistryManager(config_path=new_config_path)
        test_manager.write_default_config()
        print(f"   Written Defaults: {new_config_path.is_file()}")