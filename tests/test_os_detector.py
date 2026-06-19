import sys
import unittest
from unittest.mock import patch, MagicMock

# Adjust imports to match your project structure
from alloy.core.os_detector import detect_os, OSInfo


class TestOSDetector(unittest.TestCase):

    @patch("platform.system")
    @patch("alloy.core.os_detector.distro")
    def test_detect_linux_with_distro_module(self, mock_distro, mock_system):
        """Verifies Linux detection when the 'distro' package is successfully imported."""
        mock_system.return_value = "Linux"

        # Configure mocked distro properties
        mock_distro.id.return_value = "Ubuntu"
        mock_distro.version.return_value = "22.04"

        # Explicitly patch the module-level 'distro' reference to ensure it evaluates as truthy
        with patch("alloy.core.os_detector.distro", mock_distro):
            info = detect_os()

            self.assertEqual(info.system, "linux")
            self.assertEqual(info.distribution, "ubuntu")
            self.assertEqual(info.version, "22.04")

    @patch("platform.system")
    @patch("platform.release")
    def test_detect_linux_without_distro_module(self, mock_release, mock_system):
        """Verifies Linux detection gracefully degrades to defaults if 'distro' is absent."""
        mock_system.return_value = "Linux"
        mock_release.return_value = "5.15.0-generic"

        # Force 'distro' to be None to simulate import failure
        with patch("alloy.core.os_detector.distro", None):
            info = detect_os()

            self.assertEqual(info.system, "linux")
            self.assertEqual(info.distribution, "linux")  # Fallback distribution name
            self.assertEqual(info.version, "5.15.0-generic")

    @patch("platform.system")
    @patch("platform.mac_ver")
    def test_detect_macos(self, mock_mac_ver, mock_system):
        """Verifies macOS (Darwin) detection and version extraction."""
        mock_system.return_value = "Darwin"
        mock_mac_ver.return_value = ("14.2.1", ("", "", ""), "arm64")

        info = detect_os()

        self.assertEqual(info.system, "macos")
        self.assertEqual(info.distribution, "all")
        self.assertEqual(info.version, "14.2.1")

    @patch("platform.system")
    @patch("platform.release")
    @patch("sys.platform", "win32")
    @patch("sys.getwindowsversion")
    def test_detect_windows_10(self, mock_get_win_ver, mock_release, mock_system):
        """Verifies standard Windows 10 detection."""
        mock_system.return_value = "Windows"
        mock_release.return_value = "10"

        # Windows 10 build is typically < 22000 (e.g. 19045)
        mock_win_ver = MagicMock()
        mock_win_ver.build = 19045
        mock_get_win_ver.return_value = mock_win_ver

        info = detect_os()

        self.assertEqual(info.system, "windows")
        self.assertEqual(info.distribution, "all")
        self.assertEqual(info.version, "10")

    @patch("platform.system")
    @patch("platform.release")
    @patch("sys.platform", "win32")
    @patch("sys.getwindowsversion")
    def test_detect_windows_11_normalization(self, mock_get_win_ver, mock_release, mock_system):
        """
        Verifies Windows 11 normalization logic.
        Ensures that if Python's platform module returns '10' but the NT build
        number is >= 22000 (Windows 11), Alloy correctly normalizes the version to '11'.
        """
        mock_system.return_value = "Windows"
        mock_release.return_value = "10"  # Python often returns '10' for Windows 11 natively [7]

        # Build 22621 is a standard Windows 11 build (22H2)
        mock_win_ver = MagicMock()
        mock_win_ver.build = 22621
        mock_get_win_ver.return_value = mock_win_ver

        info = detect_os()

        self.assertEqual(info.system, "windows")
        self.assertEqual(info.distribution, "all")
        self.assertEqual(info.version, "11")  # Normalized successfully to 11

    @patch("platform.system")
    @patch("platform.release")
    def test_detect_unknown_operating_system(self, mock_release, mock_system):
        """Verifies fallback safety logic for unsupported operating systems."""
        mock_system.return_value = "FreeBSD"
        mock_release.return_value = "13.2-RELEASE"

        info = detect_os()

        self.assertEqual(info.system, "freebsd")
        self.assertEqual(info.distribution, "unknown")
        self.assertEqual(info.version, "13.2-release")  # Lowercase normalized


if __name__ == "__main__":
    unittest.main()
