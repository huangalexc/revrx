# Architecture Diagrams

## Overview

This document contains architecture diagrams for the Post-Facto Coding Review MVP system. The diagrams illustrate the system architecture, data flow, and component interactions.

---

## 1. High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                │
│                                                                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│  │   Web Browser   │  │  Mobile Browser │  │   API Clients   │        │
│  │   (React/Vue)   │  │   (Responsive)  │  │   (SDK/REST)    │        │
│  └────────┬────────┘  └────────┬────────┘  └────────┬────────┘        │
│           │                     │                     │                  │
└───────────┼─────────────────────┼─────────────────────┼─────────────────┘
            │                     │                     │
            │        HTTPS/TLS 1.3 (JWT Auth)          │
            │                     │                     │
┌───────────▼─────────────────────▼─────────────────────▼─────────────────┐
│                           API GATEWAY / LOAD BALANCER                    │
│                         (NGINX / AWS ALB / Kubernetes Ingress)           │
└───────────┬──────────────────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────────────────┐
│                          BACKEND API LAYER                               │
│                      (FastAPI / Django REST)                             │
│                                                                           │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌────────────┐       │
│  │   Auth     │  │  Encounter │  │   Report   │  │   Stripe   │       │
│  │  Service   │  │   Service  │  │  Service   │  │  Service   │       │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘       │
└────────┼───────────────┼───────────────┼───────────────┼────────────────┘
         │               │               │               │
         │               │               │               │
┌────────▼───────────────▼───────────────▼───────────────▼────────────────┐
│                        PROCESSING LAYER                                  │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────────┐       │
│  │             Background Job Queue (Celery / RQ)              │       │
│  │                                                               │       │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │       │
│  │  │   PHI        │  │      AI      │  │    Report    │     │       │
│  │  │ Processing   │→ │   Analysis   │→ │  Generation  │     │       │
│  │  │   Worker     │  │    Worker    │  │    Worker    │     │       │
│  │  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │       │
│  └─────────┼──────────────────┼──────────────────┼─────────────┘       │
└────────────┼──────────────────┼──────────────────┼─────────────────────┘
             │                  │                  │
┌────────────▼──────────────────▼──────────────────▼─────────────────────┐
│                         EXTERNAL SERVICES                                │
│                                                                           │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐              │
│  │    Amazon     │  │    OpenAI     │  │    Stripe     │              │
│  │  Comprehend   │  │   GPT-4 API   │  │  Payment API  │              │
│  │   Medical     │  │               │  │               │              │
│  └───────────────┘  └───────────────┘  └───────────────┘              │
└───────────────────────────────────────────────────────────────────────────┘
             │                  │                  │
┌────────────▼──────────────────▼──────────────────▼─────────────────────┐
│                           DATA LAYER                                     │
│                                                                           │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────┐           │
│  │   PostgreSQL   │  │   S3-Compatible│  │   Redis Cache  │           │
│  │    Database    │  │   Object Store │  │   (Sessions)   │           │
│  │  (Encrypted)   │  │   (Encrypted)  │  │                │           │
│  └────────────────┘  └────────────────┘  └────────────────┘           │
│                                                                           │
│  ┌─────────────────────────────────────────────────────────┐           │
│  │           Logging & Monitoring (ELK / CloudWatch)       │           │
│  └─────────────────────────────────────────────────────────┘           │
└───────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Data Flow Diagram - Encounter Processing

