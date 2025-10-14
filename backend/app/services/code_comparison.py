"""
Code Comparison Engine
Compares billed codes with AI suggestions and calculates incremental revenue
"""

from typing import List, Dict, Any, Optional, Tuple
import structlog
import re

from app.services.openai_service import CodeSuggestion, CodingSuggestionResult


logger = structlog.get_logger(__name__)


# Medicare reimbursement rates (2024 national averages - approximate)
# In production, these should come from a database or external API
CPT_REIMBURSEMENT_RATES = {
    # Evaluation and Management
    "99202": 76.16,   # New patient, straightforward
    "99203": 113.46,  # New patient, low complexity
    "99204": 169.93,  # New patient, moderate complexity
    "99205": 224.14,  # New patient, high complexity
    "99211": 25.00,   # Established patient, minimal
    "99212": 56.88,   # Established patient, straightforward
    "99213": 93.51,   # Established patient, low complexity
    "99214": 131.20,  # Established patient, moderate complexity
    "99215": 183.19,  # Established patient, high complexity

    # Procedures (examples)
    "45380": 350.00,  # Colonoscopy with biopsy
    "76700": 120.00,  # Abdominal ultrasound
    "93000": 17.00,   # ECG
    "36415": 3.00,    # Routine venipuncture
    "80053": 15.00,   # Comprehensive metabolic panel
}

ICD10_REIMBURSEMENT_IMPACT = {
    # ICD-10 codes affect reimbursement through DRG/case mix
    # These are approximate adjustments
    "E11.9": 10.00,   # Type 2 diabetes
    "I10": 8.00,      # Essential hypertension
    "Z79.4": 12.00,   # Long-term insulin use
    "E78.5": 8.00,    # Hyperlipidemia
    "K21.9": 10.00,   # GERD
}


class CodeComparison:
    """Comparison between billed and suggested code"""

    def __init__(
        self,
        billed_code: Optional[str],
        suggested_code: str,
        code_type: str,
        comparison_type: str,  # "match", "upgrade", "new", "missing"
        revenue_impact: float,
        confidence: float,
        justification: str,
        supporting_text: List[str],
    ):
        self.billed_code = billed_code
        self.suggested_code = suggested_code
        self.code_type = code_type
        self.comparison_type = comparison_type
        self.revenue_impact = revenue_impact
        self.confidence = confidence
        self.justification = justification
        self.supporting_text = supporting_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "billed_code": self.billed_code,
            "suggested_code": self.suggested_code,
            "code_type": self.code_type,
            "comparison_type": self.comparison_type,
            "revenue_impact": self.revenue_impact,
            "confidence": self.confidence,
            "justification": self.justification,
            "supporting_text": self.supporting_text,
        }


class ComparisonResult:
    """Result of code comparison analysis"""

    def __init__(
        self,
        comparisons: List[CodeComparison],
        total_billed_revenue: float,
        total_suggested_revenue: float,
        incremental_revenue: float,
        confidence_score: float,
        new_codes_count: int,
        upgrade_opportunities_count: int,
    ):
        self.comparisons = comparisons
        self.total_billed_revenue = total_billed_revenue
        self.total_suggested_revenue = total_suggested_revenue
        self.incremental_revenue = incremental_revenue
        self.confidence_score = confidence_score
        self.new_codes_count = new_codes_count
        self.upgrade_opportunities_count = upgrade_opportunities_count

    def to_dict(self) -> Dict[str, Any]:
        return {
            "comparisons": [c.to_dict() for c in self.comparisons],
            "total_billed_revenue": round(self.total_billed_revenue, 2),
            "total_suggested_revenue": round(self.total_suggested_revenue, 2),
            "incremental_revenue": round(self.incremental_revenue, 2),
            "confidence_score": round(self.confidence_score, 2),
            "new_codes_count": self.new_codes_count,
            "upgrade_opportunities_count": self.upgrade_opportunities_count,
        }


