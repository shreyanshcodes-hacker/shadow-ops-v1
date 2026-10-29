import re
import hashlib
from typing import List, Dict, Any, Tuple, Optional
from dataclasses import dataclass, field


MAX_DIFF_BYTES = 64 * 1024  # 64 KB
MAX_AFFECTED_FILES = 5

# Blocked sensitive path patterns that automated patches must NEVER touch
FORBIDDEN_PATH_PATTERNS = [
    re.compile(r"(^|/)\.env(\..+)?$", re.IGNORECASE),
    re.compile(r"(^|/)\.git(/|$)", re.IGNORECASE),
    re.compile(r"\.(pem|key|pkcs12|pfx|crt|cer|der|jks|kdbx)$", re.IGNORECASE),
    re.compile(r"(^|/)(credentials|secrets|passwords?|tokens?)\.(json|ya?ml|toml|txt|py|js)$", re.IGNORECASE),
    re.compile(r"(^|/)migrations?(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)supabase/migrations(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)alembic(/|$)", re.IGNORECASE),
    re.compile(r"(^|/)(\.github|docker-compose|dockerfile|railway\.json|procfile|k8s|helm)(/|$)", re.IGNORECASE),
]


@dataclass
class DiffHunk:
    header: str
    old_start: int
    old_length: int
    new_start: int
    new_length: int
    lines: List[str]


@dataclass
class FileDiff:
    old_path: str
    new_path: str
    relative_path: str
    additions: int = 0
    deletions: int = 0
    hunks: List[DiffHunk] = field(default_factory=list)


@dataclass
class ParsedDiff:
    raw_diff: str
    patch_hash: str
    files: List[FileDiff]
    total_additions: int
    total_deletions: int
    is_safe: bool
    safety_violations: List[str]


class PatchSecurityException(Exception):
    """Raised when a proposed patch violates safety boundaries."""
    pass


