class RegistryError(Exception):
    """
    Base exception for all Alloy registry API errors.
    """
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


class PackageNotFoundError(RegistryError):
    """
    Raised when a requested package is not found in the remote registry (HTTP 404).
    """
    def __init__(self, package_name: str, message: str = None):
        msg = message or f"Package '{package_name}' could not be found in the remote registry."
        super().__init__(msg, status_code=404)
        self.package_name = package_name


class RateLimitExceededError(RegistryError):
    """
    Raised when the client exceeds the API server's rate limits (HTTP 429).
    """
    def __init__(self, message: str = "Rate limit exceeded. Please wait a few moments and try again."):
        super().__init__(message, status_code=429)


class UnauthorizedError(RegistryError):
    """
    Raised when the client is unauthorized to access the requested registry resource (HTTP 401/403).
    Useful for private enterprise registries in the future.
    """
    def __init__(self, message: str = "Access denied. Please check your credentials or auth token."):
        super().__init__(message, status_code=403)


class APIServerError(RegistryError):
    """
    Raised when the remote registry server encounters an internal error (HTTP 5xx).
    """
    def __init__(self, message: str = "Internal registry server error. Please try again later.", status_code: int = 500):
        super().__init__(message, status_code=status_code)


class APIConnectionError(RegistryError):
    """
    Raised when the client fails to connect to the remote registry server
    (timeouts, offline states, DNS issues).
    """
    def __init__(self, message: str = "Failed to establish a connection to the remote registry server."):
        super().__init__(message, status_code=None)


class APIValidationError(RegistryError):
    """
    Raised when the API returns a bad payload (HTTP 400) or when
    the client fails to parse a structurally corrupt server response.
    """
    def __init__(self, message: str):
        super().__init__(message, status_code=400)


# ==========================================
# Self-Test Block
# ==========================================
if __name__ == "__main__":
    print("--- Running Registry Exceptions Self-Test ---")

    # Verify catching hierarchical structures works cleanly
    try:
        raise PackageNotFoundError("hypocv")
    except RegistryError as err:
        print("✅ Correctly caught a subclassed RegistryError!")
        print(f"   Status Code: {err.status_code}")
        print(f"   Message:     {err.message}")