# SNOMED Crosswalk Service Usage Guide

## Overview

The SNOMED Crosswalk Service provides fast, cached lookups of CPT code mappings for SNOMED CT procedure concepts extracted by AWS Comprehend Medical.

## Quick Start

### Basic Usage

```python
from app.services.snomed_crosswalk import get_crosswalk_service
from prisma import Prisma

# Initialize database and service
db = Prisma()
await db.connect()

service = await get_crosswalk_service(db)

# Look up CPT mappings for a SNOMED code
mappings = await service.get_cpt_mappings("80146002")

for mapping in mappings:
    print(f"CPT {mapping.cpt_code}: {mapping.cpt_description}")
    print(f"  Confidence: {mapping.confidence}")
    print(f"  Type: {mapping.mapping_type}")
```

### Single Code Lookup with Confidence Threshold

```python
# Get only high-confidence mappings (≥0.7)
mappings = await service.get_cpt_mappings(
    snomed_code="80146002",
    min_confidence=0.7
)

# Results are automatically sorted by confidence (highest first)
if mappings:
    best_mapping = mappings[0]
    print(f"Best match: {best_mapping.cpt_code} ({best_mapping.confidence})")
```

### Get Best Single Mapping

```python
# Get only the highest confidence mapping
best = await service.get_best_cpt_mapping(
    snomed_code="80146002",
    min_confidence=0.7
)

if best:
    print(f"Recommended CPT: {best.cpt_code}")
else:
    print("No high-confidence mapping found")
```

### Batch Lookup (Multiple SNOMED Codes)

```python
# Efficient batch lookup for multiple codes
snomed_codes = ["80146002", "73761001", "82078001"]

results = await service.get_cpt_mappings_batch(
    snomed_codes=snomed_codes,
    min_confidence=0.5
)

for snomed_code, mappings in results.items():
    print(f"\nSNOMED {snomed_code}:")
    for mapping in mappings:
        print(f"  → CPT {mapping.cpt_code} ({mapping.confidence})")
```

### Reverse Lookup (CPT → SNOMED)

```python
# Find SNOMED codes that map to a CPT code
mappings = await service.find_by_cpt_code("44950")

for mapping in mappings:
    print(f"SNOMED {mapping.snomed_code}: {mapping.snomed_description}")
```

## Integration with PHI Processing

### Example: Processing Encounter with SNOMED Extraction

```python
from app.services.comprehend_medical import ComprehendMedicalService
from app.services.snomed_crosswalk import get_crosswalk_service

async def process_clinical_note(encounter_id: str, clinical_text: str):
    """Process clinical note and suggest CPT codes"""

    db = Prisma()
    await db.connect()

    try:
        # Extract SNOMED codes using AWS Comprehend Medical
        comprehend = ComprehendMedicalService()
        snomed_entities = await comprehend.infer_snomed_ct(clinical_text)

        # Get crosswalk service
        crosswalk = await get_crosswalk_service(db)

        # Extract unique SNOMED codes
        snomed_codes = list(set([e.code for e in snomed_entities]))

        # Batch lookup CPT mappings
        cpt_suggestions = await crosswalk.get_cpt_mappings_batch(
            snomed_codes=snomed_codes,
            min_confidence=0.6
        )

        # Store SNOMED codes in database
        for entity in snomed_entities:
            await db.snomedcode.create(
                data={
                    "encounterId": encounter_id,
                    "code": entity.code,
                    "description": entity.description,
                    "category": entity.category,
                    "type": entity.type,
                    "score": entity.score,
                    "beginOffset": entity.begin_offset,
                    "endOffset": entity.end_offset,
                    "text": entity.text,
                }
            )

        # Prepare CPT suggestions for LLM
        cpt_codes_for_llm = []
        for snomed_code, mappings in cpt_suggestions.items():
            for mapping in mappings[:3]:  # Top 3 per SNOMED code
                cpt_codes_for_llm.append({
                    "cpt_code": mapping.cpt_code,
                    "description": mapping.cpt_description,
                    "source": "SNOMED_CROSSWALK",
                    "confidence": mapping.confidence,
                    "snomed_source": snomed_code,
                })

        # Update report with suggestions
        await db.report.update(
            where={"encounterId": encounter_id},
            data={
                "extractedSnomedCodes": [e.to_dict() for e in snomed_entities],
                "cptSuggestions": cpt_codes_for_llm,
            }
        )

        return cpt_codes_for_llm

    finally:
        await db.disconnect()
```

## Performance Monitoring

### View Metrics

```python
# Get current metrics
metrics = service.get_metrics()
print(f"Total lookups: {metrics['total_lookups']}")
print(f"Cache hit rate: {metrics['cache_hit_rate']}")
print(f"DB hit rate: {metrics['db_hit_rate']}")

# Get cache statistics
cache_stats = service.get_cache_stats()
print(f"Cache size: {cache_stats['current_size']}/{cache_stats['max_size']}")
print(f"Utilization: {cache_stats['utilization']}")
```

