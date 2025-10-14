# Business Associate Agreement (BAA) Template

## BUSINESS ASSOCIATE AGREEMENT

**This Business Associate Agreement ("Agreement") is entered into as of [DATE] ("Effective Date") by and between:**

**COVERED ENTITY:**
[Client Name]
[Address]
[City, State ZIP]
("Covered Entity")

**BUSINESS ASSOCIATE:**
RevRX Inc.
[Company Address]
[City, State ZIP]
("Business Associate")

---

## RECITALS

WHEREAS, Covered Entity is a "Covered Entity" as defined by the Health Insurance Portability and Accountability Act of 1996 ("HIPAA") and wishes to disclose certain Protected Health Information ("PHI") to Business Associate for the purposes described below;

WHEREAS, Business Associate provides AI-powered medical coding review services that require access to PHI;

WHEREAS, both parties wish to comply with the HIPAA Privacy Rule (45 CFR Part 160 and Part 164, Subparts A and E) and Security Rule (45 CFR Part 160 and Part 164, Subparts A and C);

NOW, THEREFORE, in consideration of the mutual covenants and agreements herein, the parties agree as follows:

---

## ARTICLE 1: DEFINITIONS

**1.1 Defined Terms**

Terms used but not otherwise defined in this Agreement shall have the same meaning as those terms are defined in HIPAA and its implementing regulations.

- **"Breach"** means the acquisition, access, use, or disclosure of PHI in a manner not permitted under the Privacy Rule which compromises the security or privacy of the PHI.

- **"Electronic Protected Health Information" or "ePHI"** means PHI that is transmitted by or maintained in electronic media.

- **"Individual"** means the patient or person who is the subject of PHI and includes a person who qualifies as a personal representative in accordance with 45 CFR § 164.502(g).

- **"Protected Health Information" or "PHI"** means individually identifiable health information transmitted or maintained in any form or medium by Business Associate on behalf of Covered Entity.

- **"Required by Law"** means as defined in 45 CFR § 164.103.

- **"Secretary"** means the Secretary of the Department of Health and Human Services or designee.

- **"Services"** means the AI-powered medical coding review and revenue optimization services provided by Business Associate as described in the underlying service agreement.

---

## ARTICLE 2: OBLIGATIONS OF BUSINESS ASSOCIATE

**2.1 Permitted Uses and Disclosures**

Business Associate may use and disclose PHI only as permitted by this Agreement or as Required by Law, and may not use or disclose PHI in any manner that would violate Subpart E of 45 CFR Part 164 if done by Covered Entity.

Specifically, Business Associate is permitted to:
a) Process clinical notes through automated PHI de-identification systems
b) Analyze de-identified clinical data for medical coding suggestions
c) Generate reports containing suggested billing codes
d) Store PHI in encrypted databases for the duration of service provision

**2.2 Safeguards**

Business Associate shall implement appropriate safeguards to prevent use or disclosure of PHI other than as provided for by this Agreement, including but not limited to:
a) Encryption of PHI at rest using AES-256 encryption
b) Encryption of PHI in transit using TLS 1.3
c) Automated PHI de-identification before AI processing
d) Access controls and authentication mechanisms
e) Comprehensive audit logging of all PHI access

**2.3 Mitigation**

Business Associate shall mitigate, to the extent practicable, any harmful effect that is known to Business Associate of a use or disclosure of PHI by Business Associate in violation of the requirements of this Agreement.

**2.4 Reporting**

Business Associate shall report to Covered Entity any use or disclosure of PHI not provided for by this Agreement of which it becomes aware, including any Security Incident or Breach of Unsecured PHI, within:
- **24 hours** of discovery for P0/P1 incidents
- **72 hours** of discovery for P2 incidents as required by 45 CFR § 164.410

Reports shall include:
a) Description of the incident
b) Date of occurrence and discovery
c) PHI involved
d) Individuals affected (if known)
e) Mitigation measures taken
f) Contact person for further information

