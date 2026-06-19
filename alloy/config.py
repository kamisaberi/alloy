# alloy/config.py
from pathlib import Path
import os

# Get the user's home directory cross-platform
HOME_DIR = Path.home()

# Define the base Alloy directory (~/.alloy)
ALLOY_DIR = HOME_DIR / ".alloy"

# Define subdirectories
REGISTRY_DIR = ALLOY_DIR / "registry"
PACKAGES_DIR = REGISTRY_DIR / "packages"
CACHE_DIR = ALLOY_DIR / "cache"

# Define important files
INSTALLED_DB = ALLOY_DIR / "installed.json"
REGISTRY_INDEX = REGISTRY_DIR / "index.json"


def init_directories():
    """Run this when Alloy starts to ensure directories exist."""
    PACKAGES_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if not INSTALLED_DB.exists():
        with open(INSTALLED_DB, "w") as f:
            f.write("{}")  # Start with empty JSON object
