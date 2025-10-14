# Incident Response Plan

## Overview

This Incident Response Plan (IRP) outlines procedures for identifying, responding to, and recovering from security incidents that may affect the confidentiality, integrity, or availability of the Post-Facto Coding Review MVP system or protected health information (PHI).

---

## Incident Response Team

### Primary Contacts

| Role | Name | Contact | Backup |
|------|------|---------|--------|
| Incident Commander | Security Lead | security@revrx.com | CTO |
| Technical Lead | DevOps Lead | devops@revrx.com | Senior Engineer |
| HIPAA Compliance Officer | Compliance Officer | compliance@revrx.com | Legal Counsel |
| Communications Lead | Marketing Director | communications@revrx.com | CEO |
| Legal Counsel | Corporate Attorney | legal@revrx.com | External Counsel |

### 24/7 Emergency Hotline
**Phone:** (555) 123-4567
**PagerDuty:** revrx-security-oncall

---

## Incident Classification

### Severity Levels

**P0 - Critical**
- Active PHI breach
- Ransomware attack
- Complete system outage
- Response Time: Immediate (< 15 minutes)

**P1 - High**
- Suspected PHI breach
- Unauthorized database access
- Critical system component failure
- Response Time: < 1 hour

**P2 - Medium**
- Failed login attempts exceeding threshold
- Suspicious network activity
- Non-critical service degradation
- Response Time: < 4 hours

**P3 - Low**
- Minor security policy violations
- Low-impact vulnerabilities
- Response Time: < 24 hours

---

## Incident Response Phases

### Phase 1: Detection & Identification (0-15 minutes)

**Automated Monitoring**
```bash
# Alert triggers from monitoring systems
- Failed authentication attempts > 10/min
- Database queries returning > 1000 PHI records
- Unusual network traffic patterns
- Unexpected privilege escalations
- File integrity changes to critical system files
```

**Manual Detection**
- User reports suspicious activity
- Audit log anomalies discovered
- Third-party security notifications

**Initial Actions**
1. Document incident discovery time and source
2. Capture initial evidence (screenshots, logs)
3. Notify Incident Commander immediately
4. Do NOT alert suspect or shut down systems prematurely

**Evidence Collection**
```bash
# Preserve logs immediately
kubectl logs deployment/revrx-backend > incident-backend-$(date +%Y%m%d-%H%M%S).log
kubectl logs deployment/revrx-worker > incident-worker-$(date +%Y%m%d-%H%M%S).log

# Database activity logs
psql $DATABASE_URL -c "COPY (SELECT * FROM \"AuditLog\" WHERE timestamp > NOW() - INTERVAL '2 hours') TO '/tmp/audit-incident.csv' CSV HEADER;"

# Export audit logs for last 24 hours
aws s3 cp /var/log/nginx/access.log s3://revrx-incident-evidence/access-$(date +%Y%m%d).log
```

### Phase 2: Containment (15-60 minutes)

**Short-term Containment**

For suspected unauthorized access:
```bash
# Revoke specific user tokens
psql $DATABASE_URL -c "DELETE FROM \"Token\" WHERE user_id='<suspicious-user-id>';"

# Block IP address
kubectl exec deployment/nginx-ingress -- nginx -s reload

# Disable compromised account
psql $DATABASE_URL -c "UPDATE \"User\" SET email_verified=false WHERE id='<user-id>';"
```

For ransomware/malware:
```bash
# Isolate affected pods
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data

# Snapshot volumes before remediation
kubectl exec <pod> -- tar czf /tmp/snapshot.tar.gz /data
```

**Long-term Containment**

Apply temporary fixes while maintaining business operations:
- Deploy patched application version
- Implement temporary firewall rules
- Enable additional logging
- Rotate credentials

### Phase 3: Eradication (1-4 hours)

**Root Cause Analysis**
- Identify attack vector
- Determine scope of compromise
- List all affected systems and data