```
┌─────────┐
│  User   │
└────┬────┘
     │
     │ 1. Upload Clinical Note (TXT/PDF/DOCX)
     ▼
┌─────────────────┐
│   API Gateway   │
└────┬────────────┘
     │ 2. Validate & Authenticate
     ▼
┌─────────────────┐         ┌──────────────┐
│  Backend API    │─────────►│  PostgreSQL  │
│  (Encounter     │         │  (Save       │
│   Service)      │◄─────────│   Encounter) │
└────┬────────────┘         └──────────────┘
     │ 3. Store file metadata
     ▼
┌─────────────────┐
│  S3 Bucket      │
│  (Encrypted)    │◄────── 4. Upload encrypted file
└─────────────────┘
     │
     │ 5. Trigger background job
     ▼
┌─────────────────────────────────────────────────┐
│           Background Job Queue                  │
│                                                  │
│  Step 1: PHI Detection & De-identification      │
│  ┌──────────────────────────────────┐          │
│  │  1. Fetch file from S3            │          │
│  │  2. Extract text (PDF/DOCX→TXT)  │          │
│  │  3. Call Amazon Comprehend Medical│          │
│  │  4. Detect PHI entities            │          │
│  │  5. Replace PHI with tokens        │          │
│  │  6. Store PHI mapping (encrypted)  │          │
│  └──────────┬───────────────────────┘          │
│             │                                    │
│  Step 2: AI Code Suggestion                    │
│  ┌──────────▼───────────────────────┐          │
│  │  7. Send de-identified text to    │          │
│  │     ChatGPT with billing codes    │          │
│  │  8. Receive suggested codes        │          │
│  │  9. Parse justifications           │          │
│  │ 10. Calculate revenue estimates    │          │
│  └──────────┬───────────────────────┘          │
│             │                                    │
│  Step 3: Report Generation                     │
│  ┌──────────▼───────────────────────┐          │
│  │ 11. Generate structured report     │          │
│  │ 12. Store in database              │          │
│  │ 13. Update encounter status        │          │
│  │ 14. Log audit trail                │          │
│  └──────────┬───────────────────────┘          │
└─────────────┼─────────────────────────────────┘
              │
              │ 15. Report ready notification
              ▼
         ┌─────────┐
         │  User   │
         │ (Views  │
         │ Report) │
         └─────────┘
```

---

## 3. PHI De-identification Flow (HIPAA Compliance)

```
┌──────────────────────────────────────────────────────────────┐
│                   Clinical Note (Raw Text)                   │
│                                                               │
│  "Patient John Smith, DOB 03/15/1975, visited on 09/30/2025. │
│   Phone: (555) 123-4567. Lives at 123 Main St, Anytown."    │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         │ 1. Send to Amazon Comprehend Medical
                         ▼
┌──────────────────────────────────────────────────────────────┐
│            Amazon Comprehend Medical - DetectPHI             │
│                                                               │
│  Returns PHI entities:                                        │
│  [                                                            │
│    { type: "NAME", text: "John Smith", offset: 8-18 },      │
│    { type: "DATE", text: "03/15/1975", offset: 24-34 },     │
│    { type: "DATE", text: "09/30/2025", offset: 47-57 },     │
│    { type: "PHONE", text: "(555) 123-4567", offset: 66-80 },│
│    { type: "ADDRESS", text: "123 Main St, Anytown", ...}    │
│  ]                                                            │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         │ 2. Create PHI mapping & de-identify
                         ▼
┌──────────────────────────────────────────────────────────────┐
│              De-identified Text + PHI Mapping                │
│                                                               │
│  De-identified Text:                                          │
│  "Patient [NAME_1], DOB [DATE_1], visited on [DATE_2].      │
│   Phone: [PHONE_1]. Lives at [ADDRESS_1]."                  │
│                                                               │
│  PHI Mapping (Encrypted):                                    │
│  {                                                            │
│    "NAME_1": "John Smith",                                   │
│    "DATE_1": "03/15/1975",                                   │
│    "DATE_2": "09/30/2025",                                   │
│    "PHONE_1": "(555) 123-4567",                             │
│    "ADDRESS_1": "123 Main St, Anytown"                      │
│  }                                                            │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         │ 3. Store mapping in encrypted DB column
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                  PostgreSQL Database                          │
│                                                               │
│  Report table:                                                │
│  - de_identified_text: "Patient [NAME_1]..."                │
│  - phi_mapping: <AES-256 encrypted JSONB>                   │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         │ 4. Send de-identified text to ChatGPT
                         ▼
┌──────────────────────────────────────────────────────────────┐
│                     ChatGPT Analysis                          │
│                                                               │
│  Input: De-identified text + billed codes                    │
│  Output: Suggested codes + justifications                    │
│  (No PHI exposed to external AI service)                     │
└──────────────────────────────────────────────────────────────┘
```

---

## 4. Authentication & Authorization Flow

