from pathlib import Path
from typing import List, Dict, Optional
import yaml
from pydantic import BaseModel, Field, ValidationError


# ==========================================
# 1. Custom Exceptions
# ==========================================

class RecipeParseError(Exception):
    """Raised when a recipe YAML is invalid or corrupt."""
    pass


# ==========================================
# 2. Pydantic Models for Schema Validation
# ==========================================

class PackageMetadata(BaseModel):
    name: str = Field(..., min_length=1, description="The name of the Python package")
    version: str = Field(..., description="The package version")
    description: Optional[str] = Field(None, description="A brief description of the package")
    python_requires: Optional[str] = Field(None, description="Python version constraints (e.g. >=3.8)")
    python_dependencies: List[str] = Field(
        default_factory=list,
        description="Standard pip dependencies"
    )


class RequirementConfig(BaseModel):
    os_version: str = Field(..., description="OS version constraints, e.g. '>=20.04' or 'all'")
    package_manager: str = Field(..., description="Native package manager to use, e.g. 'apt', 'brew'")
    pre_install: List[str] = Field(default_factory=list,
                                   description="Commands to execute before packages are installed")
    packages: List[str] = Field(default_factory=list, description="Native packages to install")
    env_vars: Dict[str, str] = Field(default_factory=dict, description="Environment variables to inject during build")


class SystemRequirements(BaseModel):
    # Mapping distribution/category to list of configs (e.g. {"ubuntu": [RequirementConfig]})
    linux: Dict[str, List[RequirementConfig]] = Field(default_factory=dict)
    macos: Dict[str, List[RequirementConfig]] = Field(default_factory=dict)
    windows: Dict[str, List[RequirementConfig]] = Field(default_factory=dict)


class Recipe(BaseModel):
    package: PackageMetadata
    system_requirements: SystemRequirements = Field(default_factory=SystemRequirements)
    build_steps: List[str] = Field(default_factory=list,
                                   description="Commands to execute to compile and install the package")


# ==========================================
# 3. Parser Logic
# ==========================================

def parse_recipe_string(yaml_content: str) -> Recipe:
    """
    Parses a YAML string into a structured and validated Recipe object.

    Raises:
        RecipeParseError: If YAML formatting is invalid or Pydantic validation fails.
    """
    try:
        # Step 1: Safely load YAML into a raw Python dictionary
        raw_data = yaml.safe_load(yaml_content)
        if raw_data is None:
            raise RecipeParseError("The recipe file is empty.")

        # Step 2: Validate dictionary against our Pydantic model
        return Recipe.model_validate(raw_data)

    except yaml.YAMLError as e:
        raise RecipeParseError(f"YAML Syntax Error: {e}")
    except ValidationError as e:
        # Reformat Pydantic's validation error for user readability
        errors = []
        for error in e.errors():
            loc = " -> ".join(str(item) for item in error["loc"])
            msg = error["msg"]
            errors.append(f"[{loc}]: {msg}")

        error_summary = "\n  ".join(errors)
        raise RecipeParseError(f"Recipe Validation Failed:\n  {error_summary}")


def parse_recipe_file(file_path: Path) -> Recipe:
    """
    Reads and parses a local recipe file.

    Raises:
        RecipeParseError: If the file does not exist or fails validation.
    """
    path = Path(file_path)
    if not path.is_file():
        raise RecipeParseError(f"File not found: {file_path}")

    try:
        content = path.read_text(encoding="utf-8")
        return parse_recipe_string(content)
    except OSError as e:
        raise RecipeParseError(f"Failed to read file '{file_path}': {e}")


# ==========================================
# 4. Self-Test Block
# ==========================================
if __name__ == "__main__":
    # A sample valid YAML schema string to verify parser integrity
    sample_yaml = """
    package:
      name: "hypocv"
      version: "1.2.0"
      description: "Sample computer vision wrapper library."
      python_requires: ">=3.8"
      python_dependencies:
        - "numpy>=1.21.0"
        - "pybind11"

    system_requirements:
      linux:
        ubuntu:
          - os_version: ">=20.04"
            package_manager: "apt"
            packages:
              - "build-essential"
              - "libopencv-dev"
            env_vars:
              CMAKE_BUILD_TYPE: "Release"

    build_steps:
      - "pip install ."
    """

    print("--- Running Parser Self-Test ---")
    try:
        recipe = parse_recipe_string(sample_yaml)
        print("✅ Parsing Successful!")
        print(f"Package Name: {recipe.package.name}")
        print(f"Pip Deps:     {recipe.package.python_dependencies}")
        print(f"Ubuntu Deps:  {recipe.system_requirements.linux['ubuntu'][0].packages}")
    except RecipeParseError as err:
        print(f"❌ Test Failed:\n{err}")