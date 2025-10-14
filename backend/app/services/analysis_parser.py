"""
Analysis Response Parser Service

Parses LLM responses for extended analysis features:
- Documentation Quality
- Denial Risk
- Revenue Comparison
- Modifier Suggestions
- Charge Capture
- Audit Log Data
"""

from typing import List, Dict, Any, Optional
import structlog
from pydantic import BaseModel, Field, field_validator

logger = structlog.get_logger(__name__)


# ============================================================================
# Pydantic Models for Response Parsing
# ============================================================================

class MissingDocumentationItem(BaseModel):
    """Parsed missing documentation item"""
    section: str
    issue: str
    suggestion: str
    priority: Optional[str] = None

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v and v not in ['High', 'Medium', 'Low']:
            return None
        return v


class DenialRiskItem(BaseModel):
    """Parsed denial risk assessment"""
    code: str
    riskLevel: str = Field(alias='risk_level')
    reasons: List[str]
    addressed: bool
    justification: str

    @field_validator('riskLevel')
    @classmethod
    def validate_risk_level(cls, v):
        if v not in ['Low', 'Medium', 'High']:
            raise ValueError(f'Invalid risk level: {v}')
        return v


class RevenueComparisonData(BaseModel):
    """Parsed revenue comparison"""
    billedCodes: List[str] = Field(default_factory=list, alias='billed_codes')
    billedRVUs: float = Field(default=0.0, alias='billed_rvus')
    suggestedCodes: List[str] = Field(default_factory=list, alias='suggested_codes')
    suggestedRVUs: float = Field(default=0.0, alias='suggested_rvus')
    missedRevenue: float = Field(default=0.0, alias='missed_revenue')
    percentDifference: float = Field(default=0.0, alias='percent_difference')


class ModifierSuggestionItem(BaseModel):
    """Parsed modifier suggestion"""
    code: str
    modifier: str
    justification: str
    isNewSuggestion: bool = Field(alias='is_new_suggestion')


class UncapturedServiceItem(BaseModel):
    """Parsed uncaptured service"""
    service: str
    location: str
    suggestedCodes: List[str] = Field(alias='suggested_codes')
    priority: str
    estimatedRVUs: Optional[float] = Field(None, alias='estimated_rvus')

    @field_validator('priority')
    @classmethod
    def validate_priority(cls, v):
        if v not in ['High', 'Medium', 'Low']:
            raise ValueError(f'Invalid priority: {v}')
        return v


class AuditLogMetadata(BaseModel):
    """Audit log metadata"""
    providerId: str = Field(alias='provider_id')
    patientId: str = Field(alias='patient_id')
    dateOfService: str = Field(alias='date_of_service')
    encounterType: str = Field(alias='encounter_type')
    analysisTimestamp: str = Field(alias='analysis_timestamp')


class AuditSuggestedCode(BaseModel):
    """Audit suggested code"""
    code: str
    description: str
    justification: str
    chartReference: str = Field(alias='chart_reference')


class AuditJustifications(BaseModel):
    """Audit justifications"""
    assessment: str
    qualityNotes: Optional[List[str]] = Field(None, alias='quality_notes')
    riskNotes: Optional[List[str]] = Field(None, alias='risk_notes')


class AuditLogData(BaseModel):
    """Complete audit log"""
    metadata: AuditLogMetadata
    suggestedCodes: List[AuditSuggestedCode] = Field(alias='suggested_codes')
    justifications: AuditJustifications
    timestamp: str


# ============================================================================
# Analysis Parser Service
# ============================================================================

