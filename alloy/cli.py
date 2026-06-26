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


