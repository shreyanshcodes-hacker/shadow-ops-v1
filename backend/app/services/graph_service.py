"""
Attack Path Builder & Graph Service

Constructs directed attack paths from security relationships,
enforces graph safety bounds (cycle prevention, max node limit),
and coordinates deterministic risk scoring via RiskEngine.
"""

import uuid
from typing import List, Dict, Any, Optional, Set
from collections import defaultdict
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import Finding
from app.models.security_relationship import SecurityRelationship
from app.models.attack_path import AttackPath, AttackPathNode, AttackPathEdge, RiskSnapshot
from app.models.asset import Asset
from app.services.risk_engine import RiskEngine

MAX_ATTACK_PATH_NODES = 8


class GraphService:
    @staticmethod
    def detect_cycles(adj: Dict[uuid.UUID, List[uuid.UUID]]) -> bool:
        """
        Check if the directed relationship graph contains any cycles using DFS.
        """
        visited: Set[uuid.UUID] = set()
        rec_stack: Set[uuid.UUID] = set()

        def dfs(node: uuid.UUID) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for n in list(adj.keys()):
            if n not in visited:
                if dfs(n):
                    return True
        return False

    @staticmethod
    async def build_attack_paths_from_relationships(
        db: AsyncSession,
        workspace_id: uuid.UUID,
        scan_id: Optional[uuid.UUID] = None,
    ) -> List[AttackPath]:
        """
        Synthesizes attack paths in a workspace from existing active/confirmed security relationships.
        Enforces workspace boundaries, cycle detection, and MAX_ATTACK_PATH_NODES.
        """
        # Fetch active or confirmed relationships in this workspace
        stmt = select(SecurityRelationship).where(
            and_(
                SecurityRelationship.workspace_id == workspace_id,
                SecurityRelationship.status.in_(["active", "confirmed"]),
            )
        )
        res = await db.execute(stmt)
        relationships = list(res.scalars().all())
        if not relationships:
            return []

        # Build adjacency graph
        adj: Dict[uuid.UUID, List[SecurityRelationship]] = defaultdict(list)
        in_degree: Dict[uuid.UUID, int] = defaultdict(int)
        all_finding_ids: Set[uuid.UUID] = set()

        for rel in relationships:
            adj[rel.source_finding_id].append(rel)
            in_degree[rel.target_finding_id] += 1
            all_finding_ids.add(rel.source_finding_id)
            all_finding_ids.add(rel.target_finding_id)

        # Pre-fetch findings to access details
        f_stmt = select(Finding).where(
            and_(
                Finding.id.in_(all_finding_ids),
                Finding.workspace_id == workspace_id,
            )
        )
        f_res = await db.execute(f_stmt)
        findings_map = {f.id: f for f in f_res.scalars().all()}

        # Find candidate entry points (nodes with in_degree == 0, or with auth/secret traits)
        entry_points = [fid for fid in all_finding_ids if in_degree[fid] == 0]
        if not entry_points:
            entry_points = list(adj.keys())

        # Traverse paths using DFS with visited set to prevent infinite cycles
        discovered_paths: List[List[SecurityRelationship]] = []

        def find_chains(current_id: uuid.UUID, current_chain: List[SecurityRelationship], visited_nodes: Set[uuid.UUID]):
            if len(visited_nodes) >= MAX_ATTACK_PATH_NODES:
                if current_chain:
                    discovered_paths.append(list(current_chain))
                return

            outgoing = adj.get(current_id, [])
            if not outgoing:
                if len(current_chain) >= 1:
                    discovered_paths.append(list(current_chain))
                return

            extended = False
            for edge in outgoing:
                target_id = edge.target_finding_id
                if target_id not in visited_nodes:
                    extended = True
                    visited_nodes.add(target_id)
                    current_chain.append(edge)
                    find_chains(target_id, current_chain, visited_nodes)
                    current_chain.pop()
                    visited_nodes.remove(target_id)

            if not extended and current_chain:
                discovered_paths.append(list(current_chain))

        for ep in entry_points:
            find_chains(ep, [], {ep})

        # Filter duplicate chains
        unique_chains = []
        seen_signatures = set()
        for chain in discovered_paths:
            sig = "-".join(str(e.id) for e in chain)
            if sig not in seen_signatures:
                seen_signatures.add(sig)
                unique_chains.append(chain)

        created_attack_paths: List[AttackPath] = []

        for chain in unique_chains:
            chain_nodes_ids: List[uuid.UUID] = [chain[0].source_finding_id]
            for edge in chain:
                if edge.target_finding_id not in chain_nodes_ids:
                    chain_nodes_ids.append(edge.target_finding_id)

            first_finding = findings_map.get(chain_nodes_ids[0])
            last_finding = findings_map.get(chain_nodes_ids[-1])
            if not first_finding or not last_finding:
                continue

            # Fetch asset metadata
            a_stmt = select(Asset).where(Asset.id == last_finding.asset_id)
            a_res = await db.execute(a_stmt)
            asset = a_res.scalar_one_or_none()

            asset_meta = {
                "criticality": getattr(asset, "criticality", "medium") if asset else "medium",
                "is_public": getattr(asset, "is_public", True) if asset else True,
                "exposure_type": getattr(asset, "type", "repository") if asset else "repository",
            }

            path_name = f"Exploit chain: {first_finding.title[:40]} -> {last_finding.title[:40]}"
            path_title = f"{first_finding.title} to {last_finding.title}"

            attack_path = AttackPath(
                workspace_id=workspace_id,
                scan_id=scan_id or first_finding.scan_id,
                name=path_name,
                title=path_title,
                description=f"Multi-step attack path progressing from {first_finding.title} through {len(chain)} intermediate security transitions to {last_finding.title}.",
                entry_point=first_finding.title,
                target_asset=asset.name if asset else str(last_finding.asset_id),
                status="active",
                node_count=len(chain_nodes_ids),
                edge_count=len(chain),
                is_critical=any(findings_map[fid].severity == "critical" for fid in chain_nodes_ids if fid in findings_map),
            )
            db.add(attack_path)
            await db.flush()

            # Create Nodes
            nodes_data_for_risk = []
            db_nodes: Dict[uuid.UUID, AttackPathNode] = {}

            for idx, fid in enumerate(chain_nodes_ids):
                f = findings_map[fid]
                node = AttackPathNode(
                    attack_path_id=attack_path.id,
                    workspace_id=workspace_id,
                    node_type="vulnerability",
                    node_order=idx,
                    label=f.title,
                    description=f.description[:200] if f.description else None,
                    asset_id=f.asset_id,
                    finding_id=f.id,
                    risk_contribution=10.0,
                    metadata_={
                        "severity": f.severity,
                        "confidence": f.confidence,
                        "cwe": f.cwe_ids,
                    },
                )
                db.add(node)
                await db.flush()
                db_nodes[fid] = node

                nodes_data_for_risk.append({
                    "id": str(node.id),
                    "finding_id": str(f.id),
                    "severity": f.severity,
                    "confidence": f.confidence,
                })

            # Create Edges
            edges_data_for_risk = []
            for edge in chain:
                src_node = db_nodes.get(edge.source_finding_id)
                tgt_node = db_nodes.get(edge.target_finding_id)
                if not src_node or not tgt_node:
                    continue

                db_edge = AttackPathEdge(
                    attack_path_id=attack_path.id,
                    workspace_id=workspace_id,
                    source_node_id=src_node.id,
                    target_node_id=tgt_node.id,
                    edge_type="exploits" if edge.relationship_type in ("ENABLES", "EXPOSES") else "accesses",
                    description=edge.rationale,
                    likelihood=float(edge.confidence),
                )
                db.add(db_edge)

                edges_data_for_risk.append({
                    "source": str(src_node.id),
                    "target": str(tgt_node.id),
                    "edge_type": edge.relationship_type,
                    "likelihood": float(edge.confidence),
                    "confidence": float(edge.confidence),
                })

            # Compute Deterministic Risk Score
            risk_result = RiskEngine.calculate_attack_path_risk(
                nodes_data=nodes_data_for_risk,
                edges_data=edges_data_for_risk,
                asset_metadata=asset_meta,
            )

            attack_path.risk_score = risk_result["score"]
            attack_path.risk_band = risk_result["risk_band"]
            attack_path.factors = risk_result["factors"]
            attack_path.model_version = risk_result["model_version"]

            snapshot = RiskSnapshot(
                workspace_id=workspace_id,
                attack_path_id=attack_path.id,
                score=risk_result["score"],
                risk_band=risk_result["risk_band"],
                model_version=risk_result["model_version"],
                factors=risk_result["factors"],
                calculated_by="deterministic_engine",
            )
            db.add(snapshot)
            await db.flush()

            created_attack_paths.append(attack_path)

        await db.commit()
        for p in created_attack_paths:
            await db.refresh(p)
        return created_attack_paths

    @staticmethod
    async def recalculate_path_risk(db: AsyncSession, attack_path: AttackPath) -> RiskSnapshot:
        """
        Recalculates deterministic risk score for an existing attack path.
        Preserves complete historical audit trail in risk_snapshots.
        """
        stmt = (
            select(AttackPath)
            .options(
                selectinload(AttackPath.nodes).selectinload(AttackPathNode.finding),
                selectinload(AttackPath.edges),
            )
            .where(AttackPath.id == attack_path.id)
        )
        res = await db.execute(stmt)
        full_path = res.scalar_one_or_none() or attack_path

        nodes = full_path.nodes or []
        edges = full_path.edges or []

        nodes_data = []
        for n in nodes:
            sev = "medium"
            conf = 0.7
            if n.finding:
                sev = n.finding.severity
                conf = n.finding.confidence
            elif n.metadata_:
                sev = n.metadata_.get("severity", "medium")
                conf = n.metadata_.get("confidence", 0.7)

            nodes_data.append({
                "id": str(n.id),
                "severity": sev,
                "confidence": conf,
            })

        edges_data = [
            {
                "source": str(e.source_node_id),
                "target": str(e.target_node_id),
                "edge_type": e.edge_type,
                "likelihood": float(e.likelihood or 0.8),
                "confidence": float(e.likelihood or 0.8),
            }
            for e in edges
        ]

        # Fetch actual asset metadata if linked to nodes
        asset = None
        for n in nodes:
            if n.asset_id:
                a_res = await db.execute(select(Asset).where(Asset.id == n.asset_id))
                asset = a_res.scalar_one_or_none()
                if asset:
                    break

        asset_meta = {
            "criticality": getattr(asset, "criticality", ("high" if full_path.is_critical else "medium")) if asset else ("high" if full_path.is_critical else "medium"),
            "is_public": getattr(asset, "is_public", True) if asset else True,
            "exposure_type": getattr(asset, "type", "repository") if asset else "repository",
        }

        risk_result = RiskEngine.calculate_attack_path_risk(
            nodes_data=nodes_data,
            edges_data=edges_data,
            asset_metadata=asset_meta,
        )

        full_path.risk_score = risk_result["score"]
        full_path.risk_band = risk_result["risk_band"]
        full_path.factors = risk_result["factors"]
        full_path.model_version = risk_result["model_version"]

        snapshot = RiskSnapshot(
            workspace_id=full_path.workspace_id,
            attack_path_id=full_path.id,
            score=risk_result["score"],
            risk_band=risk_result["risk_band"],
            model_version=risk_result["model_version"],
            factors=risk_result["factors"],
            calculated_by="deterministic_engine",
        )
        db.add(snapshot)
        await db.commit()
        await db.refresh(snapshot)
        await db.refresh(full_path)

        return snapshot
