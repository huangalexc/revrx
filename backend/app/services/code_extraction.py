"""
Billed Code Extraction Service
Extracts already-billed codes from clinical note text using regex patterns
"""

import re
from typing import List, Dict, Optional
import structlog

logger = structlog.get_logger(__name__)

# Regex patterns for common billing code formats
# CPT codes: 5-digit numeric codes (e.g., 99393, 99214)
CPT_PATTERN = r'\b(99[0-9]{3}|[0-9]{5})\b'

# ICD-10 codes: Letter + 2 digits + optional dot + 0-4 alphanumeric (e.g., Z00.129, Z00129)
ICD10_PATTERN = r'\b([A-TV-Z][0-9]{2}\.?[0-9A-TV-Z]{0,4})\b'

# HCPCS codes: Letter + 4 digits (e.g., J0585, A0426)
HCPCS_PATTERN = r'\b([A-Z][0-9]{4})\b'

# Context patterns to identify billed vs suggested codes
BILLED_CONTEXT_PATTERNS = [
    r'billed',
    r'billing',
    r'submitted',
    r'charged',
    r'invoiced',
    r'claim',
    r'already coded',
    r'previously coded',
]


def _is_valid_cpt(code: str) -> bool:
    """Validate CPT code format"""
    if not code.isdigit():
        return False
    if len(code) != 5:
        return False
    # Common CPT code ranges
    code_int = int(code)
    return (
        (code_int >= 99201 and code_int <= 99499) or  # E&M codes
        (code_int >= 10000 and code_int <= 69999) or  # Surgery
        (code_int >= 70000 and code_int <= 79999) or  # Radiology
        (code_int >= 80000 and code_int <= 89999) or  # Pathology
        (code_int >= 90000 and code_int <= 99607)     # Medicine
    )


def _is_valid_icd10(code: str) -> bool:
    """Validate ICD-10 code format"""
    # Remove dot for validation
    clean_code = code.replace(".", "")

    if len(clean_code) < 3:
        return False

    # First character must be letter (A-Z, except U which is reserved)
    if not clean_code[0].isalpha() or clean_code[0] == 'U':
        return False

    # Second and third characters must be digits
    if not clean_code[1:3].isdigit():
        return False

    return True


def _normalize_icd10(code: str) -> str:
    """Normalize ICD-10 code (remove dots, uppercase)"""
    return code.replace(".", "").upper()


def _extract_codes_with_context(
    clinical_text: str,
    pattern: str,
    code_type: str,
    validator: Optional[callable] = None
) -> List[Dict]:
    """
    Extract codes with surrounding context to determine if they are billed codes

    Args:
        clinical_text: Clinical note text
        pattern: Regex pattern for code extraction
        code_type: Code type (CPT, ICD10, HCPCS)
        validator: Optional validation function

    Returns:
        List of dicts with code, code_type, is_billed, context
    """
    codes = []

    # Search for codes with surrounding context (50 chars before/after)
    for match in re.finditer(pattern, clinical_text, re.IGNORECASE):
        code = match.group(1)

        # Validate code if validator provided
        if validator and not validator(code):
            continue

        # Extract context (50 chars before and after)
        start = max(0, match.start() - 50)
        end = min(len(clinical_text), match.end() + 50)
        context = clinical_text[start:end]

        # Check if context suggests this is a billed code
        is_billed = any(
            re.search(pattern, context, re.IGNORECASE)
            for pattern in BILLED_CONTEXT_PATTERNS
        )

        codes.append({
            "code": code,
            "code_type": code_type,
            "is_billed": is_billed,
            "context": context,
        })

    return codes


