import os
import shutil
import subprocess
from pathlib import Path
from typing import List
from alloy.managers.base import BasePackageManager, PackageManagerError


class BrewPackageManager(BasePackageManager):
    """
    Implementation of the macOS Homebrew native package manager.
    """

    def __init__(self):
        # Dynamically discover the absolute path to brew
        self._brew_path = self._discover_brew()

    @property
    def name(self) -> str:
        return "brew"

    @property
    def executable(self) -> str:
        # Use discovered absolute path if available, fallback to default name
        return self._brew_path

    def is_available(self) -> bool:
        """
        Verifies if Homebrew is available locally.
        Uses absolute path discovery rather than relying strictly on the host's PATH.
        """
        return Path(self._brew_path).exists() or shutil.which("brew") is not None

    def update_database(self) -> None:
        """
        Updates the Homebrew repository index.
        """
        print("⏳ Running brew update...")
        # Homebrew explicitly forbids 'sudo' usage
        self._execute([self._brew_path, "update"], use_sudo=False)

    def install(self, packages: List[str]) -> None:
        """
        Installs a list of Homebrew formulas non-interactively.
        """
        if not packages:
            return

        print(f"⏳ Running brew install {' '.join(packages)}...")
        # We set HOMEBREW_NO_AUTO_UPDATE=1 to make installs faster if update was just run
        old_val = os.environ.get("HOMEBREW_NO_AUTO_UPDATE")
        os.environ["HOMEBREW_NO_AUTO_UPDATE"] = "1"

        try:
            self._execute([self._brew_path, "install"] + packages, use_sudo=False)
        finally:
            if old_val is not None:
                os.environ["HOMEBREW_NO_AUTO_UPDATE"] = old_val
            else:
                os.environ.pop("HOMEBREW_NO_AUTO_UPDATE", None)

    def uninstall(self, packages: List[str]) -> None:
        """
        Uninstalls a list of Homebrew formulas.
        """
        if not packages:
            return

        print(f"⏳ Running brew uninstall {' '.join(packages)}...")
        self._execute([self._brew_path, "uninstall"] + packages, use_sudo=False)

    def is_installed(self, package: str) -> bool:
        """
        Queries Homebrew locally to verify if a formula is already installed.
        """
        try:
            # Querying the formula specifically avoids standard cask interference
            result = subprocess.run(
                [self._brew_path, "list", "--formula", package],
                capture_output=True,
                text=True,
                check=False
            )
            return result.returncode == 0
        except Exception:
            return False

    # =========================================================================
    # Private Helpers
    # =========================================================================

    def _discover_brew(self) -> str:
        """
        Finds the Homebrew executable.
        Resolves PATH missing issues on Apple Silicon (M-series) Macs
        where brew is installed to a non-standard directory (/opt/homebrew).
        """
        # Standard system PATH check
        path_brew = shutil.which("brew")
        if path_brew:
            return path_brew

        # Fallback standard locations if the executing context has no loaded shell PATH
        standard_locations = [
            "/opt/homebrew/bin/brew",  # Apple Silicon (Macs 2020+) [2]
            "/usr/local/bin/brew",  # Intel Macs (Macs < 2020)
            "/home/linuxbrew/.linuxbrew/bin/brew"  # Linuxbrew
        ]

        for path in standard_locations:
            if Path(path).exists():
                return path

        return "brew"  # Ultimate fallback to default lookup string


# ==========================================
# Self-Test Block
# ==========================================
if __name__ == "__main__":
    print("--- Running BrewPackageManager Diagnostic Test ---")
    brew_mgr = BrewPackageManager()

    if not brew_mgr.is_available():
        print("❌ Homebrew is not available on this host (expected if not running on macOS).")
    else:
        print(f"✅ Homebrew executable found at: {brew_mgr.executable}")

        # Safe query test (no sudo or install actions run)
        test_pkg = "cmake"
        installed_status = brew_mgr.is_installed(test_pkg)
        print(f"🔍 Checking if '{test_pkg}' is installed locally... {installed_status}")