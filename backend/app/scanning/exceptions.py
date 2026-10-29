class ScannerException(Exception):
    """Base exception for scanning operations."""
    pass


class TargetValidationException(ScannerException):
    """Raised when scan target path or structure violates security boundaries."""
    pass


class ScanAuthorizationException(ScannerException):
    """Raised when an asset does not have valid, unexpired scan authorization."""
    pass


class StateTransitionException(ScannerException):
    """Raised when an invalid scan lifecycle state transition is attempted."""
    pass


class SemgrepExecutionException(ScannerException):
    """Raised when Semgrep process fails, times out, or returns invalid output."""
    pass
