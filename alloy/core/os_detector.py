import platform
import sys
from dataclasses import dataclass, asdict

# On Linux, Alloy depends on the third-party 'distro' library for accurate
# distribution name and version detection. We fall back gracefully if it is missing.
try:
    import distro
except ImportError:
    distro = None


@dataclass
class OSInfo:
    system: str  # 'linux', 'macos', 'windows' (normalized to lowercase)
    distribution: str  # 'ubuntu', 'centos', 'debian', or 'all' for non-linux
    version: str  # '22.04', '14.2.1', '11', etc.

    def to_dict(self) -> dict:
        """Serializes the OSInfo dataclass into a standard dictionary."""
        return asdict(self)


def detect_os() -> OSInfo:
    """
    Detects the host operating system family, distribution, and system version.
    Normalizes outputs to lowercase to guarantee consistent matching in YAMLs.
    """
    system_name = platform.system().lower()

    if system_name == "linux":
        return _detect_linux()
    elif system_name in ("darwin", "macos"):
        return _detect_macos()
    elif system_name == "windows":
        return _detect_windows()
    else:
        # Fallback for other operating systems (e.g., FreeBSD, OpenBSD)
        return OSInfo(
            system=system_name,
            distribution="unknown",
            version=platform.release().lower()
        )


def _detect_linux() -> OSInfo:
    """Detects Linux-specific distribution and version details."""
    dist_id = "unknown"
    dist_version = "0.0"

    if distro:
        # 'distro' provides robust distribution ID (e.g., 'ubuntu', 'arch', 'centos')
        dist_id = distro.id().lower()
        dist_version = distro.version()
    else:
        # Basic fallback using platform module if distro is missing
        dist_id = "linux"
        dist_version = platform.release()

    return OSInfo(
        system="linux",
        distribution=dist_id,
        version=dist_version
    )


def _detect_macos() -> OSInfo:
    """Detects macOS-specific version details."""
    # platform.mac_ver() returns a tuple like ('14.2.1', ('', '', ''), 'arm64')
    mac_version = platform.mac_ver()[0]

    if not mac_version:
        # Fallback if mac_ver() unexpectedly returns empty
        mac_version = platform.release()

    return OSInfo(
        system="macos",
        distribution="all",  # macOS does not have divergent distributions
        version=mac_version
    )


def _detect_windows() -> OSInfo:
    """
    Detects Windows version details. Handles the built-in Python edge case
    where Windows 11 build is reported by the OS as Windows 10.
    """
    win_release = platform.release()

    if sys.platform == "win32":
        try:
            # sys.getwindowsversion().build >= 22000 natively indicates Windows 11
            # (Python's platform.release() sometimes maps build 22000+ to '10')
            win_build = sys.getwindowsversion().build
            if win_build >= 22000 and win_release == "10":
                win_release = "11"
        except AttributeError:
            pass

    return OSInfo(
        system="windows",
        distribution="all",  # Windows does not have divergent distributions
        version=win_release
    )


if __name__ == "__main__":
    # Self-test block to run directly for debugging
    info = detect_os()
    print("--- Detected OS Information ---")
    print(f"System:       {info.system}")
    print(f"Distribution: {info.distribution}")
    print(f"Version:      {info.version}")
    print(f"JSON-ready:   {info.to_dict()}")