import asyncio
import os
import sys
import uuid
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.core.config import settings
from app.db.session import async_session_maker
from app.models.profile import Profile
from app.models.workspace import Workspace, WorkspaceMember
from app.models.asset import Asset, AssetAuthorization
from app.models.scan import Scan, ScanEvent, AgentRun
from app.models.finding import Finding, FindingEvidence, FindingAIAnalysis
from app.models.security_relationship import SecurityRelationship
from app.models.attack_path import AttackPath, AttackPathNode, AttackPathEdge, RiskSnapshot
from app.models.security_team import SecurityTeamRun

async def seed():
    async with async_session_maker() as session:
        print("Checking if local user already exists...")
        from sqlalchemy import select
        stmt = select(Profile).where(Profile.email == "operator@shadowops.io")
        res = await session.execute(stmt)
        existing_profile = res.scalar_one_or_none()

        if existing_profile:
            print("Local data already seeded. Skipping seed.")
            return

        print("Seeding local operator profile...")
        profile_id = uuid.uuid4()
        profile = Profile(
            id=profile_id,
            firebase_uid="local-dev-user",
            email="operator@shadowops.io",
            display_name="Security Lead (Local)",
            role="admin",
            last_login_at=datetime.now(timezone.utc),
        )
        session.add(profile)

        print("Seeding local development workspace...")
        workspace_id = uuid.uuid4()
        workspace = Workspace(
            id=workspace_id,
            name="ShadowOps Core Ops",
            slug="shadowops-core",
            owner_id=profile_id,
            plan="enterprise",
        )
        session.add(workspace)

        member = WorkspaceMember(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            user_id=profile_id,
            role="owner",
        )
        session.add(member)

        print("Seeding authorized perimeter assets...")
        asset_id = uuid.uuid4()
        asset = Asset(
            id=asset_id,
            workspace_id=workspace_id,
            name="Payments & Billing API",
            type="repository",
            subtype="github",
            criticality="critical",
            status="active",
            created_by=profile_id,
            connection_config={"identifier": "github.com/shadowops/payments-service"},
            tags=["production", "pci-dss", "core-api"],
            last_scanned_at=datetime.now(timezone.utc),
        )
        session.add(asset)

        authz = AssetAuthorization(
            id=uuid.uuid4(),
            asset_id=asset_id,
            workspace_id=workspace_id,
            authorization_type="ownership",
            status="verified",
            verified_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=180),
        )
        session.add(authz)

        # Asset 2: Auth Service
        asset2_id = uuid.uuid4()
        asset2 = Asset(
            id=asset2_id,
            workspace_id=workspace_id,
            name="Customer Identity Service",
            type="repository",
            subtype="github",
            criticality="high",
            status="active",
            created_by=profile_id,
            connection_config={"identifier": "github.com/shadowops/auth-service"},
            tags=["production", "oauth2", "iam"],
            last_scanned_at=datetime.now(timezone.utc),
        )
        session.add(asset2)

        authz2 = AssetAuthorization(
            id=uuid.uuid4(),
            asset_id=asset2_id,
            workspace_id=workspace_id,
            authorization_type="ownership",
            status="verified",
            verified_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(days=180),
        )
        session.add(authz2)

        print("Seeding completed scan and findings...")
        scan_id = uuid.uuid4()
        scan = Scan(
            id=scan_id,
            workspace_id=workspace_id,
            asset_id=asset_id,
            scan_type="code",
            status="completed",
            triggered_by=profile_id,
            started_at=datetime.now(timezone.utc) - timedelta(minutes=15),
            completed_at=datetime.now(timezone.utc) - timedelta(minutes=12),
        )
        session.add(scan)

        # Finding 1: SQL Injection
        f1_id = uuid.uuid4()
        f1 = Finding(
            id=f1_id,
            workspace_id=workspace_id,
            scan_id=scan_id,
            asset_id=asset_id,
            source="semgrep",
            source_rule_id="semgrep.python.sqlalchemy.sqli-injection",
            title="Raw SQL Parameter Concatenation in Billing Query",
            description="Untrusted user input interpolated directly into SQL execute statement without parameterized binding.",
            severity="critical",
            confidence="high",
            cwe_ids=["CWE-89"],
            owasp_categories=["A03:2021"],
            code_snippet="query = f'SELECT balance, status FROM accounts WHERE customer_id = {customer_id}'\ncursor.execute(query)",
            location={"file": "billing/accounts.py", "start_line": 54, "end_line": 57},
            status="open",
        )
        session.add(f1)

        ev1 = FindingEvidence(
            id=uuid.uuid4(),
            finding_id=f1_id,
            workspace_id=workspace_id,
            evidence_type="ast_match",
            title="Raw String Formatted SQL Query",
            file_path="billing/accounts.py",
            line_start=54,
            line_end=57,
            content={"snippet": "cursor.execute(query)", "untrusted_var": "customer_id"},
        )
        session.add(ev1)

        # Finding 2: Hardcoded Secret
        f2_id = uuid.uuid4()
        f2 = Finding(
            id=f2_id,
            workspace_id=workspace_id,
            scan_id=scan_id,
            asset_id=asset_id,
            source="semgrep",
            source_rule_id="semgrep.generic.secrets.hardcoded-jwt-secret",
            title="Static JWT Signing Secret Key in Configuration",
            description="High-entropy JWT secret key embedded in source code, permitting unauthorized token forgery.",
            severity="high",
            confidence="high",
            cwe_ids=["CWE-798"],
            owasp_categories=["A07:2021"],
            code_snippet="JWT_SECRET_KEY = 'shadowops_live_production_jwt_signing_key_9982'",
            location={"file": "config/security.py", "start_line": 18, "end_line": 18},
            status="open",
        )
        session.add(f2)

        ev2 = FindingEvidence(
            id=uuid.uuid4(),
            finding_id=f2_id,
            workspace_id=workspace_id,
            evidence_type="regex_match",
            title="Embedded JWT Secret",
            file_path="config/security.py",
            line_start=18,
            line_end=18,
            content={"matched_rule": "hardcoded-jwt-secret"},
        )
        session.add(ev2)

        print("Seeding security relationship and attack path...")
        rel = SecurityRelationship(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            source_finding_id=f2_id,
            target_finding_id=f1_id,
            relationship_type="ENABLES",
            confidence=0.92,
            source="DETERMINISTIC",
            status="active",
            rationale="Forged JWT token grants attacker unauthenticated access to the billing endpoint containing the SQL injection vulnerability.",
        )
        session.add(rel)

        path_id = uuid.uuid4()
        path = AttackPath(
            id=path_id,
            workspace_id=workspace_id,
            scan_id=scan_id,
            name="Forged Token to Database Compromise",
            title="Forged Token to Database Compromise",
            description="Attacker leverages hardcoded JWT secret to sign arbitrary authorization claims, accessing the internal billing handler to execute arbitrary SQL.",
            entry_point="config/security.py",
            target_asset="Payments & Billing API",
            risk_score=87.5,
            risk_band="CRITICAL",
            confidence=0.95,
            node_count=2,
            edge_count=1,
            is_critical=True,
            status="active",
            factors={
                "critical_findings": 1,
                "high_findings": 1,
                "asset_criticality": "critical",
                "risk_multiplier": 1.25,
            },
            model_version="risk-v1",
        )
        session.add(path)

        node1 = AttackPathNode(
            id=uuid.uuid4(),
            attack_path_id=path_id,
            workspace_id=workspace_id,
            node_type="vulnerability",
            node_order=0,
            label="Forged JWT Authorization",
            description="Attacker creates valid admin JWT using extracted secret",
            finding_id=f2_id,
            risk_contribution=35.0,
        )
        node2 = AttackPathNode(
            id=uuid.uuid4(),
            attack_path_id=path_id,
            workspace_id=workspace_id,
            node_type="vulnerability",
            node_order=1,
            label="SQL Injection Database Extraction",
            description="Attacker executes arbitrary queries against billing database",
            finding_id=f1_id,
            risk_contribution=52.5,
        )
        session.add_all([node1, node2])

        edge1 = AttackPathEdge(
            id=uuid.uuid4(),
            attack_path_id=path_id,
            workspace_id=workspace_id,
            source_node_id=node1.id,
            target_node_id=node2.id,
            edge_type="exploits",
            description="Valid forged token authorizes request to billing endpoint",
            evidence_refs=["config/security.py", "billing/accounts.py"],
            likelihood=0.90,
        )
        session.add(edge1)

        print("Seeding AI Security Team Run evaluation...")
        team_run = SecurityTeamRun(
            id=uuid.uuid4(),
            workspace_id=workspace_id,
            asset_id=asset_id,
            scan_id=scan_id,
            status="SUCCEEDED",
            requested_by=profile_id,
            orchestration_version="security-team-v1",
            confidence=0.92,
            team_summary={
                "review_status": "AI ANALYSIS COMPLETE - HUMAN REVIEW REQUIRED",
                "executive_summary": "The AI Security Team has identified a critical multi-step exploit path in Payments & Billing API. An attacker can forge JWT tokens via embedded secrets to reach an unparameterized SQL query sink, achieving unauthorized data access.",
                "highest_priority_findings": [
                    "Raw SQL Parameter Concatenation in Billing Query (CWE-89)",
                    "Static JWT Signing Secret Key in Configuration (CWE-798)",
                ],
                "highest_priority_attack_paths": [
                    "Forged Token to Database Compromise (Score: 87.5 / 100 • CRITICAL)",
                ],
                "risk_interpretation": "Deterministic risk engine (risk-v1) scored 87.5/100 (CRITICAL) driven by production asset criticality, compound vulnerability exploitability, and direct database access.",
                "recommended_human_actions": [
                    "Immediately revoke and rotate static JWT signing secret in production",
                    "Migrate raw cursor.execute() queries in billing/accounts.py to parameterized ORM queries",
                    "Verify network egress filtering on billing datastore",
                ],
            },
            started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            completed_at=datetime.now(timezone.utc) - timedelta(minutes=8),
        )
        session.add(team_run)

        # Agent runs for all 5 specialized agents
        recon_run = AgentRun(
            id=uuid.uuid4(),
            team_run_id=team_run.id,
            workspace_id=workspace_id,
            agent_name="recon",
            status="SUCCEEDED",
            confidence=0.90,
            output={
                "relevant_components": ["billing", "config", "api"],
                "entry_points": ["/api/v1/billing/balance", "/api/v1/auth/token"],
                "security_boundaries": ["JWT Verification Barrier", "Database Layer"],
                "exposed_areas": ["Customer Billing API"],
            },
            tokens_input=240,
            tokens_output=120,
            model_used="gemini-1.5-flash",
            prompt_version="recon-v1",
        )
        vuln_run = AgentRun(
            id=uuid.uuid4(),
            team_run_id=team_run.id,
            workspace_id=workspace_id,
            agent_name="vulnerability_analyst",
            status="SUCCEEDED",
            confidence=0.95,
            output={
                "findings_analyzed": 2,
                "interpretations": [
                    {
                        "finding_id": str(f1_id),
                        "vulnerability_interpretation": "Classic SQL injection via raw f-string concatenation",
                        "preconditions": "Attacker must reach endpoint with custom customer_id query parameter",
                        "potential_impact": "Full database read/write access and credential dumping",
                    }
                ],
            },
            tokens_input=380,
            tokens_output=190,
            model_used="gemini-1.5-pro",
            prompt_version="vulnerability-analyst-v1",
        )
        path_run = AgentRun(
            id=uuid.uuid4(),
            team_run_id=team_run.id,
            workspace_id=workspace_id,
            agent_name="attack_path",
            status="SUCCEEDED",
            confidence=0.92,
            output={
                "path_observations": ["Hardcoded credential directly enables authentication bypass to SQL sink"],
                "candidate_relationships": [{"type": "ENABLES", "source": "JWT Secret", "target": "SQLi"}],
            },
            tokens_input=310,
            tokens_output=150,
            model_used="gemini-1.5-pro",
            prompt_version="attack-path-v1",
        )
        risk_run = AgentRun(
            id=uuid.uuid4(),
            team_run_id=team_run.id,
            workspace_id=workspace_id,
            agent_name="risk_analyst",
            status="SUCCEEDED",
            confidence=0.90,
            output={
                "deterministic_score_reference": 87.5,
                "risk_band": "CRITICAL",
                "important_contributing_factors": [
                    "Production payment asset (+30 pts)",
                    "Critical SQL injection (+30 pts)",
                    "Direct exploit path multiplier (1.25x)",
                ],
            },
            tokens_input=290,
            tokens_output=140,
            model_used="gemini-1.5-flash",
            prompt_version="risk-analyst-v1",
        )
        rev_run = AgentRun(
            id=uuid.uuid4(),
            team_run_id=team_run.id,
            workspace_id=workspace_id,
            agent_name="security_reviewer",
            status="SUCCEEDED",
            confidence=0.94,
            output={
                "review_status": "AI ANALYSIS COMPLETE - HUMAN REVIEW REQUIRED",
                "consensus_reached": True,
                "highest_risk": "Database compromise via forged JWT token",
            },
            tokens_input=450,
            tokens_output=210,
            model_used="gemini-1.5-pro",
            prompt_version="security-reviewer-v1",
        )
        session.add_all([recon_run, vuln_run, path_run, risk_run, rev_run])

        await session.commit()
        print("Local data seeded successfully!")
        print(f"  User: operator@shadowops.io (UID: local-dev-user)")
        print(f"  Workspace: ShadowOps Core Ops (ID: {workspace_id})")
        print(f"  Asset: Payments & Billing API (ID: {asset_id})")
        print(f"  Attack Path: Forged Token to Database Compromise (Score: 87.5 / CRITICAL)")
        print(f"  AI Security Team Run: {team_run.id}")

if __name__ == "__main__":
    asyncio.run(seed())