**Removal Actions**
```bash
# Remove malware/backdoors
kubectl delete pod <compromised-pod>
kubectl rollout undo deployment/revrx-backend

# Rebuild from clean images
docker pull revrx-backend:last-known-good
kubectl set image deployment/revrx-backend backend=revrx-backend:last-known-good

# Verify integrity
kubectl exec deployment/revrx-backend -- sha256sum /app/main.py
```

**Credential Rotation**
```bash
# Rotate all secrets
kubectl delete secret revrx-secrets
kubectl create secret generic revrx-secrets --from-env-file=.env.production.new

# Force user password resets (if necessary)
psql $DATABASE_URL -c "UPDATE \"User\" SET password_hash='FORCE_RESET' WHERE last_login < NOW() - INTERVAL '90 days';"

# Regenerate JWT secrets
kubectl set env deployment/revrx-backend JWT_SECRET=$(openssl rand -base64 32)
```

### Phase 4: Recovery (4-24 hours)

**System Restoration**
```bash
# Restore from clean backup
pg_restore --dbname=$DATABASE_URL backup-clean.dump

# Verify data integrity
psql $DATABASE_URL -c "SELECT COUNT(*) FROM \"User\";"
psql $DATABASE_URL -c "SELECT COUNT(*) FROM \"Encounter\" WHERE created_at > NOW() - INTERVAL '7 days';"

# Gradually restore services
kubectl scale deployment/revrx-backend --replicas=1
# Monitor for 15 minutes
kubectl scale deployment/revrx-backend --replicas=3
```

**Validation**
- [ ] All services operational
- [ ] Security controls functioning
- [ ] No suspicious activity in logs
- [ ] Performance metrics normal
- [ ] User access restored appropriately

### Phase 5: Post-Incident Activities (24-72 hours)

**Incident Report** (Required within 72 hours)

Document:
1. Incident timeline
2. Root cause analysis
3. Systems/data affected
4. Containment actions taken
5. Evidence collected
6. Estimated impact (users, PHI records)
7. Remediation steps
8. Lessons learned
9. Preventive measures

**Notifications** (if PHI breach)

Per HIPAA Breach Notification Rule:
- **Individual Notification:** Within 60 days to affected individuals
- **HHS Notification:** Within 60 days if > 500 individuals affected
- **Media Notification:** If > 500 individuals in same jurisdiction

**Template Email to Affected Users:**
```
Subject: Important Security Notice - RevRX

Dear [Name],

We are writing to inform you of a security incident that may have affected your account information.

What Happened:
[Brief description of incident]

What Information Was Involved:
[Specific data types: name, email, PHI categories]

What We're Doing:
- [Actions taken to secure systems]
- [Additional monitoring measures]

What You Can Do:
- Change your password immediately
- Monitor for suspicious activity
- Enable two-factor authentication

For questions, contact: security@revrx.com

Sincerely,
RevRX Security Team
```

---

## Specific Incident Scenarios

### Scenario 1: PHI Data Breach

**Indicators:**
- Unauthorized download of PHI records
- Database export by unauthorized user
- PHI found in public repository

**Immediate Actions:**
1. Isolate affected systems
2. Revoke all API keys and tokens
3. Export audit logs showing accessed records
4. Identify all affected individuals
5. Notify HIPAA Compliance Officer immediately

**Legal Requirements:**
- Breach notification within 60 days (HIPAA)
- Document investigation thoroughly
- Preserve all evidence
- Consult legal counsel before external communication

### Scenario 2: Ransomware Attack

**Indicators:**
- Files encrypted with ransom note
- Sudden system inaccessibility
- Cryptocurrency payment demand

**Immediate Actions:**
1. **DO NOT pay ransom without executive approval**
2. Isolate infected systems immediately
3. Identify encryption scope
4. Check backup integrity
5. Engage forensics team

**Recovery:**
- Restore from clean backups
- Rebuild affected systems from scratch
- Implement enhanced monitoring
- Report to FBI (IC3.gov)

### Scenario 3: Insider Threat

**Indicators:**
- Unusual data access patterns by employee
- Bulk downloads of sensitive data
- Access outside normal hours/location

