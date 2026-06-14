import subprocess
from typing import List
from alloy.managers.base import BasePackageManager, PackageManagerError


class ChocoPackageManager(BasePackageManager):
    """
    Implementation of the Windows Chocolatey native package manager.
    """

    @property
    def name(self) -> str:
        return "choco"

    @property
    def executable(self) -> str:
        return "choco"

    def update_database(self) -> None:
        """
        Chocolatey queries registries live during install operations,
        so an explicit 'update database' does not exist. We treat this as a no-op.
        """
        print("⏳ Chocolatey queries repository indexes live; skipping update database.")

    def install(self, packages: List[str]) -> None:
        """
        Installs a list of Chocolatey packages non-interactively.
        """
        if not packages:
            return

        print(f"⏳ Running choco install -y {' '.join(packages)}...")

        # -y automatically confirms prompts
        # --no-progress can be added to keep CI logs cleaner, but standard output is fine
        cmd = ["choco", "install", "-y"] + packages
        self._execute(cmd, use_sudo=False)

    def uninstall(self, packages: List[str]) -> None:
        """
        Uninstalls a list of Chocolatey packages.
        """
        if not packages:
            return

        print(f"⏳ Running choco uninstall -y {' '.join(packages)}...")
        cmd = ["choco", "uninstall", "-y"] + packages
        self._execute(cmd, use_sudo=False)

    def is_installed(self, package: str) -> bool:
        """
        Queries the local Chocolatey registry to check if a package is installed.
        Adapts gracefully between Chocolatey v1 and v2 registry behaviors.
        """
        try:
            # Step 1: Attempt Chocolatey v1.x check using '--local-only' (-lo)
            # We use --limit-output (-r) and --exact (-e) to return machine-readable lines
            result = subprocess.run(
                ["choco", "list", "-lo", "-r", "-e", package],
                capture_output=True,
                text=True,
                check=False
            )

            # Step 2: Fallback to Chocolatey v2.x if v1.x command fails (since --local-only was removed)
            if result.returncode != 0:
                result = subprocess.run(
                    ["choco", "list", "-r", "-e", package],
                    capture_output=True,
                    text=True,
                    check=False
                )

            # A return code of 0 and containing the package name indicates it is installed
            return result.returncode == 0 and package.lower() in result.stdout.lower()

        except Exception:
            return False


# ==========================================
# Self-Test Block
# ==========================================
if __name__ == "__main__":
    import sys

    print("--- Running ChocoPackageManager Diagnostic Test ---")
    choco_mgr = ChocoPackageManager()

    if not choco_mgr.is_available():
        print("❌ choco is not available on this host (expected if not running on Windows with Chocolatey).")
    else:
        print("✅ choco executable found in system PATH!")

        # Safe query test (does not elevate or modify files)
        test_pkg = "git"
        installed_status = choco_mgr.is_installed(test_pkg)
        print(f"🔍 Checking if '{test_pkg}' is installed locally... {installed_status}")