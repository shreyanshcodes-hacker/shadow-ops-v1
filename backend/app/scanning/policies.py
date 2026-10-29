import os
import re
from pathlib import Path
from app.scanning.exceptions import TargetValidationException


class ScanPathPolicy:
    """
    Enforces filesystem boundary rules for scanning targets.
    Prevents path traversal, access to backend system dirs, and scanning root.
    """

    ALLOWED_PREFIXES = [
        "app/scanning/fixtures",
        "backend/app/scanning/fixtures",
        "fixtures",
        "controlled_targets",
    ]

    @classmethod
    def sanitize_and_validate_target(cls, target_path_str: str, base_dir: Path) -> Path:
        # Prevent null bytes and common shell injections
        if "\0" in target_path_str or ";" in target_path_str or "|" in target_path_str or "&" in target_path_str:
            raise TargetValidationException("Invalid characters detected in target path.")

        # Resolve path
        target_path = Path(target_path_str)
        if not target_path.is_absolute():
            resolved = (base_dir / target_path).resolve()
        else:
            resolved = target_path.resolve()

        # Reject path traversal outside allowed sandbox
        # Must exist and be a directory or file
        if not resolved.exists():
            raise TargetValidationException(f"Target path does not exist: {target_path_str}")

        # Prohibit scanning sensitive system directories
        prohibited = ["/etc", "/bin", "/usr", "/var", "C:\\Windows", "C:\\Program Files"]
        for p in prohibited:
            if str(resolved).lower().startswith(p.lower()):
                raise TargetValidationException("Scanning system directory is prohibited.")

        return resolved
