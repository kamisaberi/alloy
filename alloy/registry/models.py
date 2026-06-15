from typing import List, Optional
from pydantic import BaseModel, Field


class PackageSummary(BaseModel):
    """
    Represents a simplified package definition. Used in search results
    and lightweight registry index listings.
    """
    name: str = Field(..., min_length=1, description="Unique name of the package")
    version: str = Field(..., description="Latest or matched version of the package")
    description: Optional[str] = Field(None, description="Brief summary of the package's purpose")


class SearchResponse(BaseModel):
    """
    Structure of the JSON payload returned by a GET /v1/search request.
    """
    query: str = Field(..., description="The original search query parameter")
    total_results: int = Field(..., description="Total count of matching packages in the registry")
    results: List[PackageSummary] = Field(
        default_factory=list,
        description="The matching packages found"
    )


class PackageDetails(BaseModel):
    """
    Structure of the detailed JSON payload returned by a GET /v1/packages/{name} request.
    Allows the CLI to list package history, homepage URLs, and maintainer details.
    """
    name: str = Field(..., min_length=1, description="Unique name of the package")
    latest_version: str = Field(..., description="Latest available version in the registry")
    versions: List[str] = Field(
        default_factory=list,
        description="List of all registered versions for this package"
    )
    description: Optional[str] = Field(None, description="Detailed package description")
    author: Optional[str] = Field(None, description="Name of the package maintainer or author")
    homepage: Optional[str] = Field(None, description="URL to the package's repository or homepage")


class RegistryIndex(BaseModel):
    """
    Structure of the index JSON payload downloaded locally during 'alloy update'
    to allow lightning-fast offline autocomplete and searching.
    """
    last_updated: str = Field(..., description="Timestamp of when the registry index was last built")
    packages: List[PackageSummary] = Field(
        default_factory=list,
        description="Complete collection of all packages in the registry"
    )


# ==========================================
# Self-Test Block
# ==========================================
if __name__ == "__main__":
    import json

    print("--- Running Registry Models Self-Test ---")

    # Mock an API response for a package details query
    mock_details_json = """
    {
        "name": "hypocv",
        "latest_version": "1.2.0",
        "versions": ["1.0.0", "1.1.0", "1.2.0"],
        "description": "API-driven mock vision wrappers.",
        "author": "Alloy Team",
        "homepage": "https://github.com/alloy-pm/hypocv"
    }
    """

    try:
        # Validate JSON serialization using the PackageDetails model
        details = PackageDetails.model_validate_json(mock_details_json)
        print("✅ PackageDetails validated successfully!")
        print(f"Name:     {details.name}")
        print(f"Latest:   {details.latest_version}")
        print(f"Versions: {details.versions}")
    except Exception as e:
        print(f"❌ Validation failed: {e}")