**2.5 Subcontractors and Agents**

Business Associate shall ensure that any subcontractors or agents that create, receive, maintain, or transmit PHI on behalf of Business Associate agree to restrictions and conditions at least as restrictive as those in this Agreement.

Current subcontractors with PHI access:
- **Amazon Web Services (AWS):** Infrastructure hosting, S3 storage
- **Amazon Comprehend Medical:** PHI detection and de-identification
- **OpenAI:** De-identified text analysis (NO PHI exposure)

**2.6 Access to PHI**

Business Associate shall make available PHI in a Designated Record Set to Covered Entity or Individual as necessary to satisfy Covered Entity's obligations under 45 CFR § 164.524 within fifteen (15) days of request.

**2.7 Amendment of PHI**

Business Associate shall make any amendment(s) to PHI in a Designated Record Set as directed by Covered Entity pursuant to 45 CFR § 164.526, within thirty (30) days of request.

**2.8 Accounting of Disclosures**

Business Associate shall document and make available to Covered Entity or Individual information required to provide an accounting of disclosures of PHI as necessary to satisfy Covered Entity's obligations under 45 CFR § 164.528 within thirty (30) days of request.

The accounting shall include:
a) Date of disclosure
b) Name and address of recipient
c) Brief description of PHI disclosed
d) Brief statement of purpose

**2.9 Compliance with HIPAA**

Business Associate shall comply with the applicable provisions of HIPAA and the HITECH Act, including but not limited to 45 CFR §§ 164.308, 164.310, 164.312, and 164.316.

---

## ARTICLE 3: OBLIGATIONS OF COVERED ENTITY

**3.1 Notice of Privacy Practices**

Covered Entity shall notify Business Associate of any limitation(s) in its Notice of Privacy Practices that may affect Business Associate's use or disclosure of PHI.

**3.2 Permission to Use or Disclose**

Covered Entity shall not request Business Associate to use or disclose PHI in any manner that would not be permissible under the Privacy Rule if done by Covered Entity.

**3.3 Authorizations and Restrictions**

Covered Entity shall notify Business Associate of any changes in, or revocation of, permission by an Individual to use or disclose PHI, to the extent that such changes may affect Business Associate's use or disclosure of PHI.

---

## ARTICLE 4: TERM AND TERMINATION

**4.1 Term**

This Agreement shall be effective as of the Effective Date and shall continue until all PHI provided by Covered Entity to Business Associate is destroyed or returned to Covered Entity, or until terminated as provided below.

**4.2 Termination for Cause**

Either party may terminate this Agreement upon thirty (30) days' written notice to the other party if:
a) The other party breaches a material term of this Agreement and does not cure the breach within thirty (30) days; or
b) Immediate termination is required by law.

**4.3 Effect of Termination**

Upon termination of this Agreement for any reason, Business Associate shall:

a) **Return or Destroy PHI:** Return to Covered Entity or destroy all PHI received from Covered Entity or created or received by Business Associate on behalf of Covered Entity that Business Associate maintains in any form, and retain no copies;

b) **Subcontractors:** Ensure all subcontractors and agents destroy or return all PHI;

c) **Certification:** Provide written certification to Covered Entity that all PHI has been returned or destroyed.

**4.4 Survival**

The obligations of Business Associate under this Article 4 shall survive the termination of this Agreement.

---

## ARTICLE 5: BREACH NOTIFICATION

**5.1 Discovery of Breach**

Business Associate shall, following the discovery of a Breach of Unsecured PHI, notify Covered Entity of such Breach.

**5.2 Timing of Notification**

Notification shall be made without unreasonable delay and in no case later than:
- **Immediate (within 1 hour):** For P0 breaches (active PHI exposure)
- **24 hours:** For P1 breaches (suspected PHI exposure)
- **72 hours:** For P2 incidents as required by 45 CFR § 164.410

