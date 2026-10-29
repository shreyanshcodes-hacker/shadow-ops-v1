import asyncio
from pathlib import Path
from typing import List, Optional
from app.scanning.semgrep import ScannerAdapter, SemgrepAdapter
from app.scanning.parser import NormalizedScanFinding


class ScanJobRunner:
    """
    Coordinates scanner execution with lifecycle timeouts, process isolation,
    and cancellation handling.
    """

    def __init__(self, adapter: Optional[ScannerAdapter] = None):
        self.adapter = adapter or SemgrepAdapter()

    async def execute_scan(self, target_path: Path, timeout_seconds: int = 60) -> List[NormalizedScanFinding]:
        return await self.adapter.scan(target_path, timeout_seconds=timeout_seconds)

    async def cancel(self) -> None:
        await self.adapter.cancel()