**Immediate Actions:**
1. Do NOT alert the individual
2. Preserve all evidence
3. Restrict access without raising suspicion
4. Engage HR and Legal
5. Document all findings

### Scenario 4: DDoS Attack

**Indicators:**
- Sudden traffic spike
- Service unresponsiveness
- Legitimate users cannot access system

**Immediate Actions:**
```bash
# Enable rate limiting
kubectl annotate ingress revrx-ingress nginx.ingress.kubernetes.io/rate-limit="10"

# Scale up pods
kubectl scale deployment/revrx-backend --replicas=10

# Enable CloudFlare DDoS protection
# Contact CloudFlare support for "Under Attack" mode
```

### Scenario 5: SQL Injection Attack

**Indicators:**
- Suspicious SQL in logs
- Unexpected database queries
- Error messages revealing schema

**Immediate Actions:**
```bash
# Review recent database queries
psql $DATABASE_URL -c "SELECT query, calls FROM pg_stat_statements ORDER BY calls DESC LIMIT 50;"

# Check for injected queries
grep -i "UNION SELECT\|DROP TABLE\|; --" /var/log/app/database.log

# Block malicious IPs
iptables -A INPUT -s <malicious-ip> -j DROP
```

**Remediation:**
- Review all database queries for parameterization
- Update ORM to latest secure version
- Implement Web Application Firewall (WAF)

---

## Communication Protocols

### Internal Communication

**Incident Response Slack Channel:** `#incident-response`

**Status Updates:**
- P0: Every 30 minutes
- P1: Every 2 hours
- P2: Twice daily
- P3: Daily

### External Communication

**Customer Communication:**
- Security Lead drafts message
- Legal reviews
- CEO approves
- Communications Lead distributes

**Regulatory Communication:**
- HIPAA Compliance Officer leads
- Legal prepares official notifications
- Submit to HHS within 60 days if breach > 500 individuals

**Media Inquiries:**
- Refer all media to Communications Lead
- No individual statements without approval
- Coordinate with PR agency if needed

---

## Tools & Resources

### Forensics Tools

```bash
# Log analysis
grep -E 'error|unauthorized|failed' /var/log/app/*.log

# Network traffic capture
tcpdump -i eth0 -w incident-capture.pcap

# File integrity check
aide --check

# Memory dump
kubectl exec <pod> -- gcore <pid>
```

### Evidence Preservation

```bash
# Create incident evidence bucket
aws s3 mb s3://revrx-incident-evidence-$(date +%Y%m%d)

# Upload all evidence with timestamps
aws s3 cp evidence/ s3://revrx-incident-evidence-$(date +%Y%m%d)/ --recursive

# Calculate checksums
sha256sum evidence/* > evidence-checksums.txt
```

### Contact Information

**External Resources:**
- FBI Cyber Division: (855) 292-3937
- CISA: (888) 282-0870
- AWS Security: security@amazonaws.com
- Legal Counsel: [external-firm]@law.com

---

## Training & Testing

### Incident Response Drills

**Quarterly Tabletop Exercises:**
- Simulate breach scenarios
- Test communication protocols
- Validate response times
- Update procedures based on learnings

**Annual Full-Scale Exercise:**
- Simulated real-world attack
- All team members participate
- External auditor observes
- Comprehensive after-action report

### Training Requirements

All employees must complete:
- HIPAA Security Awareness (annually)
- Phishing Recognition (quarterly)
- Incident Reporting Procedures (annually)

IR Team members must complete:
- Advanced Incident Response (annually)
- Forensics Training (every 2 years)
- Tabletop exercises (quarterly)

---

## Document Information

**Version:** 1.0
**Last Updated:** 2025-09-30
**Next Review:** 2026-03-31
**Owner:** HIPAA Compliance Officer

**Approval:**
- [ ] Security Lead
- [ ] Legal Counsel
- [ ] HIPAA Compliance Officer
- [ ] CEO

**Distribution:** Incident Response Team, Executive Leadership, Compliance Team
