# SNOMED CT to CPT Crosswalk System

## Overview

This document describes the SNOMED CT to CPT crosswalk mapping system used in RevRX to suggest billing codes based on clinical procedures identified by AWS Comprehend Medical.

## Background

### What is SNOMED CT?

SNOMED CT (Systematized Nomenclature of Medicine - Clinical Terms) is a comprehensive clinical terminology system that provides standardized codes for clinical documentation. AWS Comprehend Medical can extract SNOMED CT codes from clinical text.

### What is CPT?

CPT (Current Procedural Terminology) codes are standardized codes used for billing medical procedures and services in the United States. They are required for insurance reimbursement.

### Why Map SNOMED to CPT?

Clinical documentation often uses SNOMED CT concepts, but billing requires CPT codes. A crosswalk mapping allows us to:
1. Automatically suggest CPT codes based on procedures documented in clinical notes
2. Reduce manual coding effort
3. Improve coding accuracy and completeness
4. Identify potential missed billing opportunities

## Data Sources

### Official Sources

**Important Note**: There is **no free, publicly available CMS SNOMED CT to CPT crosswalk table**. Official mapping sources include:

1. **UMLS Metathesaurus** (NLM)
   - Contains both SNOMED CT and CPT concepts linked via CUIs (Concept Unique Identifiers)
   - Requires UMLS license (free but requires registration)
   - Access: https://www.nlm.nih.gov/research/umls/

2. **Commercial Mapping Services**
   - Proprietary crosswalk tables available from vendors like:
     - FindACode (Map-A-Code)
     - Intelligent Medical Objects (IMO)
     - Other medical coding software vendors
   - These typically require paid licenses

3. **SNOMED International Maps**
   - Official SNOMED CT maps primarily focus on ICD-10 mappings
   - SNOMED to CPT mapping is not officially maintained by SNOMED International
   - Access: https://www.snomed.org/maps

### Current Implementation

For development and testing, we use **expert-validated sample mappings** covering common procedures:

- Surgical procedures (appendectomy, hip arthroplasty, CABG)
- Imaging procedures (CT, MRI)
- Diagnostic procedures (colonoscopy, echocardiography)
- Laboratory tests (CBC, metabolic panel)
- E&M services

These mappings are stored in `scripts/seed_snomed_crosswalk.py` and can be loaded using the seed script.

## Database Schema

The crosswalk data is stored in the `snomed_crosswalk` table:

```prisma
model SNOMEDCrosswalk {
  id                String   @id @default(uuid())

  // Mapping
  snomedCode        String   // SNOMED CT concept ID (e.g., "80146002")
  snomedDescription String?  // Human-readable description
  cptCode           String   // CPT code (e.g., "44950")
  cptDescription    String?  // CPT code description

  // Metadata
  mappingType       String?  // EXACT, BROADER, NARROWER, APPROXIMATE
  confidence        Float?   // 0.0-1.0 confidence score
  source            String?  // Data source identifier
  sourceVersion     String?  // Version/date of source data
  effectiveDate     DateTime?

  // Timestamps
  createdAt         DateTime @default(now())
  updatedAt         DateTime @updatedAt

  @@unique([snomedCode, cptCode])
  @@index([snomedCode])  // Fast lookup by SNOMED code
  @@index([cptCode])     // Fast lookup by CPT code
}
```

### Mapping Types

- **EXACT**: One-to-one exact mapping between SNOMED and CPT
- **BROADER**: CPT code covers a broader scope than the SNOMED concept
- **NARROWER**: CPT code is more specific than the SNOMED concept
- **APPROXIMATE**: No perfect match, but reasonable clinical correlation

### Confidence Scores

- **0.90-1.00**: High confidence, well-established mapping
- **0.70-0.89**: Medium confidence, generally accepted mapping
- **0.50-0.69**: Lower confidence, use with caution
- **< 0.50**: Low confidence, human review recommended

## Loading Crosswalk Data

### Using Sample Data (Default)

```bash
cd backend
python scripts/seed_snomed_crosswalk.py --source sample
```

This loads ~16 expert-validated sample mappings for development and testing.

### Using Custom CSV Data

Create a CSV file with the following format:

```csv
snomed_code,snomed_description,cpt_code,cpt_description,mapping_type,confidence,source_version
80146002,Appendectomy,44950,Appendectomy,EXACT,0.95,2025
73761001,Colonoscopy,45378,Colonoscopy diagnostic,EXACT,0.95,2025
```

Load the data:

```bash
python scripts/seed_snomed_crosswalk.py --source custom --file data/crosswalk.csv
```

### Clearing Data

```bash
# Clear all crosswalk data
python scripts/seed_snomed_crosswalk.py --source sample --clear

# Clear only specific source
python scripts/seed_snomed_crosswalk.py --source sample --clear-source SAMPLE_EXPERT_VALIDATED
```

## Integration with Processing Pipeline

The crosswalk is used in the PHI processing pipeline:

1. **AWS Comprehend Medical** extracts SNOMED CT codes from clinical text
2. **SNOMEDCode records** are created in database
3. **Crosswalk service** looks up CPT mappings for each SNOMED code
4. **CPT suggestions** are added to the Report model
5. **LLM prompt** receives both SNOMED codes and suggested CPT codes for validation/refinement

This hybrid approach combines:
- Structured extraction (AWS Comprehend Medical)
- Rule-based mapping (SNOMED to CPT crosswalk)
- AI validation (LLM review of suggestions)

## Production Deployment

For production use, you should:

1. **Obtain Licensed Data**
   - Register for UMLS license and download Metathesaurus
   - Extract SNOMED-CPT mappings using CUI bridges
   - OR purchase commercial crosswalk data

2. **Data Processing**
   - Convert UMLS RRF files or vendor data to CSV format
   - Include mapping metadata (confidence, type, version)
   - Validate data quality

3. **Load into Database**
   - Use the seed script with custom CSV
   - Verify indexes are created for performance
   - Test lookup performance

4. **Maintenance**
   - Update crosswalk data annually (CPT codes change yearly)
   - Monitor for new SNOMED concepts
   - Track mapping quality metrics

## Performance Considerations

- **Indexes**: SNOMED code index ensures fast lookups (< 10ms)
- **One-to-Many**: One SNOMED code may map to multiple CPT codes
- **Caching**: Frequently used mappings are cached (see Phase 2.3)
- **Batch Lookups**: Support for batching multiple SNOMED codes

## Limitations

1. **Mapping Gaps**: Not all SNOMED concepts have CPT equivalents
2. **Clinical Context**: Mappings may require clinical judgment (e.g., laterality, complexity)
3. **Specificity**: CPT codes may require additional details not captured in SNOMED
4. **Annual Changes**: CPT codes are updated annually by AMA
5. **Licensing**: Production use requires proper licensing of crosswalk data

## Future Enhancements

- [ ] UMLS integration for comprehensive mappings
- [ ] Machine learning to improve mapping confidence scores
- [ ] Feedback loop to refine mappings based on human corrections
- [ ] Integration with additional clinical terminologies (LOINC, RxNorm)
- [ ] Automated annual CPT code updates

## References

- [UMLS Metathesaurus](https://www.nlm.nih.gov/research/umls/)
- [SNOMED International](https://www.snomed.org/)
- [AMA CPT Codes](https://www.ama-assn.org/practice-management/cpt)
- [AWS Comprehend Medical - SNOMED CT](https://docs.aws.amazon.com/comprehend-medical/latest/dev/ontologies-snomed.html)