async def extract_billed_codes(
    clinical_text: str,
    encounter_id: str,
    only_billed: bool = True
) -> List[Dict]:
    """
    Extract billed codes from clinical text using regex patterns

    Args:
        clinical_text: Clinical note text
        encounter_id: Encounter ID for logging
        only_billed: If True, only return codes identified as billed (default: True)

    Returns:
        List of dicts with keys: code, code_type, description (optional)
    """
    logger.info(
        "Starting billed code extraction",
        encounter_id=encounter_id,
        text_length=len(clinical_text),
        only_billed=only_billed
    )

    all_codes = []

    # Extract CPT codes
    cpt_codes = _extract_codes_with_context(
        clinical_text,
        CPT_PATTERN,
        "CPT",
        validator=_is_valid_cpt
    )
    all_codes.extend(cpt_codes)

    # Extract ICD-10 codes
    icd10_codes = _extract_codes_with_context(
        clinical_text,
        ICD10_PATTERN,
        "ICD10",
        validator=_is_valid_icd10
    )
    # Normalize ICD-10 codes
    for code_dict in icd10_codes:
        code_dict["code"] = _normalize_icd10(code_dict["code"])
    all_codes.extend(icd10_codes)

    # Extract HCPCS codes
    hcpcs_codes = _extract_codes_with_context(
        clinical_text,
        HCPCS_PATTERN,
        "HCPCS"
    )
    all_codes.extend(hcpcs_codes)

    # Filter to only billed codes if requested
    if only_billed:
        all_codes = [c for c in all_codes if c["is_billed"]]

    # Deduplicate by (code, code_type)
    seen = set()
    unique_codes = []
    for code_dict in all_codes:
        key = (code_dict["code"], code_dict["code_type"])
        if key not in seen:
            seen.add(key)
            unique_codes.append({
                "code": code_dict["code"],
                "code_type": code_dict["code_type"],
                "description": None,  # Will be populated later if needed
            })

    logger.info(
        "Billed codes extracted",
        encounter_id=encounter_id,
        total_count=len(unique_codes),
        cpt_count=len([c for c in unique_codes if c["code_type"] == "CPT"]),
        icd10_count=len([c for c in unique_codes if c["code_type"] == "ICD10"]),
        hcpcs_count=len([c for c in unique_codes if c["code_type"] == "HCPCS"]),
    )

    return unique_codes


async def extract_all_codes(
    clinical_text: str,
    encounter_id: str
) -> Dict[str, List[Dict]]:
    """
    Extract all codes from clinical text, separating billed vs suggested

    Returns:
        Dict with keys: "billed" and "suggested", each containing list of codes
    """
    logger.info(
        "Extracting all codes (billed + suggested)",
        encounter_id=encounter_id,
        text_length=len(clinical_text)
    )

    # Extract all codes with context
    all_codes = []

    # CPT codes
    cpt_codes = _extract_codes_with_context(
        clinical_text,
        CPT_PATTERN,
        "CPT",
        validator=_is_valid_cpt
    )
    all_codes.extend(cpt_codes)

    # ICD-10 codes
    icd10_codes = _extract_codes_with_context(
        clinical_text,
        ICD10_PATTERN,
        "ICD10",
        validator=_is_valid_icd10
    )
    for code_dict in icd10_codes:
        code_dict["code"] = _normalize_icd10(code_dict["code"])
    all_codes.extend(icd10_codes)

    # HCPCS codes
    hcpcs_codes = _extract_codes_with_context(
        clinical_text,
        HCPCS_PATTERN,
        "HCPCS"
    )
    all_codes.extend(hcpcs_codes)

    # Separate billed vs suggested
    billed = []
    suggested = []

    # Deduplicate
    seen_billed = set()
    seen_suggested = set()

    for code_dict in all_codes:
        code_info = {
            "code": code_dict["code"],
            "code_type": code_dict["code_type"],
            "description": None,
        }

        key = (code_dict["code"], code_dict["code_type"])

        if code_dict["is_billed"]:
            if key not in seen_billed:
                seen_billed.add(key)
                billed.append(code_info)
        else:
            if key not in seen_suggested:
                seen_suggested.add(key)
                suggested.append(code_info)

    logger.info(
        "All codes extracted and categorized",
        encounter_id=encounter_id,
        billed_count=len(billed),
        suggested_count=len(suggested)
    )

    return {
        "billed": billed,
        "suggested": suggested,
    }
