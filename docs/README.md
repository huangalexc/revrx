# RevRX Documentation

## Overview

This directory contains comprehensive documentation for the RevRX Post-Facto Coding Review MVP system. The documentation is organized into technical, user, and compliance sections.

---

## Documentation Structure

```
docs/
├── technical/           # Technical documentation for developers
│   ├── api-documentation.yaml
│   ├── database-schema.md
│   ├── architecture-diagrams.md
│   ├── deployment-guide.md
│   └── environment-variables.md
├── compliance/          # HIPAA and regulatory compliance
│   ├── hipaa-compliance-checklist.md
│   ├── phi-handling-procedures.md
│   └── data-retention-policy.md
├── user/               # End-user documentation (TODO)
└── README.md           # This file
```

---

## Technical Documentation

### [API Documentation](./technical/api-documentation.yaml)
Complete OpenAPI 3.0 specification for the RevRX API including:
- Authentication endpoints
- Encounter upload and processing
- Report retrieval
- Subscription management
- Admin endpoints
- Error responses and schemas

**Format:** OpenAPI 3.0 YAML
**Usage:** Import into Swagger UI or Postman for interactive API exploration

### [Database Schema](./technical/database-schema.md)
Comprehensive database schema documentation including:
- Entity relationship diagrams
- Table definitions with all columns and constraints
- Indexing strategy
- Security and encryption
- Backup and recovery procedures
- Performance optimization

**Key Tables:** User, Encounter, UploadedFile, Report, Subscription, AuditLog, Token

### [Architecture Diagrams](./technical/architecture-diagrams.md)
Visual architecture documentation including:
- High-level system architecture
- Data flow diagrams (encounter processing)
- PHI de-identification flow
- Authentication and authorization flow
- Payment and subscription flow
- Kubernetes deployment architecture
- Security architecture (7 layers)
- Scalability and performance architecture

**Format:** ASCII diagrams (version control friendly)

### [Deployment Guide](./technical/deployment-guide.md)
Step-by-step deployment instructions including:
- Prerequisites and requirements
- Docker containerization
- Kubernetes deployment (production-ready)
- Database migration procedures
- SSL/TLS configuration
- Monitoring setup (Prometheus + Grafana)
- Backup configuration
- Rollback procedures
- Post-deployment checklist
- CI/CD integration (GitHub Actions)

**Platforms:** Docker, Kubernetes, AWS/GCP/Azure

### [Environment Variables](./technical/environment-variables.md)
Complete environment configuration reference including:
- Application configuration
- Database connection strings
- Storage configuration (S3)
- External service credentials (AWS, OpenAI, Stripe)
- Security settings (JWT, encryption)
- Email configuration
- Monitoring and logging
- Feature flags
- Security best practices

**Environments:** Development, Staging, Production

---

## Compliance Documentation

### [HIPAA Compliance Checklist](./compliance/hipaa-compliance-checklist.md)
Comprehensive HIPAA compliance verification including:
- Administrative safeguards
- Physical safeguards
- Technical safeguards
- Organizational requirements
- Policies and procedures
- Documentation requirements
- PHI de-identification process
- Compliance monitoring
- Risk assessment summary

**Status:** ✅ All required safeguards implemented
**Last Assessment:** 2025-09-30
**Next Review:** 2026-03-30

### [PHI Handling Procedures](./compliance/phi-handling-procedures.md)
Detailed procedures for handling Protected Health Information including:
- PHI definition and 18 HIPAA identifiers
- Complete PHI lifecycle (ingestion → disposal)
- Amazon Comprehend Medical de-identification process
- PHI storage and encryption
- Access controls and audit logging
- PHI transmission security
- Incident response for PHI breaches
- Training requirements
- Code examples and implementation details

**Key Feature:** De-identification before external AI processing (ChatGPT)

### [Data Retention Policy](./compliance/data-retention-policy.md)
Comprehensive data retention and disposal policy including:
- Retention periods for all data types
- PHI retention (365 days default)
- Audit log retention (6 years - HIPAA requirement)
- Automated retention management
- Legal hold procedures
- User-requested deletion (GDPR Right to Erasure)
- Secure deletion methods (DoD 5220.22-M)
- Compliance monitoring

**Default Retention:** 365 days for encounters, 6 years for audit logs

---

## Completion Status

### Track 13.1: Technical Documentation ✅ COMPLETED

| Document | Status | Location |
|----------|--------|----------|
| API Documentation | ✅ Complete | `/docs/technical/api-documentation.yaml` |
| Database Schema | ✅ Complete | `/docs/technical/database-schema.md` |
| Architecture Diagrams | ✅ Complete | `/docs/technical/architecture-diagrams.md` |
| Deployment Guide | ✅ Complete | `/docs/technical/deployment-guide.md` |
| Environment Variables | ✅ Complete | `/docs/technical/environment-variables.md` |
| Troubleshooting Guide | ⏳ TODO | - |

### Track 13.2: User Documentation 🔄 PARTIAL

| Document | Status | Location |
|----------|--------|----------|
| User Onboarding Guide | ⏳ TODO | - |
| Video Tutorials | ⏳ TODO | Requires UI completion |
| In-App Help Tooltips | ⏳ TODO | Requires UI completion |
| FAQ Page | ⏳ TODO | - |
| Common Error Messages | ⏳ TODO | - |

