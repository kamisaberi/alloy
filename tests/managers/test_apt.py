import os
import subprocess
import unittest
from unittest.mock import patch, MagicMock

# Adjust imports to match your project structure
from alloy.managers.apt import AptPackageManager
from alloy.managers.base import PackageManagerError


class TestAptPackageManager(unittest.TestCase):

    def setUp(self):
        """Sets up a clean instance of AptPackageManager before each test."""
        self.manager = AptPackageManager()

    def test_properties(self):
        """Verifies metadata properties return the correct identifying strings."""
        self.assertEqual(self.manager.name, "apt")
        self.assertEqual(self.manager.executable, "apt-get")

    @patch("shutil.which")
    def test_is_available(self, mock_which):
        """Verifies is_available correctly queries the system PATH for apt-get."""
        # Case 1: apt-get is available
        mock_which.return_value = "/usr/bin/apt-get"
        self.assertTrue(self.manager.is_available())
        mock_which.assert_called_with("apt-get")

        # Case 2: apt-get is missing
        mock_which.return_value = None
        self.assertFalse(self.manager.is_available())

    @patch("subprocess.run")
    def test_is_installed_true(self, mock_run):
        """Verifies is_installed returns True when dpkg-query finds the package."""
        # Mock dpkg-query returning standard success payload
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "install ok installed"
        mock_run.return_value = mock_result

        self.assertTrue(self.manager.is_installed("git"))

        # Verify exact dpkg-query parameter formatting
        mock_run.assert_called_once_with(
            ["dpkg-query", "-W", "-f=${Status}", "git"],
            capture_output=True,
            text=True,
            check=False
        )

    @patch("subprocess.run")
    def test_is_installed_false(self, mock_run):
        """Verifies is_installed returns False when dpkg-query returns non-installed states."""
        # Case 1: dpkg-query returns a non-zero exit code (package unknown)
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_run.return_value = mock_result
        self.assertFalse(self.manager.is_installed("nonexistent-package"))

        # Case 2: dpkg-query raises OSError (dpkg binary missing or corrupted)
        mock_run.side_effect = OSError("command not found")
        self.assertFalse(self.manager.is_installed("git"))

    @patch.object(AptPackageManager, "_execute")
    def test_update_database_command(self, mock_execute):
        """Verifies update_database executes 'apt-get update' with sudo."""
        self.manager.update_database()

        # Verify we do NOT pass a redundant '-y' flag
        mock_execute.assert_called_once_with(["apt-get", "update"], use_sudo=True)

    @patch.object(AptPackageManager, "_execute")
    def test_install_packages(self, mock_execute):
        """Verifies install correctly formats package lists and passes sudo instructions."""
        # Case 1: No packages requested (should return immediately without calling execute)
        self.manager.install([])
        mock_execute.assert_not_called()

        # Case 2: Install packages list
        self.manager.install(["git", "cmake"])
        mock_execute.assert_called_once_with(
            ["apt-get", "install", "-y", "-q", "git", "cmake"],
            use_sudo=True
        )

    @patch.object(AptPackageManager, "_execute")
    def test_uninstall_packages(self, mock_execute):
        """Verifies uninstall formats package lists and triggers apt removal commands."""
        # Case 1: No packages requested
        self.manager.uninstall([])
        mock_execute.assert_not_called()

        # Case 2: Uninstall packages
        self.manager.uninstall(["git"])
        mock_execute.assert_called_once_with(
            ["apt-get", "remove", "-y", "-q", "git"],
            use_sudo=True
        )

    @patch.object(AptPackageManager, "_execute")
    def test_environment_isolation(self, mock_execute):
        """
        Tests the execution environment swapper.
        Ensures DEBIAN_FRONTEND and NEEDRESTART_MODE are injected strictly
        inside the subprocess call, and fully restored outside.
        """
        # Ensure target variables do not exist in the host process environment initially
        os.environ.pop("DEBIAN_FRONTEND", None)
        os.environ.pop("NEEDRESTART_MODE", None)

        captured_env = {}

        # Capture the active environment state precisely inside the _execute block
        def fake_execute(cmd, use_sudo=False):
            captured_env.update(os.environ)
            return MagicMock()

        mock_execute.side_effect = fake_execute

        # Run an install trigger
        self.manager.install(["git"])

        # 1. Assert variables were injected inside the running execution context
        self.assertEqual(captured_env.get("DEBIAN_FRONTEND"), "noninteractive")
        self.assertEqual(captured_env.get("NEEDRESTART_MODE"), "a")

        # 2. Assert variables were completely scrubbed from the global process afterward
        self.assertNotIn("DEBIAN_FRONTEND", os.environ)
        self.assertNotIn("NEEDRESTART_MODE", os.environ)


if __name__ == "__main__":
    unittest.main()