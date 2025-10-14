# Access Control Policies

## Overview

This document defines access control policies for the Post-Facto Coding Review MVP to ensure that only authorized individuals can access systems and Protected Health Information (PHI) in accordance with HIPAA requirements.

---

## Policy Statement

Access to RevRX systems and PHI shall be granted based on the principle of **least privilege** - users receive only the minimum access necessary to perform their job functions.

---

## User Roles & Permissions

### Role Definitions

#### 1. USER (Standard User)
**Job Functions:** Medical coders, physicians, billing specialists

**Permissions:**
- ✅ Create and manage own encounters
- ✅ View own reports
- ✅ Upload clinical notes and billing codes
- ✅ Export own reports
- ✅ Manage own account settings
- ✅ View own subscription status

**Restrictions:**
- ❌ Cannot access other users' data
- ❌ Cannot view system logs
- ❌ Cannot access admin dashboard
- ❌ Cannot modify system settings

#### 2. ADMIN (Administrator)
**Job Functions:** System administrators, security team

**Permissions:**
- ✅ All USER permissions
- ✅ View all users and their data
- ✅ Access audit logs
- ✅ View system metrics
- ✅ Manage user accounts (suspend/activate)
- ✅ Override subscription status
- ✅ Access system configuration

**Restrictions:**
- ❌ Cannot delete audit logs
- ❌ Cannot modify PHI without audit trail
- ❌ Must justify all PHI access

**Additional Requirements:**
- Two-factor authentication mandatory
- All actions logged in audit trail
- Quarterly access review

---

## Account Management

### Account Provisioning

**New User Accounts:**
1. User registers via web interface
2. Email verification required
3. Default role: USER
4. Trial subscription activated automatically
5. Audit log entry created

**Admin Account Creation:**
1. Requires approval from CEO or CTO
2. Security background check required
3. Documented business justification
4. Two-factor authentication setup mandatory
5. Quarterly access review scheduled

### Account Modification

**Role Changes:**
```bash
# Promote user to admin (requires approval)
psql $DATABASE_URL -c "UPDATE \"User\" SET role='ADMIN' WHERE email='user@example.com';"

# Log role change in audit
psql $DATABASE_URL -c "INSERT INTO \"AuditLog\" (user_id, action, metadata) VALUES ('<admin-id>', 'role.change', '{\"target\": \"<user-id>\", \"old_role\": \"USER\", \"new_role\": \"ADMIN\"}');"
```

### Account Termination

**Within 24 hours of employment termination:**
1. Disable account access
2. Revoke all active sessions
3. Remove from admin groups
4. Document termination in audit log
5. Archive user data per retention policy

```bash
# Immediate access revocation
psql $DATABASE_URL -c "UPDATE \"User\" SET email_verified=false, subscription_status='cancelled' WHERE email='terminated@example.com';"

# Revoke all tokens
psql $DATABASE_URL -c "DELETE FROM \"Token\" WHERE user_id='<user-id>';"
```

---

## Authentication Requirements

### Password Policy

**Minimum Requirements:**
- Length: ≥ 8 characters
- Complexity: Uppercase + lowercase + number
- Expiration: 90 days for admin accounts
- History: Cannot reuse last 5 passwords
- Lockout: 5 failed attempts = 15-minute lockout

**Implementation:**
```python
import re
from passlib.hash import bcrypt

def validate_password(password: str) -> bool:
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'[0-9]', password):
        return False
    return True

def hash_password(password: str) -> str:
    return bcrypt.hash(password, rounds=12)
```

### Multi-Factor Authentication (MFA)

**Required For:**
- All ADMIN accounts (mandatory)
- USER accounts handling >100 encounters/month (recommended)
- Access from new devices or locations

**Supported Methods:**
- Time-based One-Time Password (TOTP)
- SMS verification (backup only)
- Hardware security keys (FIDO2)

### Session Management

**Session Parameters:**
- Access token lifetime: 1 hour
- Refresh token lifetime: 7 days
- Idle timeout: 30 minutes
- Concurrent sessions: Maximum 3 per user

**Session Termination:**
- Automatic on password change
- Manual logout
- Idle timeout exceeded
- Security incident

---

## Authorization Controls

### Role-Based Access Control (RBAC)

**Implementation:**
```python
from functools import wraps
from fastapi import HTTPException

def require_role(*allowed_roles):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user=None, **kwargs):
            if current_user.role not in allowed_roles:
                raise HTTPException(
                    status_code=403,
                    detail=f"Access denied. Required role: {allowed_roles}"
                )
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator

@app.get("/admin/users")
@require_role("ADMIN")
async def list_all_users(current_user: User):
    return await db.user.find_many()
```

### Resource Ownership Validation

**Principle:** Users can only access their own resources

```python
@app.get("/encounters/{encounter_id}")
async def get_encounter(encounter_id: str, current_user: User):
    encounter = await db.encounter.find_unique(where={"id": encounter_id})

    if not encounter:
        raise HTTPException(status_code=404, detail="Encounter not found")

    # Validate ownership (unless admin)
    if current_user.role != "ADMIN" and encounter.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied")

    return encounter
```

---

## PHI Access Controls

### Minimum Necessary Standard

**Policy:** Access to PHI limited to minimum necessary for job function

