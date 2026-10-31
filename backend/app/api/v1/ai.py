import logging
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.profile import Profile
from app.models.finding import Finding
from app.models.asset import Asset
from app.models.attack_path import AttackPath
from app.ai.schemas import (
    FindingAIAnalysisRead,
    AIRunRead,
    TriggerScanAnalysisRequest,
    TriggerFindingAnalysisRequest,
    ScanAnalysisSummaryResponse,
    SecurityChatRequest,
    SecurityChatResponse,
)
from app.ai.provider import get_ai_provider, AIRequestConfig
from app.ai.manager import AISecurityManager
from app.services.ai_analysis_service import AIAnalysisService
from app.security.dependencies import get_current_user
from app.services.workspace_service import WorkspaceService
from app.services.audit_service import AuditService
from app.schemas.audit import AuditEventType
from app.repositories.scan_repo import ScanRepository
from app.repositories.ai_repo import AIRepository

logger = logging.getLogger("shadowops.api.ai")
router = APIRouter(tags=["AI Security Manager & Analyst"])


@router.post("/scans/{scan_id}/ai-analysis", response_model=ScanAnalysisSummaryResponse, status_code=status.HTTP_200_OK)
async def trigger_scan_ai_analysis(
    scan_id: UUID,
    request: Optional[TriggerScanAnalysisRequest] = None,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers structured security analysis via AI Security Manager on findings of an authorized scan.
    Advisory output is evidence-grounded and cannot alter scanner findings or severity.
    """
    scan_repo = ScanRepository(db)
    scan = await scan_repo.get_scan_by_id(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(scan.workspace_id, current_user.id)

    force = request.force if request else False
    max_findings = request.max_findings if request else None

    manager = AISecurityManager(session=db)
    result = await manager.analyze_scan_findings(
        scan=scan,
        force=force,
        max_findings=max_findings,
    )

    audit_service = AuditService(db)
    await audit_service.log(
        workspace_id=scan.workspace_id,
        user_id=current_user.id,
        action=AuditEventType.AI_ANALYSIS_EXECUTED,
        resource_type="scan",
        resource_id=scan.id,
        new_state={
            "ai_run_id": str(result["ai_run_id"]),
            "findings_analyzed": result["findings_analyzed"],
            "findings_skipped_cached": result["findings_skipped_cached"],
        },
    )

    return result


@router.get("/scans/{scan_id}/ai-analysis", response_model=List[FindingAIAnalysisRead])
async def get_scan_ai_analyses(
    scan_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves all AI findings analyses associated with a specific scan.
    """
    scan_repo = ScanRepository(db)
    scan = await scan_repo.get_scan_by_id(scan_id)
    if not scan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scan not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(scan.workspace_id, current_user.id)

    ai_repo = AIRepository(db)
    analyses = await ai_repo.get_analyses_by_scan(scan_id)
    return analyses


@router.get("/findings/{finding_id}/ai-analysis", response_model=List[FindingAIAnalysisRead])
async def list_finding_ai_analyses(
    finding_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves all historical AI analyses for a specific finding (newest first).
    Enforces multi-tenant workspace isolation.
    """
    service = AIAnalysisService(session=db)
    return await service.list_analyses_for_finding(finding_id, current_user)


@router.post("/findings/{finding_id}/ai-analysis", response_model=FindingAIAnalysisRead)
async def trigger_finding_ai_analysis(
    finding_id: UUID,
    request: Optional[TriggerFindingAnalysisRequest] = None,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Triggers structured security analysis for a specific finding via the AI Security Analyst.
    Idempotent: Reuses existing analysis if input hash, provider, model, and prompt version match unless force=True.
    """
    force = request.force if request else False
    provider_override = request.provider if request else None

    service = AIAnalysisService(session=db)
    return await service.analyze_finding(
        finding_id=finding_id,
        current_user=current_user,
        force=force,
        provider_override=provider_override,
    )


@router.get("/ai-analyses/{analysis_id}", response_model=FindingAIAnalysisRead)
async def get_ai_analysis_by_id(
    analysis_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves a specific historical AI analysis record by its ID.
    Enforces multi-tenant workspace isolation.
    """
    service = AIAnalysisService(session=db)
    return await service.get_analysis_by_id(analysis_id, current_user)


@router.get("/ai-runs/{run_id}", response_model=AIRunRead)
async def get_ai_run_details(
    run_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retrieves execution tracking details and token/cost metrics for an AI run.
    """
    ai_repo = AIRepository(db)
    run = await ai_repo.get_agent_run(run_id)
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="AI run not found")

    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(run.workspace_id, current_user.id)

    return run


@router.post("/ai/chat", response_model=SecurityChatResponse, status_code=status.HTTP_200_OK)
async def security_chat(
    request: SecurityChatRequest,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Conversational AI Security Analyst (ShadowOps Sentinel).
    Answers questions grounded in workspace assets, findings, and attack paths.
    """
    ws_service = WorkspaceService(db)
    await ws_service.get_workspace(request.workspace_id, current_user.id)

    # Gather grounded context
    f_stmt = (
        select(Finding)
        .where(Finding.workspace_id == request.workspace_id)
        .order_by(Finding.created_at.desc())
        .limit(10)
    )
    f_res = await db.execute(f_stmt)
    findings = list(f_res.scalars().all())

    a_stmt = select(Asset).where(Asset.workspace_id == request.workspace_id).limit(10)
    a_res = await db.execute(a_stmt)
    assets = list(a_res.scalars().all())

    ap_stmt = (
        select(AttackPath)
        .where(AttackPath.workspace_id == request.workspace_id)
        .order_by(AttackPath.risk_score.desc())
        .limit(5)
    )
    ap_res = await db.execute(ap_stmt)
    attack_paths = list(ap_res.scalars().all())

    grounded_context = {
        "workspace_id": str(request.workspace_id),
        "total_active_assets": len(assets),
        "asset_names": [a.name for a in assets],
        "recent_findings_count": len(findings),
        "recent_findings": [
            {"id": str(f.id), "title": f.title, "severity": f.severity, "cwe_ids": f.cwe_ids, "status": f.status}
            for f in findings[:5]
        ],
        "attack_paths_count": len(attack_paths),
        "top_attack_paths": [
            {
                "id": str(ap.id),
                "title": ap.title or ap.name,
                "risk_score": float(ap.risk_score) if ap.risk_score is not None else 0.0,
                "risk_band": ap.risk_band,
                "entry_point": ap.entry_point,
                "target_asset": ap.target_asset,
            }
            for ap in attack_paths[:3]
        ],
    }

    # Build prompt with history
    system_instruction = (
        "You are ShadowOps Sentinel, an expert AI application security consultant embedded in the user's DevSecOps team.\n"
        "Your mission is to provide defensive, actionable, and mathematically grounded cybersecurity guidance.\n"
        "RULES:\n"
        "1. Never provide offensive attack payloads, weaponized exploit code, or harmful instructions.\n"
        "2. Ground your advice in the user's workspace telemetry and standard CWE/OWASP frameworks.\n"
        "3. Explain root causes clearly with before/after secure code remediation examples when applicable.\n"
        "4. Keep your responses clear, structured (using Markdown headers and bullet points), and professional."
    )

    ap_summary = (
        ", ".join(
            f"{ap.title or ap.name} (Score: {float(ap.risk_score):.1f}, Band: {ap.risk_band}, Entry: {ap.entry_point or 'External'})"
            for ap in attack_paths[:3]
        )
        if attack_paths
        else "No synthesized attack paths recorded yet"
    )

    context_str = (
        f"Workspace Context:\n"
        f"- Assets: {', '.join(grounded_context['asset_names']) if assets else 'No assets recorded'}\n"
        f"- Open Findings: {len(findings)} findings recorded. Top: {', '.join(f.title for f in findings[:3]) if findings else 'None'}\n"
        f"- Attack Paths: {ap_summary}\n"
    )

    history_str = ""
    for msg in request.history[-6:]:
        history_str += f"{msg.role.upper()}: {msg.content}\n"

    full_prompt = f"{context_str}\n{history_str}USER: {request.message}\nASSISTANT:"

    provider = get_ai_provider()
    cfg = AIRequestConfig(timeout_seconds=12, max_retries=1)
    try:
        ai_res = await provider.generate_text(
            prompt=full_prompt,
            system_instruction=system_instruction,
            config=cfg,
        )
        reply = ai_res.content
    except Exception as e:
        logger.error(f"Chat generation failed: {e}")
        if hasattr(provider, "_mock_text_response"):
            fallback_res = provider._mock_text_response(request.message, "gemini-sentinel")
            reply = fallback_res.content
        else:
            reply = (
                "### ShadowOps Sentinel Advisory\n\n"
                "I have evaluated your workspace telemetry. "
                f"Active Assets: **{len(assets)}** | Recorded Findings: **{len(findings)}** | "
                f"Synthesized Attack Paths: **{len(attack_paths)}**.\n\n"
                "- Review the **Attack Paths** and **Findings** views for deterministic risk breakdowns and remediation diffs."
            )

    suggested_actions = [
        "Analyze latest critical vulnerabilities",
        "How do I fix SQL injection in our code?",
        "What is our highest risk attack path?",
        "Generate remediation proposal",
    ]

    return SecurityChatResponse(
        reply=reply,
        provider=provider.provider_name,
        grounded_context=grounded_context,
        suggested_actions=suggested_actions,
    )
