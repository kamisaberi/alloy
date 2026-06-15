import tempfile
import unittest
from pathlib import Path

# Adjust imports to match your project structure
from alloy.core.parser import (
    parse_recipe_string,
    parse_recipe_file,
    RecipeParseError,
    Recipe
)


class TestRecipeParser(unittest.TestCase):

    def test_parse_valid_recipe_string(self):
        """Verifies that a fully-formed, valid YAML string is correctly parsed and validated."""
        valid_yaml = """
        package:
          name: "cv-core"
          version: "1.0.0"
          description: "High-performance vision library."
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
        """
        recipe = parse_recipe_string(valid_yaml)

        # Verify instance and root models
        self.assertIsInstance(recipe, Recipe)
        self.assertEqual(recipe.package.name, "cv-core")
        self.assertEqual(recipe.package.version, "1.0.0")
        self.assertEqual(recipe.package.python_dependencies, ["numpy>=1.21.0", "pybind11"])

        # Verify deep system-requirements indexing
        ubuntu_configs = recipe.system_requirements.linux["ubuntu"]
        self.assertEqual(len(ubuntu_configs), 1)
        self.assertEqual(ubuntu_configs[0].os_version, ">=20.04")
        self.assertEqual(ubuntu_configs[0].packages, ["build-essential", "libopencv-dev"])
        self.assertEqual(ubuntu_configs[0].env_vars, {"CMAKE_BUILD_TYPE": "Release"})

    def test_parse_empty_recipe(self):
        """Verifies that parsing an empty string fails gracefully."""
        with self.assertRaises(RecipeParseError) as context:
            parse_recipe_string("")
        self.assertIn("empty", str(context.exception).lower())

    def test_parse_invalid_yaml_syntax(self):
        """Verifies that a syntax-level YAML error is trapped and reported cleanly."""
        # Corrupted syntax: unclosed indentation and missing list delimiters
        invalid_yaml = """
        package
          name "cv-core"
        """
        with self.assertRaises(RecipeParseError) as context:
            parse_recipe_string(invalid_yaml)
        self.assertIn("YAML Syntax Error", str(context.exception))

    def test_parse_missing_required_fields(self):
        """Verifies that Pydantic validation fails when mandatory schema fields are absent."""
        # The 'package' schema requires both 'name' and 'version'.
        invalid_yaml = """
        package:
          name: "cv-core"
        """
        with self.assertRaises(RecipeParseError) as context:
            parse_recipe_string(invalid_yaml)

        self.assertIn("Recipe Validation Failed", str(context.exception))
        self.assertIn("version", str(context.exception))  # Reports the missing field

    def test_parse_invalid_types(self):
        """Verifies that Pydantic validation fails if fields receive wrong data types."""
        # 'python_dependencies' must be a List of strings, not a raw string.
        invalid_yaml = """
        package:
          name: "cv-core"
          version: "1.0.0"
          python_dependencies: "numpy>=1.21.0"
        """
        with self.assertRaises(RecipeParseError) as context:
            parse_recipe_string(invalid_yaml)

        self.assertIn("Recipe Validation Failed", str(context.exception))
        self.assertIn("python_dependencies", str(context.exception))

    def test_parse_recipe_file_success(self):
        """Verifies that parse_recipe_file successfully reads and parses a valid local file."""
        valid_yaml = """
        package:
          name: "test-package"
          version: "2.0.0"
        """
        # Create a temporary directory/file securely to test local disk parsing
        with tempfile.TemporaryDirectory() as tmp_dir:
            file_path = Path(tmp_dir) / "alloy.yaml"
            file_path.write_text(valid_yaml, encoding="utf-8")

            recipe = parse_recipe_file(file_path)
            self.assertEqual(recipe.package.name, "test-package")
            self.assertEqual(recipe.package.version, "2.0.0")

    def test_parse_recipe_file_not_found(self):
        """Verifies that attempting to parse a nonexistent file yields a clean File Not Found error."""
        nonexistent_path = Path("/nonexistent/directory/structure/alloy.yaml")

        with self.assertRaises(RecipeParseError) as context:
            parse_recipe_file(nonexistent_path)

        self.assertIn("File not found", str(context.exception))


if __name__ == "__main__":
    unittest.main()