class CodeComparisonEngine:
    """
    Engine for comparing billed codes with AI suggestions
    Calculates incremental revenue opportunities
    """

    def __init__(self):
        self.cpt_rates = CPT_REIMBURSEMENT_RATES
        self.icd10_impact = ICD10_REIMBURSEMENT_IMPACT
        logger.info("Code comparison engine initialized")

    def compare_codes(
        self,
        billed_codes: List[Dict[str, str]],
        ai_result: CodingSuggestionResult,
    ) -> ComparisonResult:
        """
        Compare billed codes with AI suggestions

        Args:
            billed_codes: List of billed code dicts
            ai_result: AI analysis result

        Returns:
            ComparisonResult with revenue analysis
        """
        logger.info(
            "Starting code comparison",
            billed_codes_count=len(billed_codes),
            suggested_codes_count=len(ai_result.suggested_codes),
            additional_codes_count=len(ai_result.additional_codes),
        )

        comparisons = []

        # Calculate billed revenue
        total_billed_revenue = self._calculate_total_revenue(billed_codes)

        # Compare each suggested code
        for suggested in ai_result.additional_codes:
            comparison = self._compare_single_code(billed_codes, suggested)
            comparisons.append(comparison)

        # Calculate suggested revenue (billed + incremental)
        incremental_revenue = sum(c.revenue_impact for c in comparisons)
        total_suggested_revenue = total_billed_revenue + incremental_revenue

        # Calculate weighted average confidence
        if comparisons:
            confidence_score = sum(
                c.confidence * c.revenue_impact for c in comparisons
            ) / sum(c.revenue_impact for c in comparisons) if incremental_revenue > 0 else 0
        else:
            confidence_score = 0.0

        # Count opportunities
        new_codes_count = sum(1 for c in comparisons if c.comparison_type == "new")
        upgrade_opportunities_count = sum(
            1 for c in comparisons if c.comparison_type == "upgrade"
        )

        result = ComparisonResult(
            comparisons=comparisons,
            total_billed_revenue=total_billed_revenue,
            total_suggested_revenue=total_suggested_revenue,
            incremental_revenue=incremental_revenue,
            confidence_score=confidence_score,
            new_codes_count=new_codes_count,
            upgrade_opportunities_count=upgrade_opportunities_count,
        )

        logger.info(
            "Code comparison completed",
            total_billed=total_billed_revenue,
            incremental=incremental_revenue,
            new_codes=new_codes_count,
            upgrades=upgrade_opportunities_count,
        )

        return result

    def _compare_single_code(
        self,
        billed_codes: List[Dict[str, str]],
        suggested: CodeSuggestion,
    ) -> CodeComparison:
        """Compare a single suggested code against billed codes"""

        # Extract billed code strings
        billed_code_strings = [c["code"] for c in billed_codes]

        # Check if code was already billed
        if suggested.code in billed_code_strings:
            # Code was already billed - no revenue impact
            return CodeComparison(
                billed_code=suggested.code,
                suggested_code=suggested.code,
                code_type=suggested.code_type,
                comparison_type="match",
                revenue_impact=0.0,
                confidence=suggested.confidence,
                justification=suggested.justification,
                supporting_text=suggested.supporting_text,
            )

        # Check for upgrade opportunity (e.g., 99213 -> 99214)
        upgrade_from = self._find_upgrade_opportunity(
            billed_code_strings, suggested.code, suggested.code_type
        )

        if upgrade_from:
            billed_revenue = self._get_code_revenue(upgrade_from, suggested.code_type)
            suggested_revenue = self._get_code_revenue(suggested.code, suggested.code_type)
            revenue_impact = suggested_revenue - billed_revenue

            return CodeComparison(
                billed_code=upgrade_from,
                suggested_code=suggested.code,
                code_type=suggested.code_type,
                comparison_type="upgrade",
                revenue_impact=max(0, revenue_impact),
                confidence=suggested.confidence,
                justification=f"Upgrade from {upgrade_from}: {suggested.justification}",
                supporting_text=suggested.supporting_text,
            )

        # New code (not billed)
        revenue_impact = self._get_code_revenue(suggested.code, suggested.code_type)

        return CodeComparison(
            billed_code=None,
            suggested_code=suggested.code,
            code_type=suggested.code_type,
            comparison_type="new",
            revenue_impact=revenue_impact,
            confidence=suggested.confidence,
            justification=suggested.justification,
            supporting_text=suggested.supporting_text,
        )

    def _find_upgrade_opportunity(
        self,
        billed_codes: List[str],
        suggested_code: str,
        code_type: str,
    ) -> Optional[str]:
        """
        Find if suggested code is an upgrade from a billed code

        E.g., 99213 billed, 99214 suggested = upgrade
        """
        if code_type != "CPT":
            return None

        # Extract base code (E&M codes like 99213, 99214)
        match = re.match(r"(\d{5})", suggested_code)
        if not match:
            return None

        suggested_base = suggested_code[:4]  # e.g., "9921"

        # Look for same family with lower level
        for billed in billed_codes:
            billed_match = re.match(r"(\d{5})", billed)
            if not billed_match:
                continue

            billed_base = billed[:4]

            # Same family, different level
            if billed_base == suggested_base and billed < suggested_code:
                return billed

        return None

    def _calculate_total_revenue(self, codes: List[Dict[str, str]]) -> float:
        """Calculate total revenue from list of codes"""
        total = 0.0
        for code in codes:
            code_str = code["code"]
            code_type = code.get("code_type", "CPT")
            total += self._get_code_revenue(code_str, code_type)

        return total

    def _get_code_revenue(self, code: str, code_type: str) -> float:
        """Get revenue for a single code"""
        if code_type == "CPT":
            return self.cpt_rates.get(code, 50.0)  # Default $50 if not in table
        elif code_type == "ICD-10" or code_type == "ICD10":
            return self.icd10_impact.get(code, 5.0)  # Default $5 impact
        else:
            return 0.0

    def extract_supporting_snippets(
        self,
        clinical_note: str,
        search_terms: List[str],
        context_chars: int = 100,
    ) -> List[str]:
        """
        Extract text snippets from clinical note that support a code

        Args:
            clinical_note: Full clinical note text
            search_terms: Terms to search for
            context_chars: Characters before/after match

        Returns:
            List of text snippets
        """
        snippets = []

        for term in search_terms:
            # Case-insensitive search
            pattern = re.compile(re.escape(term), re.IGNORECASE)
            matches = pattern.finditer(clinical_note)

            for match in matches:
                start = max(0, match.start() - context_chars)
                end = min(len(clinical_note), match.end() + context_chars)

                snippet = clinical_note[start:end].strip()

                # Add ellipsis if truncated
                if start > 0:
                    snippet = "..." + snippet
                if end < len(clinical_note):
                    snippet = snippet + "..."

                snippets.append(snippet)

        return list(set(snippets))  # Remove duplicates

    def filter_duplicate_codes(
        self,
        code_suggestions: List[CodeSuggestion],
    ) -> List[CodeSuggestion]:
        """
        Filter out duplicate code suggestions

        Keep the one with highest confidence
        """
        seen_codes = {}

        for suggestion in code_suggestions:
            key = suggestion.code

            if key not in seen_codes:
                seen_codes[key] = suggestion
            else:
                # Keep higher confidence
                if suggestion.confidence > seen_codes[key].confidence:
                    seen_codes[key] = suggestion

        return list(seen_codes.values())

    def validate_code_format(self, code: str, code_type: str) -> bool:
        """
        Validate code format

        CPT: 5 digits
        ICD-10: Letter + 2-3 digits + optional decimal + 1-4 chars
        """
        if code_type == "CPT":
            return bool(re.match(r"^\d{5}$", code))
        elif code_type in ["ICD-10", "ICD10"]:
            return bool(re.match(r"^[A-Z]\d{2,3}(\.\w{1,4})?$", code))
        else:
            return False


# Export singleton instance
code_comparison_engine = CodeComparisonEngine()
