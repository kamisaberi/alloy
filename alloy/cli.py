# alloy/cli.py
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional
import typer

# --- Core Modules ---
from alloy.core.os_detector import detect_os
from alloy.core.parser import parse_recipe_file, parse_recipe_string, RecipeParseError
from alloy.core.resolver import resolve_requirements, ResolutionError
from alloy.core.runner import run_installation, ExecutionError

# --- Registry Subsystem ---
from alloy.registry.client_manager import AlloyRegistryManager, CONFIG_FILE
from alloy.registry.exceptions import RegistryError, PackageNotFoundError

# --- Platform Package Managers ---
from alloy.managers.apt import AptPackageManager
from alloy.managers.brew import BrewPackageManager
from alloy.managers.choco import ChocoPackageManager
from alloy.managers.dnf import DnfPackageManager
from alloy.managers.pacman import PacmanPackageManager

# Map of raw recipe keys to concrete manager classes
PM_MAP = {
    "apt": AptPackageManager,
    "apt-get": AptPackageManager,
    "brew": BrewPackageManager,
    "choco": ChocoPackageManager,
    "dnf": DnfPackageManager,
    "yum": DnfPackageManager,
    "pacman": PacmanPackageManager,
}


# Define CLI app
app = typer.Typer(
    help="Alloy: The universal, API-driven Python and System Package Manager.",
    rich_markup_mode="markdown"
)

# Instantiate the global manager (bootstraps cache, client, config automatically)
manager = AlloyRegistryManager()
INSTALLED_DB = Path.home() / ".alloy" / "installed.json"


# =========================================================================
# Helper State Persistence Methods
# =========================================================================

