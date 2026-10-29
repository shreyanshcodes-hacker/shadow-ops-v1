import hashlib
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class SemgrepConfig(BaseModel):
    rulesets: List[str] = Field(default_factory=lambda: ["p/security-audit", "p/secrets", "p/owasp-top-ten"])
    timeout_seconds: int = 600
    max_target_size_mb: int = 1000
    target_path: str = "/tmp/sandbox"
    output_format: str = "json"


class SemgrepRawMatch(BaseModel):
    check_id: str
    path: str
    start_line: int
    end_line: int
    extra: Dict[str, Any] = Field(default_factory=dict)


class SemgrepResult(BaseModel):
    exit_code: int
    raw_output: Dict[str, Any] = Field(default_factory=dict)
    matches: List[SemgrepRawMatch] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    execution_time_ms: int = 0


class SemgrepRunner:
    """
    Integration boundary for Semgrep execution.
    Prepares parameters, sandbox directory constraints, and execution boundaries.
    Does NOT execute external processes in Stage 1.
    """
    def __init__(self, config: Optional[SemgrepConfig] = None):
        self.config = config or SemgrepConfig()

    def build_command(self, target_directory: str) -> List[str]:
        cmd = ["semgrep", "scan", "--json"]
        for ruleset in self.config.rulesets:
            cmd.extend(["--config", ruleset])
        cmd.append(target_directory)
        return cmd

    async def execute_mock(self, target_path: str) -> SemgrepResult:
        """Controlled boundary stub for unit testing without live CLI dependencies."""
        return SemgrepResult(
            exit_code=0,
            raw_output={"results": []},
            matches=[],
            errors=[],
            execution_time_ms=150,
        )
