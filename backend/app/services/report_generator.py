"""
Report Generation Service
Generates reports in multiple formats (HTML, JSON, YAML, PDF)
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import structlog
import yaml
import json
from io import BytesIO

from app.core.database import prisma
from app.services.phi_handler import phi_handler


logger = structlog.get_logger(__name__)


class ReportGenerator:
    """
    Service for generating coding review reports in multiple formats
    """

    def __init__(self):
        logger.info("Report generator initialized")

    async def generate_report(
        self,
        encounter_id: str,
        include_phi: bool = False,
        user_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate comprehensive report for an encounter

        Args:
            encounter_id: Encounter ID
            include_phi: Whether to include PHI (requires admin access)
            user_id: User ID for audit logging

        Returns:
            Dictionary with report data
        """
        logger.info(
            "Generating report",
            encounter_id=encounter_id,
            include_phi=include_phi,
        )

        # Get encounter with all related data
        encounter = await prisma.encounter.find_unique(
            where={"id": encounter_id},
            include={
                "user": True,
                "uploadedFiles": True,
                "report": True,
                "phiMapping": True,
            },
        )

        if not encounter:
            raise ValueError(f"Encounter {encounter_id} not found")

        if not encounter.report:
            raise ValueError(f"Report not yet generated for encounter {encounter_id}")

        # Get clinical text (de-identified or re-identified)
        clinical_text = ""
        if encounter.phiMapping:
            if include_phi:
                # Re-identify PHI for authorized users
                phi_result = await phi_handler.retrieve_phi_mapping(encounter_id)
                if phi_result:
                    clinical_text = phi_handler.reidentify(
                        phi_result.deidentifiedText,
                        phi_result.phiMappings,
                    )

                # Log PHI access
                if user_id:
                    await prisma.auditlog.create(
                        data={
                            "userId": user_id,
                            "action": "REPORT_PHI_ACCESSED",
                            "resourceType": "Report",
                            "resourceId": encounter.report.id,
                        }
                    )
            else:
                clinical_text = encounter.phiMapping.deidentifiedText

        # Build report data
        report_data = {
            "encounter_id": encounter.id,
            "generated_at": datetime.utcnow().isoformat(),
            "status": encounter.status,
            "metadata": {
                "encounter_created": encounter.createdAt.isoformat(),
                "processing_time_ms": encounter.processingTime,
                "processing_completed": encounter.processingCompletedAt.isoformat()
                if encounter.processingCompletedAt
                else None,
                "user_email": encounter.user.email,
                "phi_included": include_phi,
                "phi_detected": encounter.phiMapping.phiDetected
                if encounter.phiMapping
                else False,
            },
            "clinical_note": {
                "text": clinical_text,
                "length": len(clinical_text),
                "uploaded_files": [
                    {
                        "filename": f.fileName,
                        "file_type": f.fileType,
                        "file_size": f.fileSize,
                        "uploaded_at": f.createdAt.isoformat(),
                    }
                    for f in encounter.uploadedFiles
                ],
            },
            "code_analysis": {
                "billed_codes": encounter.report.billedCodes,
                "suggested_codes": encounter.report.suggestedCodes,
                "ai_model": encounter.report.aiModel,
                "confidence_score": float(encounter.report.confidenceScore)
                if encounter.report.confidenceScore
                else 0.0,
            },
            "revenue_analysis": {
                "incremental_revenue": float(encounter.report.incrementalRevenue),
                "currency": "USD",
                "calculation_method": "Medicare 2024 National Average Rates",
            },
            "summary": {
                "total_billed_codes": len(encounter.report.billedCodes)
                if isinstance(encounter.report.billedCodes, list)
                else 0,
                "total_suggested_codes": len(encounter.report.suggestedCodes)
                if isinstance(encounter.report.suggestedCodes, list)
                else 0,
                "new_code_opportunities": sum(
                    1
                    for code in (encounter.report.suggestedCodes or [])
                    if code.get("comparison_type") == "new"
                ),
                "upgrade_opportunities": sum(
                    1
                    for code in (encounter.report.suggestedCodes or [])
                    if code.get("comparison_type") == "upgrade"
                ),
            },
        }

        logger.info(
            "Report generated",
            encounter_id=encounter_id,
            incremental_revenue=report_data["revenue_analysis"]["incremental_revenue"],
        )

        return report_data

    def generate_json(self, report_data: Dict[str, Any]) -> str:
        """
        Generate JSON report

        Args:
            report_data: Report data dictionary

        Returns:
            JSON string
        """
        return json.dumps(report_data, indent=2, ensure_ascii=False)

    def generate_yaml(self, report_data: Dict[str, Any]) -> str:
        """
        Generate YAML report

        Args:
            report_data: Report data dictionary

        Returns:
            YAML string
        """
        return yaml.dump(
            report_data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False,
        )

    def generate_html(self, report_data: Dict[str, Any]) -> str:
        """
        Generate HTML report

        Args:
            report_data: Report data dictionary

        Returns:
            HTML string
        """
        metadata = report_data["metadata"]
        clinical = report_data["clinical_note"]
        codes = report_data["code_analysis"]
        revenue = report_data["revenue_analysis"]
        summary = report_data["summary"]

        # Build code comparison table
        suggested_codes_html = ""
        for code_data in codes.get("suggested_codes", []):
            suggested_codes_html += f"""
            <tr>
                <td>{code_data.get('suggested_code', 'N/A')}</td>
                <td>{code_data.get('code_type', 'N/A')}</td>
                <td>{code_data.get('billed_code', 'N/A')}</td>
                <td><span class="badge badge-{code_data.get('comparison_type', 'new')}">{code_data.get('comparison_type', 'N/A').upper()}</span></td>
                <td>${code_data.get('revenue_impact', 0):.2f}</td>
                <td>{code_data.get('confidence', 0):.0%}</td>
            </tr>
            """

        # Build justifications
        justifications_html = ""
        for code_data in codes.get("suggested_codes", []):
            justifications_html += f"""
            <div class="justification-item">
                <h4>{code_data.get('suggested_code')} - {code_data.get('code_type')}</h4>
                <p><strong>Justification:</strong> {code_data.get('justification', 'N/A')}</p>
                <p><strong>Supporting Text:</strong></p>
                <ul>
                    {''.join(f'<li>{text}</li>' for text in code_data.get('supporting_text', []))}
                </ul>
            </div>
            """

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Coding Review Report - {report_data['encounter_id']}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            background: #f5f5f5;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .header {{
            border-bottom: 3px solid #3498db;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .header h1 {{
            color: #2c3e50;
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .header .meta {{
            color: #7f8c8d;
            font-size: 14px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section h2 {{
            color: #2c3e50;
            font-size: 20px;
            margin-bottom: 15px;
            border-left: 4px solid #3498db;
            padding-left: 12px;
        }}
        .summary-cards {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            border: 1px solid #e0e0e0;
        }}
        .card h3 {{
            color: #7f8c8d;
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 8px;
            font-weight: 600;
        }}
        .card .value {{
            font-size: 28px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .card.revenue .value {{
            color: #27ae60;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #e0e0e0;
        }}
        th {{
            background: #f8f9fa;
            font-weight: 600;
            color: #2c3e50;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 11px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        .badge-new {{
            background: #e8f5e9;
            color: #27ae60;
        }}
        .badge-upgrade {{
            background: #e3f2fd;
            color: #2196f3;
        }}
        .badge-match {{
            background: #f5f5f5;
            color: #7f8c8d;
        }}
        .clinical-note {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 6px;
            border-left: 4px solid #3498db;
            white-space: pre-wrap;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            line-height: 1.8;
            max-height: 400px;
            overflow-y: auto;
        }}
        .justification-item {{
            margin-bottom: 20px;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 6px;
        }}
        .justification-item h4 {{
            color: #2c3e50;
            margin-bottom: 10px;
        }}
        .justification-item ul {{
            margin-left: 20px;
            margin-top: 10px;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            color: #7f8c8d;
            font-size: 12px;
        }}
        @media print {{
            body {{
                background: white;
                padding: 0;
            }}
            .container {{
                box-shadow: none;
                padding: 20px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Coding Review Report</h1>
            <div class="meta">
                Encounter ID: {report_data['encounter_id']}<br>
                Generated: {metadata['generated_at']}<br>
                Status: {report_data['status']}<br>
                User: {metadata['user_email']}
            </div>
        </div>

        <div class="section">
            <h2>Revenue Summary</h2>
            <div class="summary-cards">
                <div class="card revenue">
                    <h3>Incremental Revenue</h3>
                    <div class="value">${revenue['incremental_revenue']:.2f}</div>
                </div>
                <div class="card">
                    <h3>New Codes</h3>
                    <div class="value">{summary['new_code_opportunities']}</div>
                </div>
                <div class="card">
                    <h3>Upgrades</h3>
                    <div class="value">{summary['upgrade_opportunities']}</div>
                </div>
                <div class="card">
                    <h3>Confidence</h3>
                    <div class="value">{codes['confidence_score']:.0%}</div>
                </div>
            </div>
        </div>

        <div class="section">
            <h2>Code Comparison</h2>
            <table>
                <thead>
                    <tr>
                        <th>Suggested Code</th>
                        <th>Type</th>
                        <th>Billed Code</th>
                        <th>Status</th>
                        <th>Revenue Impact</th>
                        <th>Confidence</th>
                    </tr>
                </thead>
                <tbody>
                    {suggested_codes_html}
                </tbody>
            </table>
        </div>

        <div class="section">
            <h2>Justifications & Supporting Evidence</h2>
            {justifications_html}
        </div>

        <div class="section">
            <h2>Clinical Note</h2>
            <div class="clinical-note">{clinical['text']}</div>
        </div>

        <div class="section">
            <h2>Processing Information</h2>
            <table>
                <tr>
                    <th>Processing Time</th>
                    <td>{metadata['processing_time_ms']}ms</td>
                </tr>
                <tr>
                    <th>AI Model</th>
                    <td>{codes['ai_model']}</td>
                </tr>
                <tr>
                    <th>PHI Detected</th>
                    <td>{'Yes' if metadata['phi_detected'] else 'No'}</td>
                </tr>
                <tr>
                    <th>PHI Included in Report</th>
                    <td>{'Yes' if metadata['phi_included'] else 'No (De-identified)'}</td>
                </tr>
            </table>
        </div>

        <div class="footer">
            <p>🤖 Generated with AI-Powered Coding Review System</p>
            <p>Report generated on {metadata['generated_at']}</p>
            <p><strong>Note:</strong> This report is for informational purposes only. All coding decisions should be reviewed by qualified medical coding professionals.</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    async def generate_pdf(self, report_data: Dict[str, Any]) -> bytes:
        """
        Generate PDF report using WeasyPrint

        Args:
            report_data: Report data dictionary

        Returns:
            PDF bytes
        """
        try:
            from weasyprint import HTML, CSS
        except ImportError:
            logger.error("WeasyPrint not installed. Install with: pip install weasyprint")
            raise ImportError(
                "WeasyPrint is required for PDF generation. Install with: pip install weasyprint"
            )

        # Generate HTML first
        html_content = self.generate_html(report_data)

        # Convert to PDF
        pdf_bytes = HTML(string=html_content).write_pdf()

        logger.info("PDF report generated", size_bytes=len(pdf_bytes))

        return pdf_bytes


# Export singleton instance
report_generator = ReportGenerator()
