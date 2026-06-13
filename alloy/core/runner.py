import os
import shutil
import subprocess
import sys
from typing import List, Dict

from alloy.core.parser import RequirementConfig


class ExecutionError(Exception):
    """Raised when a shell command or package installation fails."""
    pass


def run_installation(config: RequirementConfig, build_steps: List[str] = None) -> None:
    """
    Orchestrates the entire system and Python installation sequence.

    1. Injects target environment variables.
    2. Runs pre-installation hooks.
    3. Triggers native system packages via apt/brew/dnf/choco.
    4. Executes post-native Python compilation & installation build steps.
    """
    env_vars = config.env_vars

    # Step 1: Log environment variable injections
    if env_vars:
        print("💉 Injecting recipe environment variables:")
        for key, value in env_vars.items():
            print(f"   {key}={value}")

    # Step 2: Execute Pre-Install hooks (e.g. 'apt-get update')
    if config.pre_install:
        print("\n🔄 Running pre-installation hooks...")
        for cmd in config.pre_install:
            _execute_command(cmd, env=env_vars, use_shell=True)

    # Step 3: Install native OS packages
    if config.packages:
        print(f"\n📦 Installing system packages via '{config.package_manager}'...")
        install_cmd = _get_install_command(config.package_manager, config.packages)

        # Windows requires shell=True to safely run script-based binaries like 'choco' or 'brew'
        use_shell = (sys.platform == "win32")
        _execute_command(install_cmd, env=env_vars, use_shell=use_shell)

    # Step 4: Run compilation/build steps
    if build_steps:
        print("\n🏗️  Running Python compilation and build steps...")
        for cmd in build_steps:
            _execute_command(cmd, env=env_vars, use_shell=True)

    print("\n✅ Installation completed successfully!")


def _execute_command(command: str | List[str], env: Dict[str, str], use_shell: bool = False) -> None:
    """
    Spawns a subprocess to execute commands, inherits the host OS environment,
    and streams standard output and errors to the terminal in real-time.
    """
    # Create copy of system env and inject recipe's custom env vars
    current_env = os.environ.copy()
    current_env.update(env)

    # Display friendly terminal output
    cmd_str = command if isinstance(command, str) else " ".join(command)
    print(f"👉 Executing: {cmd_str}")

    try:
        # Stream output directly to the current shell interface
        subprocess.run(
            command,
            env=current_env,
            shell=use_shell,
            check=True,
            stdout=sys.stdout,
            stderr=sys.stderr
        )
    except subprocess.CalledProcessError as e:
        raise ExecutionError(
            f"Command failed with exit code {e.returncode} while running:\n  '{cmd_str}'"
        )


def _get_install_command(package_manager: str, packages: List[str]) -> List[str]:
    """
    Formulates a safe list-based execution command for the targeted package manager,
    automatically prepending elevation commands (sudo) when appropriate.
    """
    pm = package_manager.lower()

    if pm in ("apt", "apt-get"):
        if _is_root():
            return ["apt-get", "install", "-y"] + packages
        elif _has_command("sudo"):
            return ["sudo", "apt-get", "install", "-y"] + packages
        return ["apt-get", "install", "-y"] + packages

    elif pm in ("dnf", "yum"):
        base_cmd = "dnf" if _has_command("dnf") else "yum"
        if _is_root():
            return [base_cmd, "install", "-y"] + packages
        elif _has_command("sudo"):
            return ["sudo", base_cmd, "install", "-y"] + packages
        return [base_cmd, "install", "-y"] + packages

    elif pm == "brew":
        # Homebrew explicitly forbids running as root/sudo
        return ["brew", "install"] + packages

    elif pm == "choco":
        return ["choco", "install", "-y"] + packages

    else:
        # Generic fallback
        return [pm, "install"] + packages


def _is_root() -> bool:
    """Verifies if the current script is running under root privileges on Unix."""
    try:
        return os.geteuid() == 0
    except AttributeError:
        # Non-Unix systems (Windows) do not have geteuid()
        return False


def _has_command(cmd: str) -> bool:
    """Helper to verify if an executable exists in the system's PATH."""
    return shutil.which(cmd) is not None


# ==========================================
# Self-Test Block
# ==========================================
if __name__ == "__main__":
    print("--- Running Runner Safe Command Formatting Test ---")

    # Mock some packages and check generated commands
    pkgs = ["cmake", "git"]

    print(f"Brew Format:  {_get_install_command('brew', pkgs)}")
    print(f"Choco Format: {_get_install_command('choco', pkgs)}")

    # We won't trigger root installation on the developer machine,
    # but we can test running a harmless echo script.
    print("\n--- Running Safe Shell Execution Test ---")
    try:
        mock_config = RequirementConfig(
            os_version="all",
            package_manager="echo",
            pre_install=["echo 'Hello from pre-install!'"],
            packages=[],  # Empty so it skips system install
            env_vars={"ALLOY_TEST": "Active"}
        )

        run_installation(mock_config, build_steps=["echo 'Hello from Python build step!'"])
    except ExecutionError as err:
        print(f"❌ Test Failed:\n{err}")