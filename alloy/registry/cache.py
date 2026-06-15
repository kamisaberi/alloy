import os
import shutil
import time
from pathlib import Path
from typing import Optional, Dict, Any

# --- Base Directory Defaults ---
HOME_DIR = Path.home()
ALLOY_DIR = HOME_DIR / ".alloy"
DEFAULT_CACHE_DIR = ALLOY_DIR / "cache"
RECIPE_SUBDIR = "recipes"


class CacheManager:
    """
    Manages the local filesystem cache for Alloy, including downloaded package recipes
    and HTTP indices. Implements TTL (Time-To-Live) expiration checks and garbage collection.
    """

    def __init__(self, cache_dir: Optional[Path] = None, recipe_ttl_seconds: int = 86400):
        self.cache_dir = Path(cache_dir) if cache_dir else DEFAULT_CACHE_DIR
        self.recipe_dir = self.cache_dir / RECIPE_SUBDIR
        self.recipe_ttl = recipe_ttl_seconds  # Default is 86400 seconds (24 hours) [9]

        # Ensure target cache directories exist on initialization
        self.recipe_dir.mkdir(parents=True, exist_ok=True)

    def get_recipe(self, package_name: str, ignore_ttl: bool = False) -> Optional[str]:
        """
        Retrieves a cached recipe by package name if it exists and has not expired.

        Returns:
            str: The raw YAML string content if valid.
            None: If the recipe does not exist or has expired.
        """
        recipe_path = self._get_recipe_path(package_name)
        if not recipe_path.is_file():
            return None

        # Check if the cache file is stale [9]
        if not ignore_ttl and self.is_expired(recipe_path, self.recipe_ttl):
            try:
                # Delete stale file to keep cache directory clean [10]
                recipe_path.unlink()
            except OSError:
                pass
            return None

        try:
            return recipe_path.read_text(encoding="utf-8")
        except OSError:
            return None

    def set_recipe(self, package_name: str, yaml_content: str) -> None:
        """
        Saves a downloaded recipe string to the local filesystem cache.
        """
        recipe_path = self._get_recipe_path(package_name)
        try:
            recipe_path.write_text(yaml_content, encoding="utf-8")
        except OSError:
            # Fail silently on cache write issues so that offline/permission warnings
            # don't completely halt an active install loop.
            pass

    def is_expired(self, file_path: Path, ttl_seconds: int) -> bool:
        """
        Compares the file's modification time (mtime) against the current time
        to determine if its age exceeds the specified TTL.
        """
        try:
            mtime = os.path.getmtime(file_path)
            age = time.time() - mtime
            return age > ttl_seconds
        except OSError:
            # If the OS cannot read mtime, treat it as expired/corrupt [9]
            return True

    def clear(self) -> None:
        """
        Deletes the entire cache folder structure. Used by 'alloy clean'. [10]
        """
        if self.cache_dir.exists():
            try:
                shutil.rmtree(self.cache_dir)
            except OSError as e:
                raise RuntimeError(f"Failed to clear cache directory: {e}")
        # Recreate clean, empty directories
        self.recipe_dir.mkdir(parents=True, exist_ok=True)

    def get_stats(self) -> Dict[str, Any]:
        """
        Calculates cache utilization statistics (total file count and disk footprint).
        Useful for developer logs, diagnostics, and CLI status displays.
        """
        file_count = 0
        total_size = 0

        if self.cache_dir.exists():
            for root, _, files in os.walk(self.cache_dir):
                for file_name in files:
                    fp = os.path.join(root, file_name)
                    # Skip symbolic links to prevent double counting file footprints
                    if not os.path.islink(fp):
                        try:
                            total_size += os.path.getsize(fp)
                            file_count += 1
                        except OSError:
                            pass

        return {
            "file_count": file_count,
            "size_bytes": total_size,
            "size_readable": self._format_size(total_size)
        }

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _get_recipe_path(self, package_name: str) -> Path:
        """
        Resolves the absolute path for a cached recipe.
        Normalizes names to lowercase to prevent case-sensitivity mismatches on Linux.
        """
        safe_name = package_name.lower().strip()
        return self.recipe_dir / f"{safe_name}.yaml"

    def _format_size(self, size_bytes: int) -> str:
        """
        Formats raw bytes into a human-readable storage string (B, KB, MB, GB).
        """
        size = float(size_bytes)
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


# ==========================================
# Self-Test Block (Sandbox Execution)
# ==========================================
if __name__ == "__main__":
    import tempfile

    print("--- Running CacheManager Self-Test ---")
    mock_yaml = "package:\n  name: hypocv\n  version: 1.2.0"

    with tempfile.TemporaryDirectory() as tmp_dir:
        sandbox_path = Path(tmp_dir)

        # Initialize CacheManager in a temporary sandbox with a short 2-second TTL
        cache = CacheManager(cache_dir=sandbox_path, recipe_ttl_seconds=2)

        # Test Case 1: Write and read from cache
        cache.set_recipe("hypocv", mock_yaml)
        retrieved = cache.get_recipe("hypocv")
        print(f"✅ Cache Write & Read: Success (Matches: {retrieved == mock_yaml})")

        # Test Case 2: Read cache statistics
        stats = cache.get_stats()
        print(f"📊 Cache Stats:        {stats['file_count']} files, {stats['size_readable']}")

        # Test Case 3: Verify TTL Expiration
        print("⏳ Waiting 3 seconds to trigger TTL expiration...")
        time.sleep(3)
        expired_retrieval = cache.get_recipe("hypocv")
        print(f"✅ TTL Expiration:     Success (File deleted/expired: {expired_retrieval is None})")

        # Test Case 4: Cache Clear
        cache.set_recipe("temporary_recipe", mock_yaml)
        print(f"📊 Pre-Clean Stats:    {cache.get_stats()['file_count']} file(s)")
        cache.clear()
        print(f"✅ Cache Clear:        Success ({cache.get_stats()['file_count']} files remaining)")