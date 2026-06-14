import shutil
import subprocess
from typing import List
from alloy.managers.base import BasePackageManager, PackageManagerError


class DnfPackageManager(BasePackageManager):
    """
    Implementation of the Red Hat / CentOS / Fedora / Rocky Linux 'dnf'
    native package manager (with automatic fallback to 'yum').
    """

    def __init__(self):
        # Dynamically determine the available binary (dnf is preferred, yum is fallback)
        self._executable = "dnf" if shutil.which("dnf") else "yum"

    @property
    def name(self) -> str:
        return "dnf"

    @property
    def executable(self) -> str:
        return self._executable

    def update_database(self) -> None:
        """
        Refreshes the local repository index cache.
        Uses 'makecache' because 'check-update' returns non-zero exit codes (100)
        when package updates are available, which crashes subprocess execution.
        """
        print(f"⏳ Running {self._executable} makecache...")
        self._execute([self._executable, "makecache"], use_sudo=True)

    def install(self, packages: List[str]) -> None:
        """
        Installs a list of native RPM packages non-interactively.
        """
        if not packages:
            return

        print(f"⏳ Running {self._executable} install -y {' '.join(packages)}...")
        # -y automatically confirms prompts
        cmd = [self._executable, "install", "-y"] + packages
        self._execute(cmd, use_sudo=True)

    def uninstall(self, packages: List[str]) -> None:
        """
        Uninstalls a list of native RPM packages.
        """
        if not packages:
            return

        print(f"⏳ Running {self._executable} remove -y {' '.join(packages)}...")
        cmd = [self._executable, "remove", "-y"] + packages
        self._execute(cmd, use_sudo=True)

    def is_installed(self, package: str) -> bool:
        """
        Queries the local RPM database using the 'rpm' binary to check if a package is installed.
        This is incredibly fast and does not require elevated root/sudo privileges.
        """
        try:
            # rpm -q <package_name> returns exit code 0 if installed, 1 if not.
            result = subprocess.run(
                ["rpm", "-q", package],
                capture_output=True,
                text=True,
                check=False  # Do not raise exception on return code != 0 (e.g. Package Not Found)
            )
            return result.returncode == 0
        except Exception:
            # Fall back to False if 'rpm' itself is missing or non-executable
            return False


# ==========================================
# Self-Test Block
# ==========================================
if __name__ == "__main__":
    print("--- Running DnfPackageManager Diagnostic Test ---")
    dnf_mgr = DnfPackageManager()

    if not dnf_mgr.is_available():
        print(f"❌ '{dnf_mgr.executable}' is not available on this host (expected if not on RHEL/CentOS/Fedora).")
    else:
        print(f"✅ Executable found: {dnf_mgr.executable}")

        # Safe query test (does not elevate or modify files)
        test_pkg = "curl"
        installed_status = dnf_mgr.is_installed(test_pkg)
        print(f"🔍 Checking if '{test_pkg}' is installed locally... {installed_status}")