### Track 13.3: Compliance Documentation ✅ COMPLETED

| Document | Status | Location |
|----------|--------|----------|
| HIPAA Compliance Checklist | ✅ Complete | `/docs/compliance/hipaa-compliance-checklist.md` |
| PHI Handling Procedures | ✅ Complete | `/docs/compliance/phi-handling-procedures.md` |
| Data Retention Policy | ✅ Complete | `/docs/compliance/data-retention-policy.md` |
| Incident Response Plan | ⏳ TODO | High priority |
| Access Control Policies | ⏳ TODO | High priority |
| BAA Template | ⏳ TODO | High priority |

---

## Quick Start

### For Developers

1. Read [Architecture Diagrams](./technical/architecture-diagrams.md) for system overview
2. Review [Database Schema](./technical/database-schema.md) for data model
3. Check [Environment Variables](./technical/environment-variables.md) for configuration
4. Follow [Deployment Guide](./technical/deployment-guide.md) for setup
5. Use [API Documentation](./technical/api-documentation.yaml) for API reference

### For Compliance Officers

1. Review [HIPAA Compliance Checklist](./compliance/hipaa-compliance-checklist.md)
2. Understand [PHI Handling Procedures](./compliance/phi-handling-procedures.md)
3. Verify [Data Retention Policy](./compliance/data-retention-policy.md)
4. Ensure Business Associate Agreements are signed

### For DevOps Engineers

1. Read [Deployment Guide](./technical/deployment-guide.md)
2. Configure [Environment Variables](./technical/environment-variables.md)
3. Review [Architecture Diagrams](./technical/architecture-diagrams.md) for infrastructure
4. Set up monitoring using deployment guide

---

## Key Features Documented

### HIPAA Compliance
- ✅ Amazon Comprehend Medical for PHI detection and de-identification
- ✅ Encryption at rest (AES-256) and in transit (TLS 1.3)
- ✅ Comprehensive audit logging (6-year retention)
- ✅ Role-based access control (RBAC)
- ✅ De-identification before external AI processing
- ✅ Business Associate Agreements with all vendors

### Security
- ✅ JWT-based authentication
- ✅ Password hashing with bcrypt (12 rounds)
- ✅ Rate limiting and DDoS protection
- ✅ WAF (Web Application Firewall)
- ✅ Security monitoring and alerting
- ✅ Incident response procedures

### Scalability
- ✅ Kubernetes deployment with autoscaling
- ✅ Horizontal pod autoscaling (HPA)
- ✅ Database connection pooling
- ✅ Redis caching
- ✅ CDN for static assets
- ✅ Background job queue (Celery)

### Data Protection
- ✅ Encrypted backups (30-day retention)
- ✅ Disaster recovery plan (RTO: 4h, RPO: 1h)
- ✅ Automated retention management
- ✅ Secure deletion (DoD 5220.22-M)
- ✅ Legal hold support
- ✅ GDPR right to erasure

---

## Document Maintenance

### Review Schedule

| Document Type | Review Cycle | Next Review |
|--------------|--------------|-------------|
| Technical Documentation | Quarterly | 2025-12-30 |
| Compliance Documentation | Semi-annual | 2026-03-30 |
| User Documentation | After major releases | TBD |

### Update Procedures

1. Make changes to relevant documentation
2. Update version number and last updated date
3. Document changes in change log
4. Get approval from document owner
5. Notify relevant stakeholders
6. Update this README if structure changes

### Document Owners

- **Technical Documentation:** Engineering Team Lead
- **Compliance Documentation:** Compliance Officer
- **User Documentation:** Product Manager

---

## Contributing

### Documentation Standards

- Use clear, concise language
- Include code examples where applicable
- Add diagrams for complex concepts
- Keep formatting consistent
- Update table of contents
- Include version and date information

### Markdown Guidelines

- Use ATX-style headers (`#`, `##`, etc.)
- Use fenced code blocks with language specification
- Use tables for structured data
- Use task lists for checklists
- Include links to related documents

---

## Contact Information

### Support

- **Technical Support:** support@revrx.com
- **Security Issues:** security@revrx.com
- **Compliance Questions:** compliance@revrx.com

### Emergency Contacts

- **Security Hotline:** [24/7 number]
- **On-Call Engineer:** [PagerDuty]

---

## Additional Resources

### External References

- [HIPAA Security Rule](https://www.hhs.gov/hipaa/for-professionals/security/index.html)
- [HIPAA Privacy Rule](https://www.hhs.gov/hipaa/for-professionals/privacy/index.html)
- [Amazon Comprehend Medical Documentation](https://docs.aws.amazon.com/comprehend-medical/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

### Internal Resources

- Wiki: wiki.revrx.com
- Jira: jira.revrx.com
- Slack: #engineering, #compliance
- GitHub: github.com/revrx/revrx

---

## License

This documentation is proprietary and confidential.

© 2025 RevRX. All rights reserved.

---

**Last Updated:** 2025-09-30
**Version:** 1.0
**Maintained By:** RevRX Engineering and Compliance Teams