### Log Performance Summary

```python
# Log comprehensive performance summary
service.log_performance_summary()

# Output (structured logs):
# crosswalk_metrics total_lookups=1250 cache_hits=980 cache_hit_rate=0.784 ...
# cache_stats current_size=342 max_size=1000 utilization=0.342
```

## Cache Management

### Manual Cache Control

```python
# Clear cache (forces all lookups to hit database)
service.clear_cache()

# Warm cache with top 200 codes
await service.warm_cache(top_n=200)

# Disable cache for specific lookup
mappings = await service.get_cpt_mappings(
    snomed_code="80146002",
    use_cache=False  # Always query database
)
```

### Cache Warming on Startup

The service automatically warms the cache on first initialization:

```python
# First call initializes and warms cache
service = await get_crosswalk_service(db)
# Cache now pre-loaded with top 100 SNOMED codes

# Subsequent calls return same instance (singleton)
service2 = await get_crosswalk_service(db)
assert service is service2  # Same instance
```

## Understanding Mapping Types

### EXACT
One-to-one perfect match between SNOMED concept and CPT code.
```python
# Example: SNOMED 80146002 (Appendectomy) → CPT 44950 (Appendectomy)
```

### BROADER
CPT code covers a broader scope than the SNOMED concept. Multiple SNOMED concepts may map to same CPT.
```python
# Example: SNOMED 179344006 (CABG) → CPT 33533 (CABG, arterial, single)
#          SNOMED 179344006 (CABG) → CPT 33534 (CABG, arterial, two)
```

### NARROWER
CPT code is more specific than the SNOMED concept (less common).

### APPROXIMATE
No perfect match, but reasonable clinical correlation. Use with caution.

## Confidence Scores

### Recommended Thresholds

- **≥0.90**: High confidence - Safe for automatic suggestion
- **0.70-0.89**: Medium confidence - Good for most cases
- **0.50-0.69**: Lower confidence - Human review recommended
- **<0.50**: Low confidence - Use only as hints

### Example: Confidence-Based Logic

```python
mappings = await service.get_cpt_mappings("80146002")

high_confidence = [m for m in mappings if m.confidence >= 0.9]
medium_confidence = [m for m in mappings if 0.7 <= m.confidence < 0.9]
low_confidence = [m for m in mappings if m.confidence < 0.7]

# Auto-suggest high confidence
# Show medium confidence with warning
# Require review for low confidence
```

## Error Handling

```python
try:
    mappings = await service.get_cpt_mappings("80146002")
except Exception as e:
    logger.error("crosswalk_error", error=str(e))
    # Fallback: Empty list or LLM-only approach
    mappings = []
```

The service handles errors gracefully:
- Database errors return empty list
- Invalid codes return empty list
- All errors are logged with structured logging

## Best Practices

### 1. Use Batch Lookups for Multiple Codes
```python
# ❌ Bad: Multiple individual lookups
for code in snomed_codes:
    mappings = await service.get_cpt_mappings(code)

# ✅ Good: Single batch lookup
all_mappings = await service.get_cpt_mappings_batch(snomed_codes)
```

### 2. Set Appropriate Confidence Thresholds
```python
# For automatic suggestions
high_conf = await service.get_cpt_mappings(code, min_confidence=0.8)

# For hints/recommendations
all = await service.get_cpt_mappings(code, min_confidence=0.5)
```

### 3. Monitor Cache Performance
```python
# Periodically log metrics
if service.metrics.total_lookups % 1000 == 0:
    service.log_performance_summary()
```

### 4. Handle Missing Mappings Gracefully
```python
mappings = await service.get_cpt_mappings(snomed_code)

if not mappings:
    # Fallback to LLM-based extraction
    # OR log for manual review
    logger.warning("no_crosswalk_mapping", snomed_code=snomed_code)
```

## Performance Characteristics

- **Cache hit**: ~0.01ms (in-memory lookup)
- **Cache miss**: ~10-50ms (database query + indexing)
- **Batch lookup**: ~20-100ms (single query for N codes)
- **Warm cache on startup**: ~500-2000ms (one-time cost)

## Testing

Run the comprehensive test suite:

```bash
cd backend
pytest app/services/test_snomed_crosswalk.py -v
```

Expected output:
```
test_snomed_crosswalk.py::TestCPTMapping::test_create_mapping PASSED
test_snomed_crosswalk.py::TestCPTMapping::test_to_dict PASSED
test_snomed_crosswalk.py::TestCrosswalkMetrics::test_initial_metrics PASSED
...
==================== 20 passed in 2.34s ====================
```

## Related Documentation

- [SNOMED CPT Crosswalk Overview](SNOMED_CPT_CROSSWALK.md)
- [AWS Comprehend Medical Integration](comprehend_medical_integration.md)
- [PHI Processing Pipeline](phi_processing_pipeline.md)
