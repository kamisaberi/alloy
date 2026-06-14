import subprocess
from typing import List
from alloy.managers.base import BasePackageManager, PackageManagerError


class PacmanPackageManager(BasePackageManager):
    """
    Implementation of the Arch Linux 'pacman' native package manager.
    """

    @property
    def name(self) -> str:
        return "pacman"

    @property
    def executable(self) -> str:
        return "pacman"

    def update_database(self) -> None:
        """
        Syncs and refreshes the local package databases from remote repositories.
        Equivalent to running 'pacman -Sy' (requires sudo).
        """
        print("⏳ Syncing pacman package databases...")
        self._execute(["pacman", "-Sy"], use_sudo=True)

    def install(self, packages: List[str]) -> None:
        """
        Installs a list of native Arch Linux packages non-interactively.
        """
        if not packages:
            return

        print(f"⏳ Running pacman -S --noconfirm {' '.join(packages)}...")
        # --noconfirm bypasses keyboard prompts to accept keyrings, dependencies, etc.
        cmd = ["pacman", "-S", "--noconfirm"] + packages
        self._execute(cmd, use_sudo=True)

    def uninstall(self, packages: List[str]) -> None:
        """
        Uninstalls a list of native Arch Linux packages.
        """
        if not packages:
            return

        print(f"⏳ Running pacman -R --noconfirm {' '.join(packages)}...")
        # -R safely removes specified packages
        cmd = ["pacman", "-R", "--noconfirm"] + packages
        self._execute(cmd, use_sudo=True)

    def is_installed(self, package: str) -> bool:
        """
        Queries the local pacman database to verify if a package is installed.
        This does not require root/sudo privileges.
        """
        try:
            # pacman -Q <package_name> returns exit code 0 if installed, 1 if not.
            result = subprocess.run(
                ["pacman", "-Q", package],
                capture_output=True,
                text=True,
                check=False  # Do not raise exception on return code != 0 (e.g. Package Not Found)
            )
            return result.returncode == 0
        except Exception:
            # Fall back to False if pacman is missing or non-executable
            return False


# ==========================================
# Self-Test Block
# ==========================================
if __name__ == "__main__":
    print("--- Running PacmanPackageManager Diagnostic Test ---")
    pac_mgr = PacmanPackageManager()

    if not pac_mgr.is_available():
        print("❌ pacman is not available on this host (expected if not running on Arch Linux).")
    else:
        print("✅ pacman executable found in system PATH!")

        # Safe query test (does not elevate or modify files)
        test_pkg = "git"
        installed_status = pac_mgr.is_installed(test_pkg)
        print(f"🔍 Checking if '{test_pkg}' is installed locally... {installed_status}")