"""
Enhanced Report Generation Service
Includes support for new analysis features (Documentation Quality, Denial Risk, etc.)
"""

from typing import Dict, Any, List
from datetime import datetime
import structlog
import csv
from io import StringIO


logger = structlog.get_logger(__name__)


class EnhancedReportGenerator:
    """
    Enhanced service for generating comprehensive coding review reports
    Supports: JSON, YAML, HTML, PDF, and CSV formats
    """

    def __init__(self):
        logger.info("Enhanced report generator initialized")

    def generate_csv(self, report_data: Dict[str, Any]) -> str:
        """
        Generate CSV report with all analysis features

        Args:
            report_data: Report data dictionary

        Returns:
            CSV string
        """
        output = StringIO()

        # Header section
        output.write("RevRX - Medical Coding Analysis Report\n")
        output.write(f"Generated: {report_data['generated_at']}\n")
        output.write(f"Encounter ID: {report_data['encounter_id']}\n")
        output.write(f"Status: {report_data['status']}\n")
        output.write(f"User: {report_data['metadata']['user_email']}\n")
        output.write(f"PHI Redacted: {not report_data['metadata']['phi_included']}\n")
        output.write("\n")

        # Summary section
        output.write("=== SUMMARY ===\n")
        summary = report_data['summary']
        output.write(f"Total Billed Codes: {summary['total_billed_codes']}\n")
        output.write(f"Total Suggested Codes: {summary['total_suggested_codes']}\n")
        output.write(f"New Opportunities: {summary['new_code_opportunities']}\n")
        output.write(f"Upgrade Opportunities: {summary['upgrade_opportunities']}\n")
        output.write(f"Incremental Revenue: ${report_data['revenue_analysis']['incremental_revenue']:.2f}\n")
        output.write("\n")

        # Billed Codes section
        if report_data['code_analysis'].get('billed_codes'):
            output.write("=== BILLED CODES ===\n")
            writer = csv.writer(output)
            writer.writerow(['Code', 'Type', 'Description'])
            for code in report_data['code_analysis']['billed_codes']:
                writer.writerow([
                    code['code'],
                    code['code_type'],
                    code.get('description', '')
                ])
            output.write("\n")

        # Suggested Codes section
        if report_data['code_analysis'].get('suggested_codes'):
            output.write("=== SUGGESTED CODES ===\n")
            writer = csv.writer(output)
            writer.writerow(['Code', 'Type', 'Description', 'Confidence', 'Revenue Impact', 'Justification'])
            for code in report_data['code_analysis']['suggested_codes']:
                writer.writerow([
                    code['code'],
                    code['code_type'],
                    code.get('description', ''),
                    f"{code['confidence']*100:.0f}%",
                    f"${code.get('revenue_impact', 0):.2f}",
                    code['justification'][:100] + '...' if len(code['justification']) > 100 else code['justification']
                ])
            output.write("\n")

        # Documentation Quality section
        if report_data.get('missing_documentation'):
            output.write("=== DOCUMENTATION QUALITY ===\n")
            if report_data.get('audit_metadata', {}).get('documentation_quality_score'):
                output.write(f"Quality Score: {report_data['audit_metadata']['documentation_quality_score']*100:.0f}%\n")
            writer = csv.writer(output)
            writer.writerow(['Priority', 'Section', 'Issue', 'Suggestion'])
            for doc in report_data['missing_documentation']:
                writer.writerow([
                    doc['priority'],
                    doc['section'],
                    doc['issue'],
                    doc['suggestion']
                ])
            output.write("\n")

        # Denial Risk section
        if report_data.get('denial_risks'):
            output.write("=== DENIAL RISK ANALYSIS ===\n")
            writer = csv.writer(output)
            writer.writerow(['Code', 'Risk Level', 'Addressed', 'Denial Reasons', 'Mitigation'])
            for risk in report_data['denial_risks']:
                writer.writerow([
                    risk['code'],
                    risk['risk_level'],
                    'Yes' if risk['documentation_addresses_risks'] else 'No',
                    '; '.join(risk['denial_reasons']),
                    risk['mitigation_notes'][:100] + '...' if len(risk['mitigation_notes']) > 100 else risk['mitigation_notes']
                ])
            output.write("\n")

        # RVU Analysis section
        if report_data.get('rvu_analysis'):
            output.write("=== RVU ANALYSIS ===\n")
            rvu = report_data['rvu_analysis']
            output.write(f"Billed RVUs: {rvu['billed_codes_rvus']:.2f}\n")
            output.write(f"Suggested RVUs: {rvu['suggested_codes_rvus']:.2f}\n")
            output.write(f"Incremental RVUs: {rvu['incremental_rvus']:.2f}\n")
            output.write("\n")

            writer = csv.writer(output)
            writer.writerow(['Type', 'Code', 'RVUs', 'Description'])
            for detail in rvu.get('billed_code_details', []):
                writer.writerow(['Billed', detail['code'], f"{detail['rvus']:.2f}", detail['description']])
            for detail in rvu.get('suggested_code_details', []):
                writer.writerow(['Suggested', detail['code'], f"{detail['rvus']:.2f}", detail['description']])
            output.write("\n")

        # Modifier Suggestions section
        if report_data.get('modifier_suggestions'):
            output.write("=== MODIFIER SUGGESTIONS ===\n")
            writer = csv.writer(output)
            writer.writerow(['Code', 'Modifier', 'Justification'])
            for mod in report_data['modifier_suggestions']:
                writer.writerow([
                    mod['code'],
                    mod['modifier'],
                    mod['justification']
                ])
            output.write("\n")

        # Uncaptured Services section
        if report_data.get('uncaptured_services'):
            output.write("=== UNCAPTURED SERVICES ===\n")
            writer = csv.writer(output)
            writer.writerow(['Priority', 'Service', 'Suggested Codes', 'Location', 'Est. RVUs'])
            for service in report_data['uncaptured_services']:
                writer.writerow([
                    service['priority'],
                    service['service'],
                    ', '.join(service['suggested_codes']),
                    service['location_in_note'],
                    f"{service.get('estimated_rvus', 0):.2f}"
                ])
            output.write("\n")

        # Footer
        output.write("=== COMPLIANCE NOTICE ===\n")
        output.write("This report is for informational purposes only.\n")
        output.write("All coding decisions should be reviewed by qualified medical coding professionals.\n")
        output.write("PHI has been redacted from this export to maintain HIPAA compliance.\n")
        output.write(f"\nReport generated by RevRX on {datetime.utcnow().isoformat()}\n")

        return output.getvalue()

    def generate_enhanced_html(self, report_data: Dict[str, Any]) -> str:
        """
        Generate enhanced HTML report with all new features

        Args:
            report_data: Report data dictionary

        Returns:
            HTML string with all features included
        """
        metadata = report_data["metadata"]
        clinical = report_data["clinical_note"]
        codes = report_data["code_analysis"]
        revenue = report_data["revenue_analysis"]
        summary = report_data["summary"]

        # Build sections for new features
        documentation_quality_html = self._build_documentation_quality_html(report_data)
        denial_risk_html = self._build_denial_risk_html(report_data)
        rvu_analysis_html = self._build_rvu_analysis_html(report_data)
        modifier_suggestions_html = self._build_modifier_suggestions_html(report_data)
        uncaptured_services_html = self._build_uncaptured_services_html(report_data)

        # Build code comparison table
        suggested_codes_html = ""
        for code_data in codes.get("suggested_codes", []):
            suggested_codes_html += f"""
            <tr>
                <td>{code_data.get('code', 'N/A')}</td>
                <td>{code_data.get('code_type', 'N/A')}</td>
                <td><span class="badge badge-{code_data.get('comparison_type', 'new')}">{code_data.get('comparison_type', 'N/A').upper()}</span></td>
                <td>${code_data.get('revenue_impact', 0):.2f}</td>
                <td>{code_data.get('confidence', 0):.0%}</td>
            </tr>
            """

        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Enhanced Coding Review Report - {report_data['encounter_id']}</title>
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
        .watermark {{
            text-align: center;
            color: #95a5a6;
            font-size: 12px;
            margin-bottom: 20px;
            padding: 10px;
            border: 1px dashed #bdc3c7;
            background: #ecf0f1;
        }}
        .section {{
            margin-bottom: 30px;
            page-break-inside: avoid;
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
        .card.high-priority .value {{
            color: #e74c3c;
        }}
        .card.medium-priority .value {{
            color: #f39c12;
        }}
        .card.low-risk .value {{
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
        .badge-high {{
            background: #ffebee;
            color: #e74c3c;
        }}
        .badge-medium {{
            background: #fff3e0;
            color: #f39c12;
        }}
        .badge-low {{
            background: #e8f5e9;
            color: #27ae60;
        }}
        .footer {{
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e0e0e0;
            text-align: center;
            color: #7f8c8d;
            font-size: 12px;
        }}
        .compliance-notice {{
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            border-radius: 6px;
            margin: 20px 0;
        }}
        .compliance-notice strong {{
            color: #856404;
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
        <div class="watermark">
            <strong>CONFIDENTIAL MEDICAL CODING ANALYSIS</strong><br>
            Generated: {metadata['generated_at']} | Report ID: {report_data['encounter_id'][:16]}...<br>
            PHI Redacted: {'Yes' if not metadata['phi_included'] else 'No'}
        </div>

        <div class="header">
            <h1>Enhanced Coding Review Report</h1>
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

        {documentation_quality_html}
        {denial_risk_html}
        {rvu_analysis_html}
        {modifier_suggestions_html}
        {uncaptured_services_html}

        <div class="compliance-notice">
            <strong>⚠️ COMPLIANCE NOTICE</strong><br>
            This report is for informational purposes only. All coding decisions should be reviewed by qualified
            medical coding professionals. This analysis is based on de-identified clinical documentation and
            should be used as a guidance tool only. PHI has been redacted from this export to maintain HIPAA compliance.
        </div>

        <div class="footer">
            <p>🤖 Generated with RevRX AI-Powered Coding Review System</p>
            <p>Report generated on {metadata['generated_at']}</p>
            <p><strong>Note:</strong> This is a confidential medical document. Handle according to HIPAA regulations.</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def _build_documentation_quality_html(self, report_data: Dict[str, Any]) -> str:
        """Build HTML section for documentation quality analysis"""
        if not report_data.get('missing_documentation'):
            return ""

        quality_score = report_data.get('audit_metadata', {}).get('documentation_quality_score', 0)
        score_html = f"<p>Documentation Quality Score: <strong>{quality_score*100:.0f}%</strong></p>" if quality_score else ""

        rows_html = ""
        for doc in report_data['missing_documentation']:
            priority_class = doc['priority'].lower()
            rows_html += f"""
            <tr>
                <td><span class="badge badge-{priority_class}">{doc['priority']}</span></td>
                <td>{doc['section']}</td>
                <td>{doc['issue']}</td>
                <td>{doc['suggestion']}</td>
            </tr>
            """

        return f"""
        <div class="section">
            <h2>Documentation Quality Analysis</h2>
            {score_html}
            <table>
                <thead>
                    <tr>
                        <th>Priority</th>
                        <th>Section</th>
                        <th>Issue</th>
                        <th>Suggestion</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """

    def _build_denial_risk_html(self, report_data: Dict[str, Any]) -> str:
        """Build HTML section for denial risk analysis"""
        if not report_data.get('denial_risks'):
            return ""

        rows_html = ""
        for risk in report_data['denial_risks']:
            risk_class = risk['risk_level'].lower()
            addressed = "✓ Yes" if risk['documentation_addresses_risks'] else "✗ No"
            rows_html += f"""
            <tr>
                <td>{risk['code']}</td>
                <td><span class="badge badge-{risk_class}">{risk['risk_level']}</span></td>
                <td>{addressed}</td>
                <td>{', '.join(risk['denial_reasons'])}</td>
            </tr>
            """

        return f"""
        <div class="section">
            <h2>Denial Risk Analysis</h2>
            <table>
                <thead>
                    <tr>
                        <th>Code</th>
                        <th>Risk Level</th>
                        <th>Addressed</th>
                        <th>Denial Reasons</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """

    def _build_rvu_analysis_html(self, report_data: Dict[str, Any]) -> str:
        """Build HTML section for RVU analysis"""
        if not report_data.get('rvu_analysis'):
            return ""

        rvu = report_data['rvu_analysis']
        return f"""
        <div class="section">
            <h2>RVU Analysis</h2>
            <div class="summary-cards">
                <div class="card">
                    <h3>Billed RVUs</h3>
                    <div class="value">{rvu['billed_codes_rvus']:.2f}</div>
                </div>
                <div class="card">
                    <h3>Suggested RVUs</h3>
                    <div class="value">{rvu['suggested_codes_rvus']:.2f}</div>
                </div>
                <div class="card revenue">
                    <h3>Incremental RVUs</h3>
                    <div class="value">+{rvu['incremental_rvus']:.2f}</div>
                </div>
            </div>
        </div>
        """

    def _build_modifier_suggestions_html(self, report_data: Dict[str, Any]) -> str:
        """Build HTML section for modifier suggestions"""
        if not report_data.get('modifier_suggestions'):
            return ""

        rows_html = ""
        for mod in report_data['modifier_suggestions']:
            rows_html += f"""
            <tr>
                <td>{mod['code']}{mod['modifier']}</td>
                <td>{mod['modifier']}</td>
                <td>{mod['justification']}</td>
            </tr>
            """

        return f"""
        <div class="section">
            <h2>Modifier Suggestions</h2>
            <table>
                <thead>
                    <tr>
                        <th>Code + Modifier</th>
                        <th>Modifier</th>
                        <th>Justification</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """

    def _build_uncaptured_services_html(self, report_data: Dict[str, Any]) -> str:
        """Build HTML section for uncaptured services"""
        if not report_data.get('uncaptured_services'):
            return ""

        rows_html = ""
        for service in report_data['uncaptured_services']:
            priority_class = service['priority'].lower()
            rows_html += f"""
            <tr>
                <td><span class="badge badge-{priority_class}">{service['priority']}</span></td>
                <td>{service['service']}</td>
                <td>{', '.join(service['suggested_codes'])}</td>
                <td>{service.get('estimated_rvus', 0):.2f}</td>
            </tr>
            """

        return f"""
        <div class="section">
            <h2>Uncaptured Services (Charge Capture Opportunities)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Priority</th>
                        <th>Service</th>
                        <th>Suggested Codes</th>
                        <th>Est. RVUs</th>
                    </tr>
                </thead>
                <tbody>
                    {rows_html}
                </tbody>
            </table>
        </div>
        """


# Export singleton instance
enhanced_report_generator = EnhancedReportGenerator()