class PatchProcessor:
    """
    Dedicated patch-processing service enforcing strict isolation, path traversal defense,
    binary patch rejection, sensitive path blocklisting, and canonical SHA-256 integrity binding.
    """

    @staticmethod
    def canonicalize_diff(diff_text: str) -> str:
        """Normalize line endings and strip trailing whitespace for deterministic hashing."""
        lines = [line.rstrip() for line in diff_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")]
        # Remove trailing empty lines
        while lines and not lines[-1]:
            lines.pop()
        return "\n".join(lines) + "\n" if lines else ""

    @staticmethod
    def compute_patch_hash(diff_text: str) -> str:
        """Compute SHA-256 hash of canonicalized unified diff."""
        canonical = PatchProcessor.canonicalize_diff(diff_text)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def validate_file_path(path: str) -> Tuple[bool, Optional[str]]:
        """Validate relative repository path against directory traversal, absolute escapes, and sensitive files."""
        clean_path = path.replace("\\", "/").strip()

        # Reject empty
        if not clean_path:
            return False, "Empty file path is not allowed"

        # Reject absolute paths (POSIX / or Windows C:)
        if clean_path.startswith("/") or re.match(r"^[a-zA-Z]:", clean_path):
            return False, f"Absolute file path escape detected: {path}"

        # Reject path traversal (e.g., ../ or /../)
        parts = clean_path.split("/")
        if ".." in parts or "." in parts:
            return False, f"Directory traversal pattern detected in path: {path}"

        # Reject null bytes or control characters
        if "\x00" in path or any(ord(c) < 32 for c in path):
            return False, f"Path contains illegal control characters: {path}"

        # Check against forbidden sensitive system and credential files
        for pattern in FORBIDDEN_PATH_PATTERNS:
            if pattern.search(clean_path):
                return False, f"Modification of sensitive or privileged file blocked by security policy: {clean_path}"

        return True, None

    @classmethod
    def parse_and_validate(cls, diff_text: str, declared_files: Optional[List[str]] = None) -> ParsedDiff:
        """
        Parse unified diff, validate all safety constraints, and return structured ParsedDiff.
        Throws PatchSecurityException if severe invariant is violated.
        """
        violations: List[str] = []

        if not diff_text or not diff_text.strip():
            raise PatchSecurityException("Diff content cannot be empty")

        canonical_diff = cls.canonicalize_diff(diff_text)
        diff_bytes = len(canonical_diff.encode("utf-8"))

        if diff_bytes > MAX_DIFF_BYTES:
            violations.append(f"Diff size ({diff_bytes} bytes) exceeds safety maximum ({MAX_DIFF_BYTES} bytes)")

        # Reject binary diffs
        if "GIT binary patch" in canonical_diff or "Binary files " in canonical_diff:
            violations.append("Binary patches are strictly forbidden; only text diffs are accepted")

        patch_hash = cls.compute_patch_hash(canonical_diff)

        # Parse files and hunks
        file_diffs: List[FileDiff] = []
        current_file: Optional[FileDiff] = None
        current_hunk: Optional[DiffHunk] = None
        total_adds = 0
        total_dels = 0

        lines = canonical_diff.split("\n")
        i = 0
        while i < len(lines):
            line = lines[i]

            # Detect file header: --- a/path and +++ b/path
            if line.startswith("--- "):
                old_p = line[4:].strip()
                if i + 1 < len(lines) and lines[i + 1].startswith("+++ "):
                    new_p = lines[i + 1][4:].strip()
                    i += 1  # advance past +++

                    # Normalize paths (strip a/ and b/ prefixes)
                    clean_old = re.sub(r"^[ab]/", "", old_p)
                    clean_new = re.sub(r"^[ab]/", "", new_p)
                    target_rel_path = clean_new if clean_new != "/dev/null" else clean_old

                    # Validate path safety
                    is_valid, reason = cls.validate_file_path(target_rel_path)
                    if not is_valid:
                        violations.append(reason)

                    current_file = FileDiff(
                        old_path=clean_old,
                        new_path=clean_new,
                        relative_path=target_rel_path,
                    )
                    file_diffs.append(current_file)
                    current_hunk = None
                    i += 1
                    continue

            # Detect hunk header: @@ -old_start,old_len +new_start,new_len @@
            if line.startswith("@@ ") and current_file:
                hunk_match = re.match(r"^@@\s+-(\d+)(?:,(\d+))?\s+\+(\d+)(?:,(\d+))?\s+@@(.*)$", line)
                if hunk_match:
                    old_start = int(hunk_match.group(1))
                    old_len = int(hunk_match.group(2)) if hunk_match.group(2) else 1
                    new_start = int(hunk_match.group(3))
                    new_len = int(hunk_match.group(4)) if hunk_match.group(4) else 1
                    current_hunk = DiffHunk(
                        header=line,
                        old_start=old_start,
                        old_length=old_len,
                        new_start=new_start,
                        new_length=new_len,
                        lines=[],
                    )
                    current_file.hunks.append(current_hunk)
                    i += 1
                    continue

            # Count additions and deletions in hunk
            if current_hunk:
                if line.startswith("+") and not line.startswith("+++"):
                    total_adds += 1
                    if current_file:
                        current_file.additions += 1
                    current_hunk.lines.append(line)
                elif line.startswith("-") and not line.startswith("---"):
                    total_dels += 1
                    if current_file:
                        current_file.deletions += 1
                    current_hunk.lines.append(line)
                elif line.startswith(" ") or line == "":
                    current_hunk.lines.append(line)

            i += 1

        if not file_diffs:
            violations.append("Malformed unified diff: no standard file headers (--- a/..., +++ b/...) found")

        if len(file_diffs) > MAX_AFFECTED_FILES:
            violations.append(f"Affected files count ({len(file_diffs)}) exceeds maximum allowed ({MAX_AFFECTED_FILES})")

        # Validate against declared files if supplied
        if declared_files:
            diff_paths = {f.relative_path for f in file_diffs}
            for declared in declared_files:
                clean_decl = declared.replace("\\", "/").strip()
                if clean_decl not in diff_paths:
                    violations.append(f"Diff does not contain expected changes for declared file: {declared}")

        is_safe = len(violations) == 0

        if not is_safe and any(
            "directory traversal" in v.lower()
            or "sensitive" in v.lower()
            or "escape" in v.lower()
            or "forbidden" in v.lower()
            for v in violations
        ):
            raise PatchSecurityException("; ".join(violations))

        return ParsedDiff(
            raw_diff=canonical_diff,
            patch_hash=patch_hash,
            files=file_diffs,
            total_additions=total_adds,
            total_deletions=total_dels,
            is_safe=is_safe,
            safety_violations=violations,
        )
