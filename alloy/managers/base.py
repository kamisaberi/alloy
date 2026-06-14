from abc import ABC, abstractmethod
from typing import List
import shutil
import subprocess
import sys


class PackageManagerError(Exception):
    """Base exception for package manager execution failures."""
    pass


class BasePackageManager(ABC):
    """
    Abstract Base Class that all native package managers (apt, brew, dnf, choco)
    must implement to integrate with the Alloy system.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        The name of the package manager as recognized in recipes (e.g., 'apt').
        """
        pass

    @property
    @abstractmethod
    def executable(self) -> str:
        """
        The name of the command line executable (e.g., 'apt-get').
        """
        pass

    def is_available(self) -> bool:
        """
        Checks if the package manager's binary exists on the host's system PATH.
        Can be overridden if custom verification logic is required.
        """
        return shutil.which(self.executable) is not None

    @abstractmethod
    def update_database(self) -> None:
        """
        Refreshes the local package list or database index of the package manager.
        Equivalent to 'apt-get update' or 'brew update'.
        """
        pass

    @abstractmethod
    def install(self, packages: List[str]) -> None:
        """
        Installs a list of native system packages.
        """
        pass

    @abstractmethod
    def uninstall(self, packages: List[str]) -> None:
        """
        Uninstalls a list of native system packages.
        """
        pass

    @abstractmethod
    def is_installed(self, package: str) -> bool:
        """
        Queries the host OS to check if a specific system package is already installed.
        Helps Alloy avoid running redundant 'install' triggers.
        """
        pass

    # =========================================================================
    # Protected Helpers for Inheriting Subclasses
    # =========================================================================

    def _execute(self, cmd: List[str], use_sudo: bool = False, check: bool = True) -> subprocess.CompletedProcess:
        """
        A protected helper that wraps subprocess execution.
        Safely prepends 'sudo' if required and available on the host.
        """
        final_cmd = cmd.copy()

        if use_sudo and self._should_use_sudo():
            final_cmd = ["sudo"] + final_cmd

        try:
            # Stream output directly to the terminal so the user sees live progress
            return subprocess.run(
                final_cmd,
                check=check,
                stdout=sys.stdout,
                stderr=sys.stderr
            )
        except subprocess.CalledProcessError as e:
            cmd_str = " ".join(final_cmd)
            raise PackageManagerError(
                f"Command failed with exit code {e.returncode} while running:\n  '{cmd_str}'"
            )

    def _should_use_sudo(self) -> bool:
        """
        Checks if sudo is required (user is not running as root, and sudo is on the PATH).
        """
        import os
        try:
            is_root = os.geteuid() == 0
        except AttributeError:
            # Windows / Non-Unix environments do not support geteuid()
            is_root = False

        has_sudo = shutil.which("sudo") is not None
        return not is_root and has_sudo