**Technical Controls:**
1. **Field-level access control**
   ```python
   # Example: PHI mapping only accessible to authorized functions
   def get_report_for_user(encounter_id: str) -> dict:
       report = db.report.find_unique(where={"encounterId": encounter_id})
       # Remove PHI mapping from user-facing response
       return {
           **report,
           "phiMapping": None  # Excluded
       }
   ```

2. **Automatic PHI de-identification**
   - All clinical notes processed through Amazon Comprehend Medical
   - PHI removed before AI analysis
   - Original PHI encrypted in database

3. **Audit logging for all PHI access**
   ```python
   @audit_log("phi.access")
   async def access_phi_mapping(encounter_id: str, current_user: User):
       # Log whenever PHI mapping is accessed
       logger.warning(f"PHI mapping accessed: {encounter_id} by {current_user.email}")
       return decrypt_phi_mapping(encounter_id)
   ```

---

## System Access Controls

### Infrastructure Access

**Production Environment:**
- SSH access disabled (kubectl exec only)
- AWS root account MFA required
- Kubernetes RBAC enforced
- VPN required for database access

**Access Levels:**
```yaml
# Kubernetes RBAC
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: developer-role
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list", "watch"]
- apiGroups: ["apps"]
  resources: ["deployments"]
  verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: admin-role
rules:
- apiGroups: ["*"]
  resources: ["*"]
  verbs: ["*"]
```

### Database Access

**Direct Access:**
- Restricted to DBAs and on-call engineers
- Requires VPN connection
- All queries logged
- Read-only replicas for reporting

**Application Access:**
- Connection pooling enforced
- Parameterized queries only
- Row-level security enabled

```sql
-- Row-level security policy
CREATE POLICY encounter_user_policy ON "Encounter"
  FOR ALL
  TO authenticated_user
  USING (user_id = current_user_id());
```

---

## Access Review & Audit

### Quarterly Access Review

**Process:**
1. Generate list of all user accounts and permissions
2. Department managers review their team's access
3. Remove unnecessary access
4. Document review findings
5. Update access control list

**Checklist:**
```bash
# Generate access report
psql $DATABASE_URL -c "
SELECT
  email,
  role,
  subscription_status,
  created_at,
  last_login
FROM \"User\"
ORDER BY role, email;
" > access-review-$(date +%Y%m%d).csv
```

- [ ] All active users have valid business justification
- [ ] No dormant accounts (>90 days inactive)
- [ ] Admin accounts reviewed and approved
- [ ] Terminated employees removed
- [ ] Role assignments appropriate

### Continuous Monitoring

**Automated Alerts:**
- Failed login attempts > 5 in 10 minutes
- Admin account created
- User role changed
- PHI accessed outside business hours
- Database queries returning >1000 records

**Alert Configuration:**
```yaml
# Prometheus alert rules
groups:
- name: access_control_alerts
  rules:
  - alert: HighFailedLoginRate
    expr: rate(auth_login_failed_total[5m]) > 0.1
    annotations:
      summary: "High failed login rate detected"

  - alert: AdminRoleGranted
    expr: increase(user_role_changed_total{new_role="ADMIN"}[5m]) > 0
    annotations:
      summary: "Admin role granted to user"
```

---

## Third-Party Access

### Vendor Access Policy

**Requirements for vendors requiring system access:**
1. Signed Business Associate Agreement (BAA)
2. Security questionnaire completed
3. Documented business justification
4. Time-limited access (30-90 days)
5. Supervised remote sessions for PHI access

**Vendor Account Management:**
```bash
# Create time-limited vendor account
psql $DATABASE_URL -c "
INSERT INTO \"User\" (email, role, subscription_status, trial_end_date)
VALUES ('vendor@partner.com', 'USER', 'active', NOW() + INTERVAL '30 days');
"

# Set reminder to review
echo "Review vendor access for vendor@partner.com" | at now + 30 days
```

---

## Emergency Access

### Break-Glass Procedures

**Emergency access account:** Used only in critical incidents when normal access unavailable

**Activation:**
1. Call on-call manager
2. Document business justification
3. Manager provides temporary credentials
4. All actions logged
5. Full audit within 24 hours
6. Credentials rotated after use

**Implementation:**
```bash
# Emergency access account (stored in sealed envelope)
export EMERGENCY_ACCESS_KEY="<sealed-secret>"

# Log emergency access use
echo "Emergency access activated: $(date) by $(whoami)" >> /var/log/emergency-access.log

# Automatic notification
curl -X POST https://slack.com/api/chat.postMessage \
  -d "channel=#security" \
  -d "text=ALERT: Emergency access activated"
```

---

## Compliance

### HIPAA Requirements

This policy addresses the following HIPAA requirements:
- § 164.308(a)(3) - Workforce security
- § 164.308(a)(4) - Access management
- § 164.312(a)(1) - Unique user identification
- § 164.312(a)(2) - Emergency access procedure
- § 164.312(d) - Person or entity authentication

### Audit Trail

All access control events logged:
- User authentication (success/failure)
- Authorization checks
- Role changes
- PHI access
- Admin actions

**Retention:** 6 years minimum (HIPAA requirement)

---

## Document Information

**Version:** 1.0
**Last Updated:** 2025-09-30
**Next Review:** 2026-03-31
**Owner:** HIPAA Compliance Officer

**Approval:**
- [ ] HIPAA Compliance Officer
- [ ] Security Lead
- [ ] Legal Counsel
- [ ] CEO
