from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.auth import router as auth_router
from app.api.v1.workspaces import router as workspaces_router
from app.api.v1.assets import router as assets_router
from app.api.v1.scans import router as scans_router
from app.api.v1.findings import router as findings_router
from app.api.v1.ai import router as ai_router
from app.api.v1.attack_paths import router as attack_paths_router
from app.api.v1.relationships import router as relationships_router
from app.api.v1.security_team import router as security_team_router
from app.api.v1.remediations import router as remediations_router
from app.api.v1.verifications import router as verifications_router
from app.api.v1.reports import router as reports_router
from app.api.v1.notifications import router as notifications_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(auth_router)
api_router.include_router(workspaces_router)
api_router.include_router(assets_router)
api_router.include_router(scans_router)
api_router.include_router(findings_router)
api_router.include_router(ai_router)
api_router.include_router(attack_paths_router)
api_router.include_router(relationships_router)
api_router.include_router(security_team_router)
api_router.include_router(remediations_router)
api_router.include_router(verifications_router)
api_router.include_router(reports_router)
api_router.include_router(notifications_router)