**5.3 Content of Notification**

The notification shall include, to the extent possible:
a) Identification of each Individual whose Unsecured PHI has been, or is reasonably believed to have been, accessed, acquired, or disclosed;
b) Description of the Breach;
c) Date of the Breach and date of discovery;
d) Types of Unsecured PHI involved;
e) Steps Individuals should take to protect themselves;
f) Brief description of what Business Associate is doing to investigate, mitigate, and prevent recurrence;
g) Contact information for Business Associate.

---

## ARTICLE 6: INDEMNIFICATION

**6.1 Indemnification by Business Associate**

Business Associate shall indemnify, defend, and hold harmless Covered Entity from and against any claims, damages, liabilities, costs, and expenses (including reasonable attorneys' fees) arising from:
a) Business Associate's breach of this Agreement;
b) Business Associate's negligent or wrongful acts or omissions;
c) Business Associate's violation of HIPAA or the HITECH Act.

**6.2 Indemnification by Covered Entity**

Covered Entity shall indemnify Business Associate for claims arising from Covered Entity's failure to comply with its obligations under this Agreement or HIPAA.

---

## ARTICLE 7: MISCELLANEOUS

**7.1 Regulatory Changes**

The parties acknowledge that federal and state laws relating to data security and privacy are rapidly evolving. This Agreement shall be amended to the extent necessary to comply with changes in applicable law.

**7.2 Interpretation**

Any ambiguity in this Agreement shall be resolved in favor of a meaning that permits Covered Entity to comply with HIPAA and the HITECH Act.

**7.3 Entire Agreement**

This Agreement constitutes the entire agreement between the parties with respect to the subject matter hereof and supersedes all prior agreements and understandings.

**7.4 Amendment**

This Agreement may not be amended except by written agreement signed by both parties.

**7.5 Governing Law**

This Agreement shall be governed by the laws of [STATE] without regard to its conflict of laws provisions.

**7.6 Notices**

All notices required under this Agreement shall be sent to:

**If to Covered Entity:**
[Name]
[Title]
[Email]
[Address]

**If to Business Associate:**
RevRX Inc.
Attention: HIPAA Compliance Officer
compliance@revrx.com
[Address]

---

## SIGNATURE BLOCK

**COVERED ENTITY:**

By: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  Date: \_\_\_\_\_\_\_\_\_\_\_\_\_\_

Name: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Title: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

**BUSINESS ASSOCIATE:**

By: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_  Date: \_\_\_\_\_\_\_\_\_\_\_\_\_\_

Name: \_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_\_

Title: Chief Executive Officer, RevRX Inc.

---

## EXHIBIT A: TECHNICAL SAFEGUARDS

Business Associate implements the following technical safeguards:

**Encryption:**
- PHI at rest: AES-256 encryption
- PHI in transit: TLS 1.3
- Database: Transparent Data Encryption (TDE)
- Backups: Encrypted with separate keys

**Access Controls:**
- Role-based access control (RBAC)
- Multi-factor authentication for admins
- Unique user IDs
- Automatic session timeout
- Account lockout after failed attempts

**Audit Controls:**
- Comprehensive audit logging
- 6-year log retention
- Tamper-evident log storage
- Regular log review

**PHI De-identification:**
- Automated PHI detection via Amazon Comprehend Medical
- PHI removal before AI processing
- Encrypted PHI mapping storage
- Reversible de-identification for authorized users

**Monitoring:**
- 24/7 security monitoring
- Intrusion detection systems
- Real-time alerting
- Quarterly security assessments

---

## Document Information

**Document Type:** Legal Template
**Version:** 1.0
**Last Updated:** 2025-09-30
**Legal Review Date:** [DATE]
**Attorney:** [NAME]

**IMPORTANT:** This is a template and must be reviewed by legal counsel before use. Customize all bracketed sections before execution.
