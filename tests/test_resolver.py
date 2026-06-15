import unittest

# Adjust imports to match your project structure
from alloy.core.os_detector import OSInfo
from alloy.core.parser import parse_recipe_string
from alloy.core.resolver import resolve_requirements, ResolutionError

# A comprehensive mock recipe with multi-stage OS, distro, and version rules
RECIPE_YAML = """
package:
  name: "test-package"
  version: "1.0.0"
system_requirements:
  linux:
    ubuntu:
      - os_version: ">=22.04"
        package_manager: "apt"
        packages: ["modern-ubuntu-pkg"]
      - os_version: ">=18.04"
        package_manager: "apt"
        packages: ["legacy-ubuntu-pkg"]
    centos:
      - os_version: ">=8"
        package_manager: "dnf"
        packages: ["centos-pkg"]
    all:
      - os_version: "all"
        package_manager: "apt"
        packages: ["fallback-linux-pkg"]
  macos:
    all:
      - os_version: ">=12.0"
        package_manager: "brew"
        packages: ["macos-modern-pkg"]
  windows:
    all:
      - os_version: "all"
        package_manager: "choco"
        packages: ["windows-pkg"]
"""


class TestRequirementsResolver(unittest.TestCase):

    def setUp(self):
        """Parses the global mock recipe once before each test."""
        self.recipe = parse_recipe_string(RECIPE_YAML)

    def test_resolve_ubuntu_modern_exact_and_specifier(self):
        """Verifies resolution selects the higher-matching config block on Ubuntu 22.04."""
        host = OSInfo(system="linux", distribution="ubuntu", version="22.04")
        config = resolve_requirements(self.recipe, host)

        self.assertEqual(config.package_manager, "apt")
        self.assertEqual(config.packages, ["modern-ubuntu-pkg"])

    def test_resolve_ubuntu_legacy_fallback(self):
        """Verifies resolution drops down to the lower configuration block if constraint is met."""
        # Ubuntu 20.04 meets >=18.04, but does NOT meet >=22.04. It should select legacy.
        host = OSInfo(system="linux", distribution="ubuntu", version="20.04")
        config = resolve_requirements(self.recipe, host)

        self.assertEqual(config.package_manager, "apt")
        self.assertEqual(config.packages, ["legacy-ubuntu-pkg"])

    def test_resolve_ubuntu_with_non_standard_version(self):
        """Verifies that OS version strings with suffixes (like '22.04-LTS') are successfully scrubbed and matched."""
        host = OSInfo(system="linux", distribution="ubuntu", version="22.04-LTS")
        config = resolve_requirements(self.recipe, host)

        self.assertEqual(config.packages, ["modern-ubuntu-pkg"])

    def test_resolve_linux_fallback_distro(self):
        """Verifies that Linux distributions not explicitly mapped (e.g., Debian) gracefully match the 'all' fallback."""
        host = OSInfo(system="linux", distribution="debian", version="11.0")
        config = resolve_requirements(self.recipe, host)

        self.assertEqual(config.packages, ["fallback-linux-pkg"])

    def test_resolve_macos_modern(self):
        """Verifies macOS version specifier matching."""
        host = OSInfo(system="macos", distribution="all", version="14.2.1")
        config = resolve_requirements(self.recipe, host)

        self.assertEqual(config.package_manager, "brew")
        self.assertEqual(config.packages, ["macos-modern-pkg"])

    def test_resolve_windows_unconditional_match(self):
        """Verifies Windows 'all' wildcard matching behaves correctly."""
        host = OSInfo(system="windows", distribution="all", version="11")
        config = resolve_requirements(self.recipe, host)

        self.assertEqual(config.package_manager, "choco")
        self.assertEqual(config.packages, ["windows-pkg"])

    def test_unsupported_os_version(self):
        """Verifies that meeting the distro key but failing the version constraints raises a ResolutionError."""
        # Host is Ubuntu 16.04 (does not satisfy >=18.04 or >=22.04)
        host = OSInfo(system="linux", distribution="ubuntu", version="16.04")

        with self.assertRaises(ResolutionError) as context:
            resolve_requirements(self.recipe, host)

        self.assertIn("not supported", str(context.exception))

    def test_unsupported_os_family(self):
        """Verifies that running on an completely unsupported OS family raises a ResolutionError."""
        # Host is FreeBSD, which does not exist in our recipe at all.
        host = OSInfo(system="freebsd", distribution="unknown", version="13.2-release")

        with self.assertRaises(ResolutionError) as context:
            resolve_requirements(self.recipe, host)

        self.assertIn("no system requirements defined", str(context.exception).lower())

    def test_invalid_specifier_in_recipe(self):
        """Verifies that a malformed version constraint inside a recipe raises a clean ResolutionError."""
        corrupt_yaml = """
        package:
          name: "corrupt"
          version: "1.0.0"
        system_requirements:
          linux:
            ubuntu:
              - os_version: "invalid>=>>=22.04"
                package_manager: "apt"
        """
        recipe = parse_recipe_string(corrupt_yaml)
        host = OSInfo(system="linux", distribution="ubuntu", version="22.04")

        with self.assertRaises(ResolutionError) as context:
            resolve_requirements(recipe, host)

        self.assertIn("Invalid version constraint", str(context.exception))


if __name__ == "__main__":
    unittest.main()