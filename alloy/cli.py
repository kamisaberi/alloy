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



