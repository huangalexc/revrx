"""
OpenAI Service for Medical Coding Suggestions
Handles GPT-4 API calls for analyzing de-identified clinical notes
"""

from typing import List, Dict, Any, Optional
import structlog
import json
from openai import AsyncOpenAI, OpenAIError, RateLimitError, APITimeoutError
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from app.core.config import settings
from app.services.prompt_templates import prompt_templates


logger = structlog.get_logger(__name__)


class BilledCode:
    """Represents a code that was already billed (extracted from clinical note)"""

    def __init__(
        self,
        code: str,
        code_type: str,
        description: Optional[str] = None,
    ):
        self.code = code
        self.code_type = code_type  # "CPT" or "ICD-10"
        self.description = description

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "code_type": self.code_type,
            "description": self.description,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "BilledCode":
        return BilledCode(
            code=data["code"],
            code_type=data["code_type"],
            description=data.get("description"),
        )


class CodeSuggestion:
    """Represents a suggested medical billing code"""

    def __init__(
        self,
        code: str,
        code_type: str,
        description: str,
        justification: str,
        confidence: float,
        supporting_text: List[str],
        confidence_reason: Optional[str] = None,
    ):
        self.code = code
        self.code_type = code_type  # "CPT" or "ICD-10"
        self.description = description
        self.justification = justification
        self.confidence = confidence  # 0.0 to 1.0
        self.confidence_reason = confidence_reason  # Explanation for confidence score
        self.supporting_text = supporting_text

    def to_dict(self) -> Dict[str, Any]:
        return {
            "code": self.code,
            "code_type": self.code_type,
            "description": self.description,
            "justification": self.justification,
            "confidence": self.confidence,
            "confidence_reason": self.confidence_reason,
            "supporting_text": self.supporting_text,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "CodeSuggestion":
        return CodeSuggestion(
            code=data["code"],
            code_type=data["code_type"],
            description=data["description"],
            justification=data["justification"],
            confidence=data["confidence"],
            supporting_text=data.get("supporting_text", []),
            confidence_reason=data.get("confidence_reason"),
        )


class CodingSuggestionResult:
    """Result from AI coding analysis with expanded features"""

    def __init__(
        self,
        suggested_codes: List[CodeSuggestion],
        billed_codes: List[BilledCode],
        additional_codes: List[CodeSuggestion],
        missing_documentation: List[Dict[str, Any]],
        denial_risks: List[Dict[str, Any]],
        rvu_analysis: Dict[str, Any],
        modifier_suggestions: List[Dict[str, Any]],
        uncaptured_services: List[Dict[str, Any]],
        audit_metadata: Dict[str, Any],
        total_incremental_revenue: float,
        processing_time_ms: int,
        model_used: str,
        tokens_used: int,
        cost_usd: float,
    ):
        self.suggested_codes = suggested_codes
        self.billed_codes = billed_codes
        self.additional_codes = additional_codes
        # Expanded features
        self.missing_documentation = missing_documentation
        self.denial_risks = denial_risks
        self.rvu_analysis = rvu_analysis
        self.modifier_suggestions = modifier_suggestions
        self.uncaptured_services = uncaptured_services
        self.audit_metadata = audit_metadata
        # Metrics
        self.total_incremental_revenue = total_incremental_revenue
        self.processing_time_ms = processing_time_ms
        self.model_used = model_used
        self.tokens_used = tokens_used
        self.cost_usd = cost_usd

    def to_dict(self) -> Dict[str, Any]:
        return {
            "suggested_codes": [c.to_dict() for c in self.suggested_codes],
            "billed_codes": [c.to_dict() for c in self.billed_codes],
            "additional_codes": [c.to_dict() for c in self.additional_codes],
            "missing_documentation": self.missing_documentation,
            "denial_risks": self.denial_risks,
            "rvu_analysis": self.rvu_analysis,
            "modifier_suggestions": self.modifier_suggestions,
            "uncaptured_services": self.uncaptured_services,
            "audit_metadata": self.audit_metadata,
            "total_incremental_revenue": self.total_incremental_revenue,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd,
        }


class OpenAIService:
    """
    Service for analyzing clinical notes using OpenAI GPT-4

    IMPORTANT: Only processes de-identified text (no PHI exposure)
    """

    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        # Use GPT-4o-mini for all operations (cost optimization)
        self.model = "gpt-4o-mini"
        self.mini_model = "gpt-4o-mini"
        self.max_tokens = settings.OPENAI_MAX_TOKENS
        self.temperature = settings.OPENAI_TEMPERATURE

        # GPT-4o-mini costs (as of 2025)
        self.mini_cost_per_1m_input_tokens = 0.15  # $0.15 per 1M tokens
        self.mini_cost_per_1m_output_tokens = 0.60  # $0.60 per 1M tokens

        logger.info(
            "OpenAI service initialized",
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )

    def _create_system_prompt(self) -> str:
        """Create system prompt using expanded feature template"""
        return prompt_templates.get_system_prompt()

    def _create_user_prompt(
        self,
        clinical_note: str,
        billed_codes: List[Dict[str, str]],
        extracted_icd10_codes: List[Dict[str, any]] = None,
        snomed_to_cpt_suggestions: List[Dict[str, any]] = None,
        encounter_type: str = None
    ) -> str:
        """
        Create user prompt using expanded feature template

        Args:
            clinical_note: De-identified clinical text
            billed_codes: List of codes already billed
            extracted_icd10_codes: Filtered ICD-10 codes
            snomed_to_cpt_suggestions: CPT codes from SNOMED crosswalk
            encounter_type: Type of encounter
        """
        return prompt_templates.get_user_prompt(
            clinical_note,
            billed_codes,
            extracted_icd10_codes,
            snomed_to_cpt_suggestions,
            encounter_type
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
    )

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate API call cost in USD (now using GPT-4o-mini pricing)"""
        input_cost = (input_tokens / 1_000_000) * self.mini_cost_per_1m_input_tokens
        output_cost = (output_tokens / 1_000_000) * self.mini_cost_per_1m_output_tokens
        return round(input_cost + output_cost, 8)

    def _calculate_mini_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate GPT-4o-mini API call cost in USD"""
        input_cost = (input_tokens / 1_000_000) * self.mini_cost_per_1m_input_tokens
        output_cost = (output_tokens / 1_000_000) * self.mini_cost_per_1m_output_tokens
        return round(input_cost + output_cost, 8)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
    )
    async def filter_clinical_relevance(
        self,
        deidentified_text: str,
    ) -> Dict[str, Any]:
        """
        Filter clinical text to keep only billing-relevant content.

        Uses GPT-4o-mini (cheapest model) to extract clinically relevant assessment
        and billing context, dropping vitals, screeners, growth charts, patient education, etc.

        Args:
            deidentified_text: De-identified clinical text (after PHI stripping)

        Returns:
            Dict with:
                - filtered_text: Clinically relevant text for coding
                - removed_sections: List of section types removed
                - tokens_used: Token count
                - cost_usd: API cost
                - processing_time_ms: Processing time

        Raises:
            OpenAIError: If API call fails after retries
        """
        import time
        start_time = time.time()

        logger.info(
            "Filtering clinical text for relevance",
            input_length=len(deidentified_text),
        )

        try:
            # Create filtering prompt
            system_prompt = """You are a medical billing coding assistant. Your task is to extract ONLY the clinically relevant portions of a clinical note that are necessary for medical billing and coding.

KEEP:
- Chief complaint and reason for visit
- History of present illness (HPI)
- Review of systems (ROS) - ONLY positive/abnormal findings
- Physical examination - ONLY abnormal findings
- Assessment and diagnosis
- Treatment plan and procedures performed
- Medical decision making
- Prescriptions and orders
- Follow-up plans
- Abnormal lab values

REMOVE:
- Vital signs (BP, HR, temp, etc.) - unless abnormal and clinically significant
- Growth charts and percentiles
- Standardized screening tools and questionnaires (PHQ-9, GAD-7, etc.)
- Patient education materials
- Administrative notes and billing reminders
- Template boilerplate text
- Normal lab values
- Vaccine administration records (unless part of today's visit)
- **Negated symptoms and findings** (e.g., "No fever", "Denies chest pain", "No shortness of breath")
- **Normal physical examination findings** (e.g., "Normocephalic", "Clear to auscultation", "Regular rate and rhythm")
- **Negative review of systems** (entire sections with only negated findings can be omitted)

For well visits with no abnormal findings, keep only:
- Chief complaint
- Brief HPI
- Assessment (e.g., "well child check, no abnormal findings")
- Plan (procedures, orders, follow-up)

Return ONLY the filtered text that is relevant for medical coding. Preserve the clinical narrative and context."""

            user_prompt = f"""Filter this de-identified clinical note to keep only billing-relevant content.

NOTE: PHI has been replaced with numbered placeholders (e.g., [NAME_1], [NAME_2], [DATE_1], [DATE_2]).

{deidentified_text}

Return a JSON object with:
{{
  "filtered_text": "the filtered clinical text",
  "encounter_type": "the type of encounter (e.g., 'well child visit', 'follow-up', 'new patient', 'post-op', 'urgent care', 'annual physical', 'sick visit', etc.)",
  "provider_placeholder": "the placeholder token for the provider/clinician who rendered the service (e.g., 'NAME_2'), or null if not identifiable",
  "service_date_placeholder": "the placeholder token for the date of service (e.g., 'DATE_3'), or null if not identifiable",
  "billed_codes": [
    {{
      "code": "the code (e.g., '99393', 'Z00.129')",
      "code_type": "CPT | ICD10 | HCPCS",
      "description": "brief description if available"
    }}
  ]
}}

To identify the provider: Look for names associated with signatures, "Added by:", "Provider:", job titles (MD, PA, CPNP, etc.), or clinical documentation.
To identify service date: Look for dates associated with the encounter, visit date, or "Signed on", not birth dates.

IMPORTANT - Billed Codes Extraction:
- Extract codes that were ACTUALLY BILLED/CHARGED for this encounter
- Look for sections like "Billing Codes", "Codes Used", "Billed:", "Charged:", "Submitted Codes"
- Include CPT procedure codes (5-digit numbers like 99393, 99214)
- Include ICD-10 diagnosis codes (format: Letter + 2-3 digits like Z00.129, E11.9)
- Include HCPCS codes if present (Letter + 4 digits like J0585)
- DO NOT include codes from reference/legend sections (e.g., "ICD 10 Billing Codes - Reference")
- DO NOT include codes from educational materials or billing guidelines
- Only extract codes explicitly stated as billed/charged/submitted for THIS encounter
- If no billed codes can be identified with certainty, return an empty array
"""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ]

            # Call OpenAI API with GPT-4o-mini
            response = await self.client.chat.completions.create(
                model=self.mini_model,
                messages=messages,
                max_tokens=4000,  # Allow sufficient output
                temperature=0.1,  # Low temperature for consistent filtering
                response_format={"type": "json_object"},  # Request JSON response
            )

            # Extract response
            response_content = response.choices[0].message.content.strip()
            usage = response.usage

            # Parse JSON response
            import json
            try:
                response_data = json.loads(response_content)
                filtered_text = response_data.get("filtered_text", response_content)
                encounter_type = response_data.get("encounter_type", None)
                provider_placeholder = response_data.get("provider_placeholder", None)
                service_date_placeholder = response_data.get("service_date_placeholder", None)
                billed_codes = response_data.get("billed_codes", [])
            except json.JSONDecodeError:
                # Fallback: treat as plain text
                filtered_text = response_content
                encounter_type = None
                provider_placeholder = None
                service_date_placeholder = None
                billed_codes = []
                logger.warning("Failed to parse JSON response from filtering, using as plain text")

            # Calculate processing time
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Calculate cost
            cost_usd = self._calculate_mini_cost(usage.prompt_tokens, usage.completion_tokens)

            # Analyze what was removed
            original_length = len(deidentified_text)
            filtered_length = len(filtered_text)
            reduction_pct = ((original_length - filtered_length) / original_length * 100) if original_length > 0 else 0

            result = {
                "filtered_text": filtered_text,
                "encounter_type": encounter_type,
                "provider_placeholder": provider_placeholder,
                "service_date_placeholder": service_date_placeholder,
                "billed_codes": billed_codes,
                "original_length": original_length,
                "filtered_length": filtered_length,
                "reduction_pct": round(reduction_pct, 1),
                "tokens_used": usage.total_tokens,
                "cost_usd": cost_usd,
                "processing_time_ms": processing_time_ms,
                "model_used": response.model,
            }

            logger.info(
                "Clinical text filtering completed",
                encounter_type=encounter_type,
                provider_placeholder=provider_placeholder,
                service_date_placeholder=service_date_placeholder,
                billed_codes_count=len(billed_codes),
                original_length=original_length,
                filtered_length=filtered_length,
                reduction_pct=round(reduction_pct, 1),
                tokens_used=usage.total_tokens,
                cost_usd=cost_usd,
                processing_time_ms=processing_time_ms,
            )

            return result

        except OpenAIError as e:
            logger.error("OpenAI API error during filtering", error=str(e))
            raise

        except Exception as e:
            logger.error("Unexpected error during filtering", error=str(e))
            raise

    async def batch_analyze(
        self,
        encounters: List[Dict[str, Any]],
        max_concurrent: int = 5,
    ) -> List[CodingSuggestionResult]:
        """
        Analyze multiple encounters concurrently (with rate limiting)

        Args:
            encounters: List of encounter dicts with 'clinical_note' and 'billed_codes'
            max_concurrent: Maximum concurrent API calls

        Returns:
            List of CodingSuggestionResult
        """
        import asyncio

        logger.info(
            "Starting batch analysis",
            encounter_count=len(encounters),
            max_concurrent=max_concurrent,
        )

        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)

        async def analyze_with_semaphore(encounter):
            async with semaphore:
                return await self.analyze_clinical_note(
                    clinical_note=encounter["clinical_note"],
                    billed_codes=encounter.get("billed_codes", []),
                )

        # Run concurrent analyses
        results = await asyncio.gather(
            *[analyze_with_semaphore(enc) for enc in encounters],
            return_exceptions=True,
        )

        # Filter out errors and log them
        successful_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "Batch analysis failed for encounter",
                    encounter_index=i,
                    error=str(result),
                )
            else:
                successful_results.append(result)

        logger.info(
            "Batch analysis completed",
            successful_count=len(successful_results),
            failed_count=len(results) - len(successful_results),
        )

        return successful_results

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((RateLimitError, APITimeoutError)),
    )
    async def analyze_clinical_note(
        self,
        clinical_note: str,
        billed_codes: List[Dict[str, str]],
        extracted_icd10_codes: List[Dict[str, any]] = None,
        snomed_to_cpt_suggestions: List[Dict[str, any]] = None,
        encounter_type: str = None
    ) -> CodingSuggestionResult:
        """
        2-Prompt approach for medical coding analysis

        Prompt 1: Code Identification & Suggestions
        Prompt 2: Quality & Compliance Analysis

        This approach improves reliability for complex encounters by:
        - Reducing token count per prompt (stays under 2000 tokens response)
        - Better error isolation
        - Clearer logical separation

        Args:
            clinical_note: De-identified clinical text
            billed_codes: List of already billed codes
            extracted_icd10_codes: Filtered ICD-10 codes from AWS Comprehend
            snomed_to_cpt_suggestions: CPT codes from SNOMED crosswalk
            encounter_type: Type of encounter

        Returns:
            CodingSuggestionResult with complete analysis

        Raises:
            OpenAIError: If API calls fail after retries
        """
        import time
        from app.services.prompt_templates import prompt_templates

        start_time = time.time()
        total_tokens = 0
        total_cost = 0.0

        logger.info(
            "Starting 2-prompt clinical note analysis",
            note_length=len(clinical_note),
            billed_codes_count=len(billed_codes),
            extracted_icd10_count=len(extracted_icd10_codes) if extracted_icd10_codes else 0,
            snomed_cpt_suggestions_count=len(snomed_to_cpt_suggestions) if snomed_to_cpt_suggestions else 0,
            encounter_type=encounter_type
        )

        try:
            # ================================================================
            # PROMPT 1: CODE IDENTIFICATION & SUGGESTIONS
            # ================================================================
            logger.info("Executing Prompt 1: Code Identification")

            messages_p1 = [
                {"role": "system", "content": prompt_templates.get_coding_system_prompt()},
                {
                    "role": "user",
                    "content": prompt_templates.get_coding_user_prompt(
                        clinical_note,
                        billed_codes,
                        extracted_icd10_codes,
                        snomed_to_cpt_suggestions,
                        encounter_type
                    ),
                },
            ]

            response_p1 = await self.client.chat.completions.create(
                model=self.model,
                messages=messages_p1,
                max_tokens=2000,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            content_p1 = response_p1.choices[0].message.content
            usage_p1 = response_p1.usage
            result_p1 = json.loads(content_p1)

            total_tokens += usage_p1.total_tokens
            total_cost += self._calculate_cost(usage_p1.prompt_tokens, usage_p1.completion_tokens)

            logger.info(
                "Prompt 1 completed",
                billed_codes_count=len(result_p1.get("billed_codes", [])),
                suggested_codes_count=len(result_p1.get("suggested_codes", [])),
                additional_codes_count=len(result_p1.get("additional_codes", [])),
                uncaptured_services_count=len(result_p1.get("uncaptured_services", [])),
                tokens_used=usage_p1.total_tokens
            )

            # ================================================================
            # PROMPT 2: QUALITY & COMPLIANCE ANALYSIS
            # ================================================================
            logger.info("Executing Prompt 2: Quality & Compliance")

            messages_p2 = [
                {"role": "system", "content": prompt_templates.get_quality_system_prompt()},
                {
                    "role": "user",
                    "content": prompt_templates.get_quality_user_prompt(
                        clinical_note,
                        result_p1.get("billed_codes", []),
                        result_p1.get("suggested_codes", []),
                        result_p1.get("additional_codes", []),
                        encounter_type
                    ),
                },
            ]

            response_p2 = await self.client.chat.completions.create(
                model=self.model,
                messages=messages_p2,
                max_tokens=2000,
                temperature=self.temperature,
                response_format={"type": "json_object"},
            )

            content_p2 = response_p2.choices[0].message.content
            usage_p2 = response_p2.usage
            result_p2 = json.loads(content_p2)

            total_tokens += usage_p2.total_tokens
            total_cost += self._calculate_cost(usage_p2.prompt_tokens, usage_p2.completion_tokens)

            logger.info(
                "Prompt 2 completed",
                missing_documentation_count=len(result_p2.get("missing_documentation", [])),
                denial_risks_count=len(result_p2.get("denial_risks", [])),
                modifier_suggestions_count=len(result_p2.get("modifier_suggestions", [])),
                tokens_used=usage_p2.total_tokens
            )

            # ================================================================
            # COMBINE RESULTS
            # ================================================================
            processing_time_ms = int((time.time() - start_time) * 1000)

            # Parse billed codes
            extracted_billed_codes = [
                BilledCode(
                    code=c["code"],
                    code_type=c["code_type"],
                    description=c.get("description"),
                )
                for c in result_p1.get("billed_codes", [])
            ]

            # Parse suggested codes
            suggested_codes = [
                CodeSuggestion(
                    code=c["code"],
                    code_type=c["code_type"],
                    description=c["description"],
                    justification=c["justification"],
                    confidence=c["confidence"],
                    confidence_reason=c.get("confidence_reason"),
                    supporting_text=c.get("supporting_text", []),
                )
                for c in result_p1.get("suggested_codes", [])
            ]

            # Parse additional codes
            additional_codes = [
                CodeSuggestion(
                    code=c["code"],
                    code_type=c["code_type"],
                    description=c["description"],
                    justification=c["justification"],
                    confidence=c["confidence"],
                    confidence_reason=c.get("confidence_reason"),
                    supporting_text=c.get("supporting_text", []),
                )
                for c in result_p1.get("additional_codes", [])
            ]

            # Get quality/compliance data from Prompt 2
            missing_documentation = result_p2.get("missing_documentation", [])
            denial_risks = result_p2.get("denial_risks", [])
            rvu_analysis = result_p2.get("rvu_analysis", {
                "billed_codes_rvus": 0.0,
                "suggested_codes_rvus": 0.0,
                "incremental_rvus": 0.0,
                "billed_code_details": [],
                "suggested_code_details": []
            })
            modifier_suggestions = result_p2.get("modifier_suggestions", [])
            uncaptured_services = result_p1.get("uncaptured_services", [])
            audit_metadata = result_p2.get("audit_metadata", {
                "total_codes_identified": len(extracted_billed_codes) + len(suggested_codes),
                "high_confidence_codes": len([c for c in suggested_codes if c.confidence >= 0.8]),
                "documentation_quality_score": 0.0,
                "compliance_flags": [],
                "timestamp": ""
            })

            # Calculate total incremental revenue
            total_incremental_revenue = rvu_analysis.get("incremental_rvus", 0.0)

            result = CodingSuggestionResult(
                suggested_codes=suggested_codes,
                billed_codes=extracted_billed_codes,
                additional_codes=additional_codes,
                missing_documentation=missing_documentation,
                denial_risks=denial_risks,
                rvu_analysis=rvu_analysis,
                modifier_suggestions=modifier_suggestions,
                uncaptured_services=uncaptured_services,
                audit_metadata=audit_metadata,
                total_incremental_revenue=total_incremental_revenue,
                processing_time_ms=processing_time_ms,
                model_used=f"{response_p1.model} (2-prompt)",
                tokens_used=total_tokens,
                cost_usd=total_cost,
            )

            logger.info(
                "2-prompt analysis completed",
                billed_codes_count=len(extracted_billed_codes),
                suggested_codes_count=len(suggested_codes),
                additional_codes_count=len(additional_codes),
                missing_documentation_count=len(missing_documentation),
                denial_risks_count=len(denial_risks),
                modifier_suggestions_count=len(modifier_suggestions),
                uncaptured_services_count=len(uncaptured_services),
                incremental_rvus=rvu_analysis.get("incremental_rvus", 0.0),
                processing_time_ms=processing_time_ms,
                tokens_used=total_tokens,
                cost_usd=total_cost,
            )

            return result

        except json.JSONDecodeError as e:
            logger.error("Failed to parse OpenAI response in 2-prompt analysis", error=str(e))
            raise ValueError(f"Invalid JSON response from OpenAI: {str(e)}")

        except OpenAIError as e:
            logger.error("OpenAI API error in 2-prompt analysis", error=str(e))
            raise

        except Exception as e:
            logger.error("Unexpected error during 2-prompt analysis", error=str(e))
            raise


# Export singleton instance
openai_service = OpenAIService()
