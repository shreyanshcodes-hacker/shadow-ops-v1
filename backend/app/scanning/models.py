from enum import Enum


class ScanStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScanProfile(str, Enum):
    CODE_SECURITY = "CODE_SECURITY"
    STANDARD = "STANDARD"
    QUICK = "QUICK"


class ScanEventType(str, Enum):
    SCAN_CREATED = "SCAN_CREATED"
    AUTHORIZATION_CONFIRMED = "AUTHORIZATION_CONFIRMED"
    SCAN_QUEUED = "SCAN_QUEUED"
    SCAN_STARTED = "SCAN_STARTED"
    ANALYSIS_STARTED = "ANALYSIS_STARTED"
    SEMGREP_STARTED = "SEMGREP_STARTED"
    SEMGREP_COMPLETED = "SEMGREP_COMPLETED"
    RESULTS_PARSED = "RESULTS_PARSED"
    EVIDENCE_STORED = "EVIDENCE_STORED"
    SCAN_COMPLETED = "SCAN_COMPLETED"
    SCAN_FAILED = "SCAN_FAILED"
    SCAN_CANCELLED = "SCAN_CANCELLED"


# State machine allowed transitions
VALID_TRANSITIONS = {
    ScanStatus.QUEUED: {ScanStatus.RUNNING, ScanStatus.CANCELLED, ScanStatus.FAILED},
    ScanStatus.RUNNING: {ScanStatus.COMPLETED, ScanStatus.CANCELLED, ScanStatus.FAILED},
    ScanStatus.COMPLETED: set(),
    ScanStatus.FAILED: set(),
    ScanStatus.CANCELLED: set(),
}


def validate_transition(current_status: ScanStatus, new_status: ScanStatus) -> bool:
    return new_status in VALID_TRANSITIONS.get(current_status, set())