```
┌─────────┐
│  User   │
└────┬────┘
     │
     │ 1. POST /auth/login (email, password)
     ▼
┌──────────────────┐
│   API Gateway    │
└────┬─────────────┘
     │
     ▼
┌──────────────────┐         ┌──────────────┐
│  Auth Service    │────────►│  PostgreSQL  │
│                  │         │  (Fetch User)│
└────┬─────────────┘         └──────────────┘
     │
     │ 2. Verify password hash (bcrypt)
     │
     │ 3. Generate JWT tokens
     │    - Access Token (1 hour expiry)
     │    - Refresh Token (7 days expiry)
     │
     ▼
┌─────────────────────────────────────────┐
│           JWT Payload                   │
│  {                                       │
│    "sub": "user_id",                    │
│    "email": "user@example.com",         │
│    "role": "USER",                      │
│    "exp": 1696089600,                   │
│    "iat": 1696086000                    │
│  }                                       │
└────┬────────────────────────────────────┘
     │
     │ 4. Return tokens to client
     ▼
┌─────────┐
│  User   │  Stores tokens in secure storage
└────┬────┘  (httpOnly cookie or localStorage)
     │
     │ 5. Subsequent requests with Authorization header
     │    Authorization: Bearer <access_token>
     ▼
┌──────────────────┐
│   API Gateway    │
└────┬─────────────┘
     │
     │ 6. Validate JWT signature & expiry
     ▼
┌──────────────────┐
│  Auth Middleware │
│  - Verify token   │
│  - Check role     │
│  - Check subscription│
└────┬─────────────┘
     │
     │ 7. Attach user context to request
     ▼
┌──────────────────┐
│  Business Logic  │
│  (Protected      │
│   Endpoint)      │
└──────────────────┘
```

---

## 5. Payment & Subscription Flow

```
┌─────────┐
│  User   │
└────┬────┘
     │
     │ 1. Click "Start Free Trial"
     ▼
┌─────────────────┐
│  Frontend       │
└────┬────────────┘
     │ 2. POST /subscriptions/start-trial
     ▼
┌─────────────────┐         ┌──────────────┐
│  Backend API    │────────►│  PostgreSQL  │
│                 │         │  (Create     │
└────┬────────────┘         │   Subscription)
     │                      └──────────────┘
     │ 3. Set trial_end_date = now() + 7 days
     │
     │ 4. Return subscription details
     ▼
┌─────────┐
│  User   │  Accesses system during trial
└────┬────┘
     │
     │ 5. Trial expiration reminder (email)
     │    at trial_end_date - 3 days, -1 day
     ▼
┌─────────┐
│  User   │
└────┬────┘
     │ 6. Click "Subscribe" ($100/month)
     ▼
┌─────────────────┐
│  Frontend       │
└────┬────────────┘
     │ 7. POST /subscriptions/create-checkout
     ▼
┌─────────────────┐         ┌──────────────┐
│  Backend API    │────────►│    Stripe    │
│                 │         │     API      │
└────┬────────────┘         └──────┬───────┘
     │ 8. Create Stripe checkout session
     │                             │
     │ 9. Return checkout URL      │
     ◄─────────────────────────────┘
     │
     ▼
┌─────────┐
│  User   │  Redirected to Stripe Checkout
└────┬────┘
     │ 10. Enter payment details
     │
     ▼
┌──────────────┐
│    Stripe    │  Processes payment
└──────┬───────┘
       │
       │ 11. Webhook: subscription.created
       ▼
┌─────────────────┐         ┌──────────────┐
│  Webhook        │────────►│  PostgreSQL  │
│  Handler        │         │  (Update     │
└─────────────────┘         │   Subscription)
                            └──────────────┘
       │ 12. Update status = 'active'
       │     Store stripe_subscription_id
       │
       ▼
┌─────────┐
│  User   │  Access granted, billing starts
└─────────┘
```

---

## 6. Deployment Architecture (Kubernetes)