class AnalysisParserService:
    """
    Service for parsing LLM responses into structured feature data
    """

    def __init__(self):
        logger.info("Analysis Parser Service initialized")

    def parse_missing_documentation(
        self,
        raw_data: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Parse missing documentation from LLM response

        Args:
            raw_data: Raw missing_documentation array from LLM

        Returns:
            List of parsed and validated missing documentation items
        """
        if not raw_data:
            return []

        parsed_items = []
        for item in raw_data:
            try:
                parsed = MissingDocumentationItem(**item)
                parsed_items.append(parsed.model_dump(by_alias=False))
            except Exception as e:
                logger.warning(
                    "Failed to parse missing documentation item",
                    item=item,
                    error=str(e)
                )
                continue

        logger.info(
            "Parsed missing documentation",
            count=len(parsed_items)
        )
        return parsed_items

    def parse_denial_risks(
        self,
        raw_data: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Parse denial risk assessments from LLM response

        Args:
            raw_data: Raw denial_risks array from LLM

        Returns:
            List of parsed and validated denial risk items
        """
        if not raw_data:
            return []

        parsed_items = []
        for item in raw_data:
            try:
                # Handle both snake_case and camelCase from LLM
                normalized_item = {
                    'code': item.get('code'),
                    'risk_level': item.get('riskLevel') or item.get('risk_level'),
                    'reasons': item.get('reasons', []),
                    'addressed': item.get('addressed', False),
                    'justification': item.get('justification', ''),
                }
                parsed = DenialRiskItem(**normalized_item)
                parsed_items.append(parsed.model_dump(by_alias=False))
            except Exception as e:
                logger.warning(
                    "Failed to parse denial risk item",
                    item=item,
                    error=str(e)
                )
                continue

        logger.info(
            "Parsed denial risks",
            count=len(parsed_items)
        )
        return parsed_items

    def parse_revenue_comparison(
        self,
        raw_data: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse revenue comparison from LLM response

        Args:
            raw_data: Raw revenue_comparison dict from LLM

        Returns:
            Parsed and validated revenue comparison or None
        """
        if not raw_data:
            return None

        try:
            parsed = RevenueComparisonData(**raw_data)
            logger.info(
                "Parsed revenue comparison",
                missed_revenue=parsed.missedRevenue
            )
            return parsed.model_dump(by_alias=False)
        except Exception as e:
            logger.warning(
                "Failed to parse revenue comparison",
                data=raw_data,
                error=str(e)
            )
            return None

    def parse_modifier_suggestions(
        self,
        raw_data: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Parse modifier suggestions from LLM response

        Args:
            raw_data: Raw modifier_suggestions array from LLM

        Returns:
            List of parsed and validated modifier suggestions
        """
        if not raw_data:
            return []

        parsed_items = []
        for item in raw_data:
            try:
                normalized_item = {
                    'code': item.get('code'),
                    'modifier': item.get('modifier'),
                    'justification': item.get('justification', ''),
                    'is_new_suggestion': item.get('isNewSuggestion') or item.get('is_new_suggestion', True),
                }
                parsed = ModifierSuggestionItem(**normalized_item)
                parsed_items.append(parsed.model_dump(by_alias=False))
            except Exception as e:
                logger.warning(
                    "Failed to parse modifier suggestion",
                    item=item,
                    error=str(e)
                )
                continue

        logger.info(
            "Parsed modifier suggestions",
            count=len(parsed_items)
        )
        return parsed_items

    def parse_uncaptured_services(
        self,
        raw_data: Optional[List[Dict[str, Any]]]
    ) -> List[Dict[str, Any]]:
        """
        Parse uncaptured services from LLM response

        Args:
            raw_data: Raw uncaptured_services array from LLM

        Returns:
            List of parsed and validated uncaptured services
        """
        if not raw_data:
            return []

        parsed_items = []
        for item in raw_data:
            try:
                normalized_item = {
                    'service': item.get('service'),
                    'location': item.get('location'),
                    'suggested_codes': item.get('suggestedCodes') or item.get('suggested_codes', []),
                    'priority': item.get('priority', 'Medium'),
                    'estimated_rvus': item.get('estimatedRVUs') or item.get('estimated_rvus'),
                }
                parsed = UncapturedServiceItem(**normalized_item)
                parsed_items.append(parsed.model_dump(by_alias=False))
            except Exception as e:
                logger.warning(
                    "Failed to parse uncaptured service",
                    item=item,
                    error=str(e)
                )
                continue

        logger.info(
            "Parsed uncaptured services",
            count=len(parsed_items)
        )
        return parsed_items

    def parse_audit_log(
        self,
        raw_data: Optional[Dict[str, Any]],
        fallback_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Parse audit log data from LLM response

        Args:
            raw_data: Raw audit_log dict from LLM
            fallback_metadata: Fallback metadata if not in LLM response

        Returns:
            Parsed and validated audit log or None
        """
        if not raw_data:
            return None

        try:
            # Use fallback metadata if not provided in response
            if 'metadata' not in raw_data and fallback_metadata:
                raw_data['metadata'] = fallback_metadata

            parsed = AuditLogData(**raw_data)
            logger.info(
                "Parsed audit log",
                codes_count=len(parsed.suggestedCodes)
            )
            return parsed.model_dump(by_alias=False)
        except Exception as e:
            logger.warning(
                "Failed to parse audit log",
                error=str(e)
            )
            return None

    def parse_extended_analysis(
        self,
        llm_response: Dict[str, Any],
        fallback_audit_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Parse complete extended analysis response from LLM

        Args:
            llm_response: Complete LLM JSON response
            fallback_audit_metadata: Optional metadata for audit log

        Returns:
            Dict with all parsed features (None for missing features)
        """
        logger.info("Parsing extended analysis response")

        result = {
            'missing_documentation': self.parse_missing_documentation(
                llm_response.get('missing_documentation')
            ),
            'denial_risks': self.parse_denial_risks(
                llm_response.get('denial_risks')
            ),
            'revenue_comparison': self.parse_revenue_comparison(
                llm_response.get('revenue_comparison')
            ),
            'modifier_suggestions': self.parse_modifier_suggestions(
                llm_response.get('modifier_suggestions')
            ),
            'uncaptured_services': self.parse_uncaptured_services(
                llm_response.get('uncaptured_services')
            ),
            'audit_log': self.parse_audit_log(
                llm_response.get('audit_log'),
                fallback_audit_metadata
            ),
        }

        # Log summary
        logger.info(
            "Extended analysis parsed",
            missing_doc_count=len(result['missing_documentation']),
            denial_risk_count=len(result['denial_risks']),
            has_revenue_comparison=result['revenue_comparison'] is not None,
            modifier_count=len(result['modifier_suggestions']),
            uncaptured_count=len(result['uncaptured_services']),
            has_audit_log=result['audit_log'] is not None,
        )

        return result


# Export singleton instance
analysis_parser = AnalysisParserService()
