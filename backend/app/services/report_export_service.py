import io
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Tuple
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)

from app.models.report import Report


class ReportExportService:
    """
    Exports reports to reproducible JSON and styled PDF documents.
    Enforces secret redaction and non-repudiation formatting.
    """

    @staticmethod
    def export_json(report: Report) -> Tuple[str, str, str]:
        """
        Returns (json_content_string, file_name, content_type)
        """
        cutoff_str = (report.data_cutoff_at or datetime.utcnow()).strftime("%Y%m%d_%H%M%S")
        file_name = f"shadowops_{report.report_type}_{str(report.id)[:8]}_{cutoff_str}.json"
        content_type = "application/json"

        payload = {
            "report_id": str(report.id),
            "workspace_id": str(report.workspace_id),
            "report_type": report.report_type,
            "title": report.title,
            "description": report.description,
            "generated_by": report.generated_by,
            "schema_version": report.schema_version,
            "data_cutoff_at": report.data_cutoff_at.isoformat() if report.data_cutoff_at else None,
            "completeness_status": report.completeness_status,
            "parameters": report.parameters,
            "snapshot_data": report.snapshot_data,
            "created_at": report.created_at.isoformat() if report.created_at else None,
            "completed_at": report.completed_at.isoformat() if report.completed_at else None,
        }

        json_str = json.dumps(payload, indent=2, default=str)
        return json_str, file_name, content_type

    @staticmethod
    def export_pdf(report: Report) -> Tuple[bytes, str, str]:
        """
        Generates a professional executive security PDF using ReportLab.
        Returns (pdf_bytes, file_name, content_type)
        """
        cutoff_str = (report.data_cutoff_at or datetime.utcnow()).strftime("%Y%m%d_%H%M%S")
        file_name = f"shadowops_{report.report_type}_{str(report.id)[:8]}_{cutoff_str}.pdf"
        content_type = "application/pdf"

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=40,
            leftMargin=40,
            topMargin=40,
            bottomMargin=40,
        )

        styles = getSampleStyleSheet()

        # Custom Styles
        title_style = ParagraphStyle(
            "DocTitle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0f172a"),
        )
        subtitle_style = ParagraphStyle(
            "DocSubTitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=colors.HexColor("#475569"),
        )
        h2_style = ParagraphStyle(
            "Heading2Custom",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#1e293b"),
            spaceBefore=14,
            spaceAfter=6,
        )
        body_style = ParagraphStyle(
            "BodyCustom",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=colors.HexColor("#334155"),
        )
        badge_style = ParagraphStyle(
            "BadgeStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Bold",
            fontSize=8,
            textColor=colors.whitesmoke,
        )
        disclaimer_style = ParagraphStyle(
            "DisclaimerStyle",
            parent=styles["Normal"],
            fontName="Helvetica-Oblique",
            fontSize=8,
            leading=11,
            textColor=colors.HexColor("#64748b"),
        )

        elements = []

        # 1. Header Banner
        elements.append(Paragraph("SHADOWOPS // CYBERSECURITY INTELLIGENCE", subtitle_style))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(report.title or "Security Report", title_style))
        elements.append(Spacer(1, 6))

        cutoff_formatted = report.data_cutoff_at.strftime("%B %d, %Y - %H:%M:%S UTC") if report.data_cutoff_at else "N/A"
        meta_line = f"Report Type: <b>{report.report_type.replace('_', ' ').upper()}</b> | Data Cutoff: <b>{cutoff_formatted}</b> | Status: <b>{report.completeness_status}</b>"
        elements.append(Paragraph(meta_line, subtitle_style))
        elements.append(Spacer(1, 10))
        elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0284c7"), spaceAfter=14))

        # 2. Executive / Security Invariant Notice
        disclaimer_box_data = [
            [
                Paragraph(
                    "<b>CONFIDENTIAL & AUDIT-VERIFIED:</b> This document contains confidential security assessments and telemetry for authorized personnel only. "
                    "Deterministic scan facts and verified evidence take strict precedence over any advisory narrative. "
                    "Redaction has been applied to sensitive credentials.",
                    disclaimer_style,
                )
            ]
        ]
        disclaimer_table = Table(disclaimer_box_data, colWidths=[530])
        disclaimer_table.setStyle(
            TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
                ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("PADDING", (0, 0), (-1, -1), 8),
            ])
        )
        elements.append(disclaimer_table)
        elements.append(Spacer(1, 14))

        snap = report.snapshot_data or {}

        # 3. Key Metrics Table (if available)
        metrics = snap.get("metrics")
        if metrics:
            elements.append(Paragraph("Security Posture Snapshot", h2_style))
            
            risk_score = metrics.get("risk_score")
            score_disp = f"{risk_score:.1f}" if risk_score is not None else "N/A"
            band_disp = metrics.get("risk_band", "NOT_CALCULATED")

            sev_counts = metrics.get("by_severity", {})
            crit = sev_counts.get("critical", 0)
            high = sev_counts.get("high", 0)
            med = sev_counts.get("medium", 0)
            low = sev_counts.get("low", 0)

            metric_rows = [
                [
                    Paragraph("<b>Deterministic Risk Score</b>", body_style),
                    Paragraph(f"<b>{score_disp}</b> ({band_disp})", body_style),
                    Paragraph("<b>Open Findings</b>", body_style),
                    Paragraph(f"<b>{metrics.get('open_findings_count', 0)}</b> (Crit: {crit}, High: {high})", body_style),
                ],
                [
                    Paragraph("<b>Critical Attack Paths</b>", body_style),
                    Paragraph(f"{metrics.get('critical_attack_paths_count', 0)}", body_style),
                    Paragraph("<b>Verified Fixes</b>", body_style),
                    Paragraph(f"{metrics.get('verifications_completed', 0)}", body_style),
                ],
            ]
            m_table = Table(metric_rows, colWidths=[140, 125, 140, 125])
            m_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1f5f9")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ])
            )
            elements.append(m_table)
            elements.append(Spacer(1, 14))

        # 4. Executive Narrative / Advisory Section
        exec_narrative = snap.get("executive_narrative")
        if exec_narrative:
            elements.append(Paragraph("Executive Advisory Summary", h2_style))
            narrative_text = exec_narrative.get("narrative", "")
            is_ai = exec_narrative.get("is_ai_generated", False)
            elements.append(Paragraph(narrative_text, body_style))
            elements.append(Spacer(1, 4))
            label = "AI-Assisted Analysis (Advisory)" if is_ai else "Deterministic Summary"
            elements.append(Paragraph(f"<i>Source: {label} — {exec_narrative.get('disclaimer', '')}</i>", disclaimer_style))
            elements.append(Spacer(1, 14))

        # 5. Top Critical Findings (for executive_summary)
        top_findings = snap.get("top_critical_findings", [])
        if top_findings:
            elements.append(Paragraph(f"Priority Critical Findings ({len(top_findings)})", h2_style))
            f_table_data = [
                [
                    Paragraph("<b>Severity</b>", body_style),
                    Paragraph("<b>Title / Rule</b>", body_style),
                    Paragraph("<b>File Location</b>", body_style),
                    Paragraph("<b>Status</b>", body_style),
                ]
            ]
            for tf in top_findings:
                sev_color = "#dc2626" if tf.get("severity") == "critical" else "#ea580c"
                sev_cell = Paragraph(f"<font color='{sev_color}'><b>{tf.get('severity', '').upper()}</b></font>", body_style)
                title_cell = Paragraph(f"<b>{tf.get('title', '')}</b><br/><font color='#64748b'>{tf.get('rule_id', '')}</font>", body_style)
                loc_cell = Paragraph(f"{tf.get('file_path', 'N/A')}:{tf.get('line_start', '')}", body_style)
                st_cell = Paragraph(tf.get("status", "open"), body_style)
                f_table_data.append([sev_cell, title_cell, loc_cell, st_cell])

            f_table = Table(f_table_data, colWidths=[70, 220, 160, 80])
            f_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )
            elements.append(f_table)
            elements.append(Spacer(1, 14))

        # 6. Technical Findings (for technical_vulnerability report)
        tech_findings = snap.get("findings", [])
        if tech_findings:
            elements.append(Paragraph(f"Identified Vulnerabilities ({len(tech_findings)})", h2_style))
            tech_table_data = [
                [
                    Paragraph("<b>Severity</b>", body_style),
                    Paragraph("<b>Vulnerability</b>", body_style),
                    Paragraph("<b>Location & CWE</b>", body_style),
                    Paragraph("<b>Evidence</b>", body_style),
                ]
            ]
            for f in tech_findings[:30]:  # limit to first 30 for PDF page size sanity
                sev_color = "#dc2626" if f.get("severity") == "critical" else ("#ea580c" if f.get("severity") == "high" else "#0284c7")
                sev_cell = Paragraph(f"<font color='{sev_color}'><b>{f.get('severity', '').upper()}</b></font>", body_style)
                title_cell = Paragraph(f"<b>{f.get('title', '')}</b><br/><font color='#64748b'>{f.get('rule_id', '')}</font>", body_style)
                loc_cell = Paragraph(f"{f.get('file_path', 'N/A')}:{f.get('line_start', '')}<br/>CWE: {f.get('cwe_id', 'N/A')}", body_style)
                ev_count = f.get("evidence_count", 0)
                ev_cell = Paragraph(f"{ev_count} item(s)", body_style)
                tech_table_data.append([sev_cell, title_cell, loc_cell, ev_cell])

            t_table = Table(tech_table_data, colWidths=[65, 230, 160, 75])
            t_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )
            elements.append(t_table)
            elements.append(Spacer(1, 14))

        # 7. Remediation Proposals (for remediation_progress report)
        proposals = snap.get("proposals", [])
        if proposals:
            elements.append(Paragraph(f"Remediation Proposals ({len(proposals)})", h2_style))
            rem_table_data = [
                [
                    Paragraph("<b>Status</b>", body_style),
                    Paragraph("<b>Proposal</b>", body_style),
                    Paragraph("<b>Files</b>", body_style),
                    Paragraph("<b>Applied Date</b>", body_style),
                ]
            ]
            for p in proposals[:30]:
                st_color = "#16a34a" if p.get("status") in ("applied", "verified") else "#d97706"
                st_cell = Paragraph(f"<font color='{st_color}'><b>{p.get('status', '').upper()}</b></font>", body_style)
                title_cell = Paragraph(f"<b>{p.get('title', 'Remediation')}</b>", body_style)
                files_disp = ", ".join(p.get("affected_files", []) or []) or "N/A"
                files_cell = Paragraph(files_disp, body_style)
                app_date = p.get("applied_at", "Pending")
                app_cell = Paragraph(app_date[:10] if app_date else "Pending", body_style)
                rem_table_data.append([st_cell, title_cell, files_cell, app_cell])

            r_table = Table(rem_table_data, colWidths=[75, 230, 140, 85])
            r_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )
            elements.append(r_table)
            elements.append(Spacer(1, 14))

        # 8. Verification Jobs (for verification_regression report)
        v_jobs = snap.get("jobs", [])
        if v_jobs:
            elements.append(Paragraph(f"Independent Fix Verifications ({len(v_jobs)})", h2_style))
            v_table_data = [
                [
                    Paragraph("<b>Status</b>", body_style),
                    Paragraph("<b>Comparison</b>", body_style),
                    Paragraph("<b>Verdict</b>", body_style),
                    Paragraph("<b>Human Review</b>", body_style),
                ]
            ]
            for j in v_jobs[:30]:
                st_cell = Paragraph(f"<b>{j.get('status', '')}</b>", body_style)
                comp_cell = Paragraph(j.get("vulnerability_status") or j.get("evidence_comparison_outcome") or "N/A", body_style)
                verd_cell = Paragraph(j.get("policy_verdict", "N/A") or "N/A", body_style)
                hr = j.get("human_review")
                hr_disp = f"<b>{hr.get('decision')}</b>" if hr else "Pending Sign-off"
                hr_cell = Paragraph(hr_disp, body_style)
                v_table_data.append([st_cell, comp_cell, verd_cell, hr_cell])

            v_table = Table(v_table_data, colWidths=[90, 160, 140, 140])
            v_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )
            elements.append(v_table)
            elements.append(Spacer(1, 14))

        # 9. Asset Inventory (for asset_security_posture report)
        assets_list = snap.get("assets", [])
        if assets_list:
            elements.append(Paragraph(f"Monitored Assets ({len(assets_list)})", h2_style))
            a_table_data = [
                [
                    Paragraph("<b>Asset Name</b>", body_style),
                    Paragraph("<b>Type / Env</b>", body_style),
                    Paragraph("<b>Authorization</b>", body_style),
                    Paragraph("<b>Open Findings</b>", body_style),
                ]
            ]
            for a in assets_list[:30]:
                name_cell = Paragraph(f"<b>{a.get('name', '')}</b>", body_style)
                type_cell = Paragraph(f"{a.get('asset_type', '')} ({a.get('environment', '')})", body_style)
                auth_status = a.get("authorization", {}).get("status", "unauthorized")
                auth_cell = Paragraph(auth_status.upper(), body_style)
                open_cnt = a.get("open_findings_count", 0)
                sev_br = a.get("severity_breakdown", {})
                crit = sev_br.get("critical", 0)
                find_cell = Paragraph(f"{open_cnt} (Crit: {crit})", body_style)
                a_table_data.append([name_cell, type_cell, auth_cell, find_cell])

            a_table = Table(a_table_data, colWidths=[150, 130, 120, 130])
            a_table.setStyle(
                TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                    ("PADDING", (0, 0), (-1, -1), 5),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ])
            )
            elements.append(a_table)
            elements.append(Spacer(1, 14))

        # Build document
        doc.build(elements)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        return pdf_bytes, file_name, content_type
