from typing import Optional
from packaging.specifiers import SpecifierSet, InvalidSpecifier
from packaging.version import Version, InvalidVersion

from alloy.core.os_detector import OSInfo
from alloy.core.parser import Recipe, RequirementConfig


class ResolutionError(Exception):
    """Raised when Alloy cannot find a matching system requirements block."""
    pass


def resolve_requirements(recipe: Recipe, os_info: OSInfo) -> RequirementConfig:
    """
    Evaluates the parsed Recipe against the host's OSInfo.
    Identifies and returns the correct RequirementConfig configuration block.

    Raises:
        ResolutionError: If no matching system block or version constraint matches.
    """
    system = os_info.system.lower()
    distro = os_info.distribution.lower()
    host_version = os_info.version

    # Step 1: Look up the system-specific block (e.g. 'linux', 'macos', 'windows')
    sys_reqs = getattr(recipe.system_requirements, system, None)
    if not sys_reqs:
        raise ResolutionError(
            f"This package has no system requirements defined for OS: '{system}'"
        )

    # Step 2: Resolve the distribution (Linux-only, or fallbacks)
    configs = []
    if system == "linux":
        if distro in sys_reqs:
            configs = sys_reqs[distro]
        elif "all" in sys_reqs:
            configs = sys_reqs["all"]
        elif "default" in sys_reqs:
            configs = sys_reqs["default"]
    else:
        # macOS and Windows configs are usually listed under 'all' or 'default'
        if "all" in sys_reqs:
            configs = sys_reqs["all"]
        elif "default" in sys_reqs:
            configs = sys_reqs["default"]

    if not configs:
        raise ResolutionError(
            f"No requirement configurations found for system '{system}' (distribution: '{distro}')."
        )

    # Step 3: Evaluate version constraints
    for config in configs:
        constraint = config.os_version.strip()

        # Unconditional matches (e.g., 'all', '*', or 'any')
        if constraint.lower() in ("all", "*", "", "any"):
            return config

        # Match using specifiers (e.g., '>=20.04')
        try:
            cleaned_host_version = _clean_version_string(host_version)
            specifier = SpecifierSet(constraint)

            # Check if host's version satisfies the constraint (e.g., '22.04' in '>=20.04')
            if specifier.contains(cleaned_host_version, prereleases=True):
                return config

        except InvalidSpecifier:
            raise ResolutionError(
                f"Invalid version constraint string '{constraint}' found "
                f"in recipe system requirements block: {system}/{distro}."
            )
        except InvalidVersion:
            # Fall back to exact string match if the OS version is highly non-standard
            # and cannot be parsed by PEP 440 specifications.
            if host_version == constraint:
                return config

    # Step 4: If we run through all configurations and find no matches
    supported_versions = ", ".join(c.os_version for c in configs)
    raise ResolutionError(
        f"Your OS version '{host_version}' on {system}/{distro} is not supported "
        f"by this library. Supported versions: {supported_versions}"
    )


def _clean_version_string(version_str: str) -> str:
    """
    Cleans up common OS version suffixes so that standard Python version
    parsers (PEP 440) don't throw warnings or errors.
    Example: '22.04.1-LTS' -> '22.04.1'
    """
    # Split on typical suffix indicators
    base_parts = version_str.split('-')[0].split('+')[0]

    # Extract only digits and decimal points
    cleaned = "".join(c for c in base_parts if c.isdigit() or c == ".")

    return cleaned if cleaned else version_str


# ==========================================
# Self-Test Block
# ==========================================
if __name__ == "__main__":
    from alloy.core.parser import parse_recipe_string

    # 1. Create a dummy recipe
    sample_yaml = """
    package:
      name: "cv-core"
      version: "1.0.0"
    system_requirements:
      linux:
        ubuntu:
          - os_version: ">=22.00"
            package_manager: "apt"
            packages: ["libopencv-dev-modern"]
          - os_version: ">=18.04"
            package_manager: "apt"
            packages: ["libopencv-dev-legacy"]
    """
    test_recipe = parse_recipe_string(sample_yaml)

    # 2. Mock some different user OS profiles
    modern_ubuntu = OSInfo(system="linux", distribution="ubuntu", version="22.04-LTS")
    legacy_ubuntu = OSInfo(system="linux", distribution="ubuntu", version="18.04")
    unsupported_ubuntu = OSInfo(system="linux", distribution="ubuntu", version="16.04")

    print("--- Running Resolver Self-Test ---")
    try:
        # Test Case 1: Resolve on Ubuntu 22.04
        config_modern = resolve_requirements(test_recipe, modern_ubuntu)
        print(f"✅ Ubuntu 22.04 resolved. Packages: {config_modern.packages}")

        # Test Case 2: Resolve on Ubuntu 18.04
        config_legacy = resolve_requirements(test_recipe, legacy_ubuntu)
        print(f"✅ Ubuntu 18.04 resolved. Packages: {config_legacy.packages}")

        # Test Case 3: Test expected failure on unsupported OS version
        print("⏳ Verifying expected failure on Ubuntu 16.04...")
        resolve_requirements(test_recipe, unsupported_ubuntu)
        print("❌ Test Failed (Should have raised a ResolutionError)")
    except ResolutionError as e:
        print(f"✅ Gracefully failed as expected on Ubuntu 16.04:\n   -> {e}")