```
┌───────────────────────────────────────────────────────────────────┐
│                        Kubernetes Cluster                         │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Ingress Controller                     │   │
│  │              (NGINX / Traefik / AWS ALB)                  │   │
│  │            - TLS Termination (HTTPS)                      │   │
│  │            - Rate Limiting                                │   │
│  │            - WAF (Web Application Firewall)               │   │
│  └─────────────────────┬────────────────────────────────────┘   │
│                        │                                          │
│  ┌─────────────────────▼────────────────────────────────────┐   │
│  │                  Frontend Service                         │   │
│  │         (Next.js / React - 3 replicas)                    │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │  Pod 1   │  │  Pod 2   │  │  Pod 3   │              │   │
│  │  └──────────┘  └──────────┘  └──────────┘              │   │
│  └───────────────────────────────────────────────────────────┘   │
│                        │                                          │
│  ┌─────────────────────▼────────────────────────────────────┐   │
│  │                  Backend API Service                      │   │
│  │      (FastAPI / Django REST - 5 replicas)                │   │
│  │  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐      │   │
│  │  │ Pod 1│  │ Pod 2│  │ Pod 3│  │ Pod 4│  │ Pod 5│      │   │
│  │  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘      │   │
│  └───────────────────────────────────────────────────────────┘   │
│                        │                                          │
│  ┌─────────────────────▼────────────────────────────────────┐   │
│  │            Background Worker Service                      │   │
│  │           (Celery Workers - 3 replicas)                   │   │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐              │   │
│  │  │Worker 1  │  │Worker 2  │  │Worker 3  │              │   │
│  │  └──────────┘  └──────────┘  └──────────┘              │   │
│  └───────────────────────────────────────────────────────────┘   │
│                        │                                          │
│  ┌─────────────────────┼────────────────────────────────────┐   │
│  │                     ▼                                      │   │
│  │  ┌──────────────────────┐  ┌──────────────────────┐     │   │
│  │  │   PostgreSQL Pod     │  │   Redis Pod          │     │   │
│  │  │   (StatefulSet)      │  │   (StatefulSet)      │     │   │
│  │  │   - Primary          │  │   - Job Queue        │     │   │
│  │  │   - Read Replicas    │  │   - Session Cache    │     │   │
│  │  └──────────────────────┘  └──────────────────────┘     │   │
│  └───────────────────────────────────────────────────────────┘   │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              Persistent Volume Claims                     │   │
│  │  - Database Storage (Encrypted EBS / Persistent Disk)    │   │
│  │  - File Upload Storage (S3 CSI / Cloud Storage)          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                  Secrets Management                       │   │
│  │  - Kubernetes Secrets (base64)                           │   │
│  │  - External Secrets Operator (AWS Secrets Manager)       │   │
│  │  - Sealed Secrets (encrypted in Git)                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │             Monitoring & Logging                          │   │
│  │  - Prometheus (Metrics)                                   │   │
│  │  - Grafana (Dashboards)                                   │   │
│  │  - ELK Stack (Logs)                                       │   │
│  │  - Jaeger (Distributed Tracing)                           │   │
│  └──────────────────────────────────────────────────────────┘   │
└───────────────────────────────────────────────────────────────────┘
```

---

