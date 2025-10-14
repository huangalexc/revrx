"""
ICD-10 Code Filtering Utilities

Filters ICD-10 codes extracted by AWS Comprehend Medical to only include
codes related to actual diagnoses (excluding symptoms, signs, negations).

Uses fuzzy text matching to connect ICD-10 codes to diagnosis entities
from DetectEntitiesV2.
"""

from typing import List, Set
from difflib import SequenceMatcher
import structlog

logger = structlog.get_logger(__name__)


def get_diagnosis_entities(medical_entities) -> List:
    """
    Extract entities that represent diagnoses or symptoms from DetectEntitiesV2 results.

    Filters for:
    - Category: MEDICAL_CONDITION
    - Trait: DIAGNOSIS or SYMPTOM (allows billable conditions)
    - Excluding: NEGATION trait (filters out "No fever", "denies pain", etc.)

    This allows the LLM to handle the logic of which symptoms are billable.

    Args:
        medical_entities: List of MedicalEntity objects from detect_entities_v2

    Returns:
        List of diagnosis/symptom entities (excluding negations)
    """
    diagnosis_entities = []

    for entity in medical_entities:
        # Only MEDICAL_CONDITION category
        if entity.category != "MEDICAL_CONDITION":
            continue

        # Check traits
        has_diagnosis_or_symptom = False
        has_negation = False

        if entity.traits:
            trait_names = [t.get('Name', '') for t in entity.traits]
            has_diagnosis_or_symptom = 'DIAGNOSIS' in trait_names or 'SYMPTOM' in trait_names
            has_negation = 'NEGATION' in trait_names

        # Include DIAGNOSIS or SYMPTOM, exclude NEGATION
        # This filters out: SIGN-only entities and NEGATION entities
        if has_diagnosis_or_symptom and not has_negation:
            diagnosis_entities.append(entity)

    return diagnosis_entities


def normalize_text(text: str) -> str:
    """
    Normalize text for fuzzy matching.

    Args:
        text: Input text

    Returns:
        Normalized text (lowercase, trimmed)
    """
    return text.lower().strip()


def fuzzy_match_score(text1: str, text2: str) -> float:
    """
    Calculate fuzzy match score between two texts.

    Uses SequenceMatcher for similarity score.

    Args:
        text1: First text
        text2: Second text

    Returns:
        Similarity score (0.0-1.0)
    """
    norm1 = normalize_text(text1)
    norm2 = normalize_text(text2)

    # Exact match
    if norm1 == norm2:
        return 1.0

    # Check if one contains the other
    if norm1 in norm2 or norm2 in norm1:
        return 0.9

    # Sequence matching
    return SequenceMatcher(None, norm1, norm2).ratio()


def filter_icd10_codes(
    icd10_entities,
    diagnosis_entities,
    min_match_score: float = 0.5
):
    """
    Filter ICD-10 codes to only those matching actual diagnoses.

    Uses fuzzy text matching to connect ICD-10 codes to diagnosis entities
    from DetectEntitiesV2. Only keeps ICD-10 codes that match a diagnosis.

    Args:
        icd10_entities: List of ICD10Entity objects from infer_icd10_cm
        diagnosis_entities: List of diagnosis MedicalEntity objects
        min_match_score: Minimum fuzzy match score (default 0.5)

    Returns:
        Tuple of (filtered_icd10_entities, filter_stats)
    """
    if not diagnosis_entities:
        # No diagnoses, return empty list
        logger.warning("No diagnosis entities found, filtering out all ICD-10 codes")
        return [], {
            "total_icd10": len(icd10_entities),
            "filtered_icd10": 0,
            "filtered_out": len(icd10_entities),
            "diagnosis_entities": 0,
        }

    # Get diagnosis text for matching
    diagnosis_texts = [normalize_text(e.text) for e in diagnosis_entities]

    filtered = []
    matched_codes = set()

    for icd10_entity in icd10_entities:
        icd10_text = normalize_text(icd10_entity.text)

        # Check if this ICD-10 text matches any diagnosis entity
        best_match_score = 0.0
        best_match_text = None

        for diagnosis_entity in diagnosis_entities:
            diagnosis_text = normalize_text(diagnosis_entity.text)
            score = fuzzy_match_score(icd10_text, diagnosis_text)

            if score > best_match_score:
                best_match_score = score
                best_match_text = diagnosis_entity.text

        # Keep if match score is above threshold
        if best_match_score >= min_match_score:
            # Avoid duplicates (same code extracted multiple times)
            code_key = f"{icd10_entity.code}_{icd10_text}"
            if code_key not in matched_codes:
                filtered.append(icd10_entity)
                matched_codes.add(code_key)

                logger.debug(
                    "icd10_matched",
                    icd10_code=icd10_entity.code,
                    icd10_text=icd10_entity.text,
                    matched_diagnosis=best_match_text,
                    match_score=round(best_match_score, 3)
                )
        else:
            logger.debug(
                "icd10_filtered_out",
                icd10_code=icd10_entity.code,
                icd10_text=icd10_entity.text,
                best_match_score=round(best_match_score, 3)
            )

    stats = {
        "total_icd10": len(icd10_entities),
        "filtered_icd10": len(filtered),
        "filtered_out": len(icd10_entities) - len(filtered),
        "diagnosis_entities": len(diagnosis_entities),
        "match_threshold": min_match_score,
    }

    logger.info(
        "icd10_filtering_complete",
        **stats
    )

    return filtered, stats