def _load_installed_db() -> dict:
    if not INSTALLED_DB.is_file():
        return {}
    try:
        return json.loads(INSTALLED_DB.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_installed_db(db: dict) -> None:
    INSTALLED_DB.parent.mkdir(parents=True, exist_ok=True)
    try:
        INSTALLED_DB.write_text(json.dumps(db, indent=2), encoding="utf-8")
    except OSError:
        pass


# =========================================================================
# Command 1: alloy update
# =========================================================================
@app.command()
def update():
    """
    Syncs the local lightweight index with the remote package registry.
    """
    typer.secho("⏳ Fetching remote registry package index...", fg=typer.colors.CYAN)
    try:
        manager.write_default_config()  # Ensure config exists [2]
        count = manager.registry.update_registry()
        typer.secho(f"✅ Sync complete! Cached {count} package definitions locally.", fg=typer.colors.GREEN, bold=True)
    except RegistryError as e:
        typer.secho(f"❌ Update failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)

# =========================================================================
# Command 2: alloy search <query>
# =========================================================================

@app.command()
def search(query: str):
    """
    Performs an instant offline search over cached package definitions.
    """
    try:
        matches = manager.registry.search_local(query)
        if not matches:
            typer.secho(f"No packages found matching: '{query}'", fg=typer.colors.YELLOW)
            return

        typer.secho(f"🔍 Found {len(matches)} matching package(s):\n", fg=typer.colors.CYAN, bold=True)
        for pkg in matches:
            typer.secho(f"👉 {pkg.name} ({pkg.version})", fg=typer.colors.GREEN, bold=True)
            if pkg.description:
                typer.echo(f"   Description: {pkg.description}\n")
    except RegistryError as e:
        typer.secho(f"❌ Search failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


# =========================================================================
# Command 3: alloy install <package>
# =========================================================================

@app.command()
def install(
    package: str = typer.Argument(..., help="Package name from registry or path to a local alloy.yaml file"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Evaluate the installation requirements without modifying files"),
    force: bool = typer.Option(False, "--force", help="Skip checking for cached configurations and force redownloading")
):
    """
    Resolves OS and Python requirements, installs system packages, and builds the library.
    """
    try:
        # Step 1: Parse the recipe (Detect if local file path or remote API target)
        path_target = Path(package)
        if path_target.is_file():
            typer.secho(f"📄 Parsing local recipe file: {package}", fg=typer.colors.CYAN)
            recipe = parse_recipe_file(path_target)
        else:
            typer.secho(f"⏳ Fetching recipe for '{package}' from registry...", fg=typer.colors.CYAN)
            recipe = manager.registry.get_recipe(package, force_update=force)

        # Step 2: Discover OS details
        os_info = detect_os()
        typer.echo(f"🖥️  Detected OS: {os_info.system} (Distro: {os_info.distribution}, Version: {os_info.version})")

        # Step 3: Resolve version constraints
        resolved_config = resolve_requirements(recipe, os_info)

        # Step 4: Redundancy check - check which system dependencies are already installed
        pm_class = PM_MAP.get(resolved_config.package_manager.lower())
        missing_packages = resolved_config.packages.copy()
        already_installed = []

        if pm_class:
            pm = pm_class()
            if pm.is_available() and resolved_config.packages:
                missing_packages = []
                for pkg in resolved_config.packages:
                    if pm.is_installed(pkg):
                        already_installed.append(pkg)
                    else:
                        missing_packages.append(pkg)

        # Step 5: Dry-Run reporting
        if dry_run:
            typer.secho("\n📢 --- Dry-Run Evaluation Summary ---", fg=typer.colors.YELLOW, bold=True)
            typer.echo(f"   Target Package:      {recipe.package.name} ({recipe.package.version})")
            typer.echo(f"   Native Manager:      {resolved_config.package_manager}")
            typer.echo(f"   Already Installed:   {', '.join(already_installed) if already_installed else 'None'}")
            typer.echo(f"   Packages to Install: {', '.join(missing_packages) if missing_packages else 'None'}")
            if resolved_config.env_vars:
                typer.echo("   Env Injections:")
                for k, v in resolved_config.env_vars.items():
                    typer.echo(f"     {k}={v}")
            typer.echo("   Python Build Steps:")
            for step in recipe.build_steps:
                typer.echo(f"     - {step}")
            return

        # Step 6: Trigger Installation [3]
        if already_installed:
            typer.secho(f"ℹ️  Skipping already-installed system packages: {', '.join(already_installed)}", fg=typer.colors.BLUE)

        # Temporarily update resolved config to omit packages that are already present
        resolved_config.packages = missing_packages

        # Run system and python setup [3]
        run_installation(resolved_config, recipe.build_steps)

        # Step 7: Record installation state locally
        db = _load_installed_db()
        db[recipe.package.name.lower()] = {
            "version": recipe.package.version,
            "package_manager": resolved_config.package_manager,
            "system_packages": resolved_config.packages + already_installed
        }
        _save_installed_db(db)

        typer.secho(f"\n🎉 Successfully installed {recipe.package.name}!", fg=typer.colors.GREEN, bold=True)

    except (RecipeParseError, ResolutionError, ExecutionError, RegistryError) as e:
        typer.secho(f"\n❌ Installation failed: {e}", fg=typer.colors.RED, err=True)
        raise typer.Exit(code=1)


# ==========================================
# Command 4: alloy remove <package>
# ==========================================

@app.command()
def remove(
    package: str = typer.Argument(..., help="Name of the installed package to remove"),
    purge: bool = typer.Option(False, "--purge", help="Attempt to uninstall all system dependencies that were installed with it")
):
    """
    Uninstalls the specified Python library, with optional native system package purging.
    """
    package_lower = package.lower().strip()
    db = _load_installed_db()

    # Step 1: Run standard pip uninstall
    typer.secho(f"⏳ Uninstalling Python package '{package}'...", fg=typer.colors.CYAN)
    try:
        subprocess.run([sys.executable, "-m", "pip", "uninstall", "-y", package], check=True)
        typer.secho(f"✅ Python package '{package}' uninstalled successfully.", fg=typer.colors.GREEN)
    except subprocess.CalledProcessError:
        typer.secho(f"⚠️  Failed to cleanly remove pip package '{package}'. It might have already been deleted.", fg=typer.colors.YELLOW)

    # Step 2: Handle Native System Purging
    if purge and package_lower in db:
        record = db[package_lower]
        sys_pkgs = record.get("system_packages", [])
        pm_name = record.get("package_manager", "")
        pm_class = PM_MAP.get(pm_name.lower())

        if sys_pkgs and pm_class:
            pm = pm_class()
            if pm.is_available():
                typer.secho(f"\n⚠️  Purge requested: Do you want to uninstall system packages: {', '.join(sys_pkgs)}?", fg=typer.colors.YELLOW, bold=True)
                confirm = typer.confirm("Are you sure you want to proceed?")
                if confirm:
                    try:
                        pm.uninstall(sys_pkgs)
                        typer.secho("✅ Native system package purge complete.", fg=typer.colors.GREEN)
                    except Exception as e:
                        typer.secho(f"❌ System purge failed: {e}", fg=typer.colors.RED)
            else:
                typer.secho(f"⚠️  Cannot purge: Native package manager '{pm_name}' is not available.", fg=typer.colors.YELLOW)

    # Step 3: Delete database state reference
    if package_lower in db:
        del db[package_lower]
        _save_installed_db(db)