## 7. Security Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                         Security Layers                            │
│                                                                     │
│  Layer 1: Network Security                                         │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │  - VPC with private subnets                              │    │
│  │  - Security Groups / Network Policies                    │    │
│  │  - WAF (SQL injection, XSS protection)                   │    │
│  │  - DDoS protection (CloudFlare / AWS Shield)             │    │
│  └──────────────────────────────────────────────────────────┘    │
│                           │                                        │
│  Layer 2: Transport Security                                      │
│  ┌──────────────────────▼───────────────────────────────────┐    │
│  │  - TLS 1.3 for all connections                           │    │
│  │  - Certificate pinning                                    │    │
│  │  - HSTS (HTTP Strict Transport Security)                 │    │
│  └──────────────────────────────────────────────────────────┘    │
│                           │                                        │
│  Layer 3: Authentication & Authorization                          │
│  ┌──────────────────────▼───────────────────────────────────┐    │
│  │  - JWT tokens with RS256 signing                         │    │
│  │  - Role-Based Access Control (RBAC)                      │    │
│  │  - API key authentication for programmatic access        │    │
│  │  - Rate limiting per user/IP                             │    │
│  └──────────────────────────────────────────────────────────┘    │
│                           │                                        │
│  Layer 4: Application Security                                    │
│  ┌──────────────────────▼───────────────────────────────────┐    │
│  │  - Input validation & sanitization                       │    │
│  │  - Parameterized SQL queries (no SQL injection)          │    │
│  │  - CSRF protection                                        │    │
│  │  - Content Security Policy (CSP) headers                 │    │
│  └──────────────────────────────────────────────────────────┘    │
│                           │                                        │
│  Layer 5: Data Security                                           │
│  ┌──────────────────────▼───────────────────────────────────┐    │
│  │  - Encryption at rest (AES-256)                          │    │
│  │  - Database encryption (PostgreSQL TDE)                  │    │
│  │  - S3 bucket encryption                                   │    │
│  │  - Key management (AWS KMS / HSM)                        │    │
│  └──────────────────────────────────────────────────────────┘    │
│                           │                                        │
│  Layer 6: HIPAA Compliance                                        │
│  ┌──────────────────────▼───────────────────────────────────┐    │
│  │  - PHI de-identification (Amazon Comprehend Medical)     │    │
│  │  - Comprehensive audit logging                           │    │
│  │  - Access control & monitoring                           │    │
│  │  - Data retention policies                               │    │
│  │  - Business Associate Agreements                         │    │
│  └──────────────────────────────────────────────────────────┘    │
│                           │                                        │
│  Layer 7: Monitoring & Incident Response                          │
│  ┌──────────────────────▼───────────────────────────────────┐    │
│  │  - Real-time security monitoring                         │    │
│  │  - Intrusion detection system (IDS)                      │    │
│  │  - Automated alerting (Slack / PagerDuty)                │    │
│  │  - Incident response playbooks                           │    │
│  └──────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
```

---

## 8. Scalability & Performance Architecture

```
┌────────────────────────────────────────────────────────────────────┐
│                    Performance Optimization                        │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────┐    │
│  │                    CDN Layer                              │    │
│  │  - Static assets (JS, CSS, images)                       │    │
│  │  - Edge caching (CloudFlare / AWS CloudFront)            │    │
│  │  - Gzip / Brotli compression                             │    │
│  └─────────────────────┬────────────────────────────────────┘    │
│                        │                                           │
│  ┌─────────────────────▼────────────────────────────────────┐    │
│  │              Application Layer Caching                    │    │
│  │  - Redis for session storage                             │    │
│  │  - API response caching                                   │    │
│  │  - Database query result caching                          │    │
│  └─────────────────────┬────────────────────────────────────┘    │
│                        │                                           │
│  ┌─────────────────────▼────────────────────────────────────┐    │
│  │                Load Balancing                             │    │
│  │  - Round-robin distribution                              │    │
│  │  - Health checks                                          │    │
│  │  - Automatic failover                                     │    │
│  └─────────────────────┬────────────────────────────────────┘    │
│                        │                                           │
│  ┌─────────────────────▼────────────────────────────────────┐    │
│  │           Horizontal Pod Autoscaling (HPA)                │    │
│  │  - Scale based on CPU/Memory usage                       │    │
│  │  - Scale based on request queue depth                    │    │
│  │  - Min replicas: 3, Max replicas: 20                     │    │
│  └─────────────────────┬────────────────────────────────────┘    │
│                        │                                           │
│  ┌─────────────────────▼────────────────────────────────────┐    │
│  │              Database Optimization                        │    │
│  │  - Read replicas for reporting queries                   │    │
│  │  - Connection pooling (pgBouncer)                        │    │
│  │  - Query optimization & indexing                          │    │
│  │  - Partitioning for large tables                         │    │
│  └─────────────────────┬────────────────────────────────────┘    │
│                        │                                           │
│  ┌─────────────────────▼────────────────────────────────────┐    │
│  │              Async Processing                             │    │
│  │  - Background job queue (Celery)                         │    │
│  │  - Non-blocking I/O                                       │    │
│  │  - Batch processing for bulk operations                  │    │
│  └──────────────────────────────────────────────────────────┘    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Document Information

**Version:** 1.0
**Last Updated:** 2025-09-30
**Author:** RevRX Engineering Team
**Review Cycle:** Quarterly

**Tools Used:**
- ASCII art for clarity and version control friendliness
- For interactive diagrams, consider using:
  - Lucidchart
  - draw.io
  - Mermaid (markdown-based diagrams)
  - PlantUML

**Next Steps:**
- Convert ASCII diagrams to Mermaid format for rendering in documentation sites
- Create interactive diagrams for stakeholder presentations
- Update diagrams as architecture evolves