def get_procedure_entities(medical_entities, min_score: float = 0.5) -> List:
    """
    Extract entities that represent procedures/treatments from DetectEntitiesV2 results.

    Filters for:
    - Category: TEST_TREATMENT_PROCEDURE
    - Score: >= min_score (default 0.5)

    Args:
        medical_entities: List of MedicalEntity objects from detect_entities_v2
        min_score: Minimum confidence score (default 0.5)

    Returns:
        List of procedure/treatment entities with sufficient confidence
    """
    procedure_entities = []

    for entity in medical_entities:
        # Only TEST_TREATMENT_PROCEDURE category
        if entity.category != "TEST_TREATMENT_PROCEDURE":
            continue

        # Check confidence score
        if entity.score >= min_score:
            procedure_entities.append(entity)

    return procedure_entities


def filter_snomed_codes(
    snomed_entities,
    procedure_entities,
    min_match_score: float = 0.5
):
    """
    Filter SNOMED codes to only those matching actual procedures/treatments.

    Uses fuzzy text matching to connect SNOMED codes to procedure entities
    from DetectEntitiesV2. Only keeps SNOMED codes that:
    - Have category TEST_TREATMENT_PROCEDURE
    - Match a procedure entity with score >= min_match_score

    Args:
        snomed_entities: List of SNOMEDEntity objects from infer_snomed_ct
        procedure_entities: List of procedure MedicalEntity objects
        min_match_score: Minimum fuzzy match score (default 0.5)

    Returns:
        Tuple of (filtered_snomed_entities, filter_stats)
    """
    if not procedure_entities:
        # No procedures, return empty list
        logger.warning("No procedure entities found, filtering out all SNOMED codes")
        return [], {
            "total_snomed": len(snomed_entities),
            "filtered_snomed": 0,
            "filtered_out": len(snomed_entities),
            "procedure_entities": 0,
        }

    # Get procedure text for matching
    procedure_texts = [normalize_text(e.text) for e in procedure_entities]

    filtered = []
    matched_codes = set()

    for snomed_entity in snomed_entities:
        # Only consider TEST_TREATMENT_PROCEDURE category
        if snomed_entity.category != "TEST_TREATMENT_PROCEDURE":
            continue

        snomed_text = normalize_text(snomed_entity.text)

        # Check if this SNOMED text matches any procedure entity
        best_match_score = 0.0
        best_match_text = None

        for procedure_entity in procedure_entities:
            procedure_text = normalize_text(procedure_entity.text)
            score = fuzzy_match_score(snomed_text, procedure_text)

            if score > best_match_score:
                best_match_score = score
                best_match_text = procedure_entity.text

        # Keep if match score is above threshold
        if best_match_score >= min_match_score:
            # Avoid duplicates (same code extracted multiple times)
            code_key = f"{snomed_entity.code}_{snomed_text}"
            if code_key not in matched_codes:
                filtered.append(snomed_entity)
                matched_codes.add(code_key)

                logger.debug(
                    "snomed_matched",
                    snomed_code=snomed_entity.code,
                    snomed_text=snomed_entity.text,
                    matched_procedure=best_match_text,
                    match_score=round(best_match_score, 3)
                )
        else:
            logger.debug(
                "snomed_filtered_out",
                snomed_code=snomed_entity.code,
                snomed_text=snomed_entity.text,
                best_match_score=round(best_match_score, 3)
            )

    stats = {
        "total_snomed": len(snomed_entities),
        "filtered_snomed": len(filtered),
        "filtered_out": len(snomed_entities) - len(filtered),
        "procedure_entities": len(procedure_entities),
        "match_threshold": min_match_score,
    }

    logger.info(
        "snomed_filtering_complete",
        **stats
    )

    return filtered, stats


def deduplicate_icd10_codes(icd10_entities):
    """
    Remove duplicate ICD-10 codes (same code extracted multiple times).

    Keeps the highest confidence instance of each code.

    Args:
        icd10_entities: List of ICD10Entity objects

    Returns:
        Deduplicated list of ICD10Entity objects
    """
    # Group by code
    by_code = {}
    for entity in icd10_entities:
        code = entity.code

        if code not in by_code:
            by_code[code] = entity
        else:
            # Keep higher confidence
            if entity.score > by_code[code].score:
                by_code[code] = entity

    deduplicated = list(by_code.values())

    logger.info(
        "icd10_deduplication",
        original_count=len(icd10_entities),
        deduplicated_count=len(deduplicated),
        duplicates_removed=len(icd10_entities) - len(deduplicated)
    )

    return deduplicated
