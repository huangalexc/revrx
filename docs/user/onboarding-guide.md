# User Onboarding Guide

Welcome to **RevRX** - the AI-powered medical coding review platform that helps you identify missed billing opportunities and maximize revenue.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [Creating Your Account](#creating-your-account)
3. [Understanding the Dashboard](#understanding-the-dashboard)
4. [Uploading Your First Encounter](#uploading-your-first-encounter)
5. [Reviewing Reports](#reviewing-reports)
6. [Managing Your Subscription](#managing-your-subscription)
7. [Best Practices](#best-practices)
8. [Getting Help](#getting-help)

---

## Getting Started

### What is RevRX?

RevRX uses advanced AI to analyze your clinical documentation and compare it against the codes you've billed. Our platform:

- ✅ Identifies additional billable CPT/ICD codes supported by your documentation
- ✅ Provides justifications for each suggested code
- ✅ Calculates potential incremental revenue
- ✅ Maintains HIPAA compliance with automatic PHI de-identification
- ✅ Processes encounters in under 30 seconds

### System Requirements

- **Browser:** Chrome, Firefox, Safari, or Edge (latest versions)
- **Internet:** Stable broadband connection
- **Files:** Clinical notes in TXT, PDF, or DOCX format (max 5MB)
- **Billing Codes:** CSV or JSON format

---

## Creating Your Account

### Step 1: Sign Up

1. Navigate to [https://revrx.com/register](https://revrx.com/register)
2. Enter your information:
   - **Email Address:** Use your professional work email
   - **Password:** Min 8 characters with uppercase, lowercase, and number
   - **Full Name:** Your professional name
   - **Organization** (optional): Your practice or clinic name

3. Click **"Create Account"**

### Step 2: Verify Your Email

1. Check your email inbox for a message from `noreply@revrx.com`
2. Click the **"Verify Email Address"** link
3. You'll be redirected to the login page

> 💡 **Tip:** Check your spam folder if you don't see the email within 5 minutes

### Step 3: Log In

1. Enter your email and password
2. Click **"Log In"**
3. You'll be taken to your dashboard

### Step 4: Start Your 7-Day Free Trial

Your free trial begins immediately upon email verification. During your trial:

- ✅ Upload up to 50 encounters
- ✅ Full access to all features
- ✅ No credit card required
- ✅ Cancel anytime

---

## Understanding the Dashboard

### Main Navigation

The left sidebar contains:

- **📊 Dashboard** - Overview of your encounters and revenue opportunities
- **📁 Encounters** - List of all uploaded encounters
- **📤 Upload** - Submit new clinical notes and billing codes
- **💰 Reports** - View detailed analysis reports
- **⚙️ Settings** - Account and notification preferences
- **💳 Billing** - Subscription and payment information

### Dashboard Widgets

**Revenue Summary Card**
- Total potential incremental revenue across all encounters
- Average revenue per encounter
- Number of processed encounters

**Recent Encounters**
- Latest uploads with status indicators:
  - 🟡 Pending - Waiting to be processed
  - 🔵 Processing - AI analysis in progress
  - 🟢 Complete - Report ready
  - 🔴 Failed - Error occurred

**Processing Status**
- Live updates on encounter processing
- Estimated time remaining

---

## Uploading Your First Encounter

### Step 1: Prepare Your Files

**Clinical Note Requirements:**
- Format: TXT, PDF, or DOCX
- Size: Maximum 5MB
- Content: Complete clinical documentation including:
  - Chief complaint
  - History of present illness
  - Review of systems
  - Physical examination
  - Assessment and plan
  - Procedures performed

**Billing Codes Requirements:**
- Format: CSV or JSON
- Contents: CPT and ICD-10 codes you've already billed
- Example CSV:
  ```csv
  code,type,description
  99214,CPT,Office visit - established patient
  I10,ICD10,Essential hypertension
  ```

- Example JSON:
  ```json
  [
    {"code": "99214", "type": "CPT", "description": "Office visit - established patient"},
    {"code": "I10", "type": "ICD10", "description": "Essential hypertension"}
  ]
  ```

### Step 2: Upload Clinical Note

1. Click **"Upload"** in the left sidebar
2. Click **"Choose File"** or drag-and-drop your clinical note
3. Fill in optional metadata:
   - **Patient Age:** Helps with code validation
   - **Patient Sex:** M/F/O
   - **Visit Date:** Date of service
   - **Encounter Type:** Office Visit, ER, etc.

4. Click **"Upload Clinical Note"**

> 🔒 **HIPAA Compliance:** All PHI (names, dates, IDs) is automatically removed before AI analysis. Original data is encrypted and stored securely.

### Step 3: Upload Billing Codes

1. After the clinical note uploads, you'll see a prompt to upload billing codes
2. Choose your file or paste JSON directly
3. Click **"Upload Billing Codes"**

### Step 4: Wait for Processing

- Processing typically takes **15-30 seconds**
- You'll see a progress indicator
- Feel free to navigate away - we'll notify you when complete

---

## Reviewing Reports

### Accessing Your Report

1. Go to **"Encounters"** in the sidebar
2. Click on any encounter with status **"Complete"** (🟢)
3. Your detailed report will open

### Report Sections

#### 1. Executive Summary
- Total incremental revenue opportunity
- Number of additional codes identified
- Confidence level overview

#### 2. Code Comparison Table

| Billed Code | Description | Suggested Code | Description | Incremental Revenue | Confidence |
|-------------|-------------|----------------|-------------|---------------------|------------|
| 99214 | Office visit - Established | 99215 | Office visit - High complexity | $75.00 | 92% |

#### 3. Detailed Justifications

For each suggested code, you'll see:

- **Justification:** Why this code is supported by documentation
- **Supporting Text:** Exact excerpts from the clinical note
- **Confidence Score:** AI's confidence level (0-100%)
- **Revenue Estimate:** Based on Medicare fee schedule

**Example:**
```
Suggested Code: 99215 (Office visit - High complexity)
Confidence: 92%
Estimated Revenue: $75.00

Justification:
Documentation supports a high-complexity evaluation with:
- Comprehensive history taken
- Detailed examination of multiple organ systems
- High medical decision-making complexity

Supporting Text:
- "Comprehensive review of systems performed across 10+ systems"
- "Detailed examination including cardiovascular, respiratory, and neurological assessment"
- "Considered multiple diagnoses and ordered extensive diagnostic workup"
```

### Taking Action

For each suggested code, you can:

1. **✅ Accept** - Add to your billing
2. **❌ Reject** - Not applicable
3. **📝 Notes** - Add comments for later review

### Exporting Reports

Click **"Export"** to download in:
- **PDF** - Professional report format
- **YAML** - Structured data format
- **JSON** - API-compatible format
- **CSV** - Spreadsheet-compatible

---

## Managing Your Subscription

### Viewing Subscription Status

1. Click **"Billing"** in the sidebar
2. View your current plan:
   - Trial status and days remaining
   - Active subscription details
   - Next billing date

### Upgrading to Paid Plan

When your trial ends, or to upgrade early:

1. Go to **"Billing"**
2. Click **"Subscribe Now"**
3. Choose your plan:
   - **Monthly:** $100/month
   - **Annual:** $1,000/year (save 17%)

4. Enter payment information (securely processed by Stripe)
5. Click **"Subscribe"**

### Canceling Your Subscription

1. Go to **"Billing"**
2. Click **"Cancel Subscription"**
3. Confirm cancellation
4. You'll retain access until the end of your billing period

---

## Best Practices

### For Optimal Results

**1. Submit Complete Documentation**
- Include all sections of your clinical note
- Don't omit procedures, tests, or counseling
- More detail = better code suggestions

**2. Upload Regularly**
- Review encounters shortly after completion
- Catch billing opportunities before claim submission
- Build a habit of checking every encounter

**3. Verify Suggested Codes**
- Review justifications carefully
- Cross-reference with your documentation
- Use your professional judgment
- RevRX suggests, you decide

**4. Track Your Revenue**
- Monitor the dashboard summary
- Identify patterns in missed opportunities
- Adjust documentation practices accordingly

### Common Pitfalls to Avoid

❌ **Incomplete Clinical Notes**
- Leads to missed suggestions
- Upload complete documentation

❌ **Outdated Billing Codes**
- Ensure codes match what was actually billed
- Update if billing changed

❌ **Ignoring Low-Confidence Suggestions**
- Even 70% confidence can be valid
- Review the justification

❌ **Not Documenting Enough**
- If codes are missing, improve documentation
- Use RevRX to identify documentation gaps

---

## Getting Help

### In-App Help

- Click **"?"** icon for contextual help tooltips
- View **"FAQ"** in the footer
- Access **"Documentation"** from settings

### Knowledge Base

Visit [https://docs.revrx.com](https://docs.revrx.com) for:
- Detailed user guides
- Video tutorials
- Best practices articles
- Coding resources

### Contact Support

**Email:** support@revrx.com
**Response Time:** Within 24 hours

**Live Chat:**
- Available Monday-Friday, 9 AM - 5 PM EST
- Click chat icon in bottom right

### Report Issues

**Bug Reports:** bugs@revrx.com
**Feature Requests:** feedback@revrx.com

### Community

Join our community of medical coding professionals:
- **Webinars:** Monthly best practices sessions
- **User Forum:** [community.revrx.com](https://community.revrx.com)
- **Newsletter:** Coding tips and platform updates

---

## Quick Reference

### Keyboard Shortcuts

- `Ctrl/Cmd + U` - Quick upload
- `Ctrl/Cmd + E` - View encounters
- `Ctrl/Cmd + D` - Go to dashboard
- `Ctrl/Cmd + /` - Search

### Status Indicators

- 🟡 **Pending** - In queue for processing
- 🔵 **Processing** - AI analysis in progress (15-30 seconds)
- 🟢 **Complete** - Report ready to view
- 🔴 **Failed** - Error occurred (hover for details)

### File Size Limits

- Clinical Notes: **5MB max**
- Billing Codes: **1MB max**

### Supported File Types

- Clinical Notes: `.txt`, `.pdf`, `.docx`
- Billing Codes: `.csv`, `.json`

---

## Next Steps

Now that you're set up:

1. ✅ Upload your first encounter
2. ✅ Review the generated report
3. ✅ Explore the dashboard analytics
4. ✅ Customize your notification preferences
5. ✅ Join our community forum

**Need immediate assistance?** Our support team is here to help!

---

## Document Information

**Version:** 1.0
**Last Updated:** 2025-09-30
**Audience:** RevRX Users (Medical Coders, Physicians, Billing Specialists)

**Feedback:** Help us improve this guide! Email docs@revrx.com with suggestions.
