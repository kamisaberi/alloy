import os
import subprocess
from typing import List
from alloy.managers.base import BasePackageManager, PackageManagerError


class AptPackageManager(BasePackageManager):
    """
    Implementation of the Debian/Ubuntu 'apt-get' native package manager.
    """






    @property
    def name(self) -> str:
        return "apt"

    @property
    def executable(self) -> str:
        return "apt-get"

    def update_database(self) -> None:
        """
        Refreshes the local apt repository cache.
        """
        print("⏳ Syncing apt package repositories...")
        self._execute(["apt-get", "update", "-y"], use_sudo=True)

    def install(self, packages: List[str]) -> None:
        """
        Installs a list of apt packages.
        Forces non-interactive frontend to prevent hanging in headless/Docker environments.
        """
        if not packages:
            return

        # Safeguard: Force DEBIAN_FRONTEND=noninteractive so apt-get doesn't hang
        # waiting for keyboard input on post-install prompts.
        old_frontend = os.environ.get("DEBIAN_FRONTEND")
        os.environ["DEBIAN_FRONTEND"] = "noninteractive"

        try:
            cmd = ["apt-get", "install", "-y", "-q"] + packages
            self._execute(cmd, use_sudo=True)
        finally:
            # Restore original DEBIAN_FRONTEND state
            if old_frontend is not None:
                os.environ["DEBIAN_FRONTEND"] = old_frontend
            else:
                os.environ.pop("DEBIAN_FRONTEND", None)

    def uninstall(self, packages: List[str]) -> None:
        """
        Uninstalls a list of apt packages safely.
        """
        if not packages:
            return

        cmd = ["apt-get", "remove", "-y"] + packages
        self._execute(cmd, use_sudo=True)

    def is_installed(self, package: str) -> bool:
        """
        Queries the local dpkg database to check if a package is fully installed.
        This does not require root/sudo privileges.
        """
        try:
            # Query the status of the package.
            # If installed, 'dpkg-query' returns 'install ok installed'
            result = subprocess.run(
                ["dpkg-query", "-W", "-f=${Status}", package],
                capture_output=True,
                text=True,
                check=False  # Do not raise exception on return code != 0 (e.g. Package Not Found)
            )
            return result.returncode == 0 and "install ok installed" in result.stdout
        except Exception:
            # Fall back to False if dpkg-query is missing, broken, or not executable
            return False


# ==========================================
# Self-Test Block
# ==========================================
if __name__ == "__main__":
    print("--- Running AptPackageManager Diagnostic Test ---")
    apt = AptPackageManager()

    if not apt.is_available():
        print("❌ apt-get is not available on this host (expected if not running on Debian/Ubuntu).")
    else:
        print("✅ apt-get executable found in system PATH!")

        # Safe query test (does not install or modify files, no sudo required)
        test_pkg = "git"
        installed_status = apt.is_installed(test_pkg)
        print(f"🔍 Checking if '{test_pkg}' is installed locally... {installed_status}")