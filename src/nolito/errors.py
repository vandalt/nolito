class NolitoError(Exception):
    """Base exception for this package."""


class OAuthFlowError(NolitoError):
    """Raised for OAuth-specific failures."""


class NolioApiError(NolitoError):
    """Raised when Nolio API returns an error or unexpected response."""
