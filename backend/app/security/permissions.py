from typing import List
from app.schemas.workspace import WorkspaceRole

ROLE_PERMISSIONS = {
    WorkspaceRole.OWNER: ["*"],
    WorkspaceRole.ADMIN: [
        "members:manage",
        "assets:manage",
        "assets:authorize",
        "scans:trigger",
        "scans:cancel",
        "findings:view",
        "findings:triage",
        "remediation:approve",
        "reports:generate",
        "audit:view",
    ],
    WorkspaceRole.MEMBER: [
        "assets:create",
        "assets:view",
        "scans:trigger",
        "findings:view",
        "findings:triage",
        "remediation:propose",
        "reports:view",
    ],
    WorkspaceRole.VIEWER: [
        "assets:view",
        "findings:view",
        "reports:view",
    ],
}


def has_permission(role: str, permission: str) -> bool:
    try:
        ws_role = WorkspaceRole(role)
        perms = ROLE_PERMISSIONS.get(ws_role, [])
        return "*" in perms or permission in perms
    except ValueError:
        return False
