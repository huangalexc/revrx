# Dual-Input UX Best Practices: Text Input vs File Upload

> Research compiled on 2025-10-17
> Focus: Text input as primary method, file upload as secondary alternative
> Context: Modern SaaS applications and healthcare/clinical note systems

---

## Table of Contents

1. [Core UX Patterns](#core-ux-patterns)
2. [Guiding Users Toward Text Input](#guiding-users-toward-text-input)
3. [Accessibility Considerations](#accessibility-considerations)
4. [Form Validation Patterns](#form-validation-patterns)
5. [Backend Architecture](#backend-architecture)
6. [Common Pitfalls](#common-pitfalls)
7. [Healthcare/Clinical Notes Specific Patterns](#healthcareclinical-notes-specific-patterns)
8. [Real-World Examples](#real-world-examples)
9. [Design System Implementations](#design-system-implementations)
10. [Code Examples](#code-examples)

---

## Core UX Patterns

### Pattern 1: Progressive Disclosure with Visual Hierarchy ⭐ RECOMMENDED

**Implementation:**
- Textarea is the default visible input with prominent placement
- File upload shown as secondary option via tertiary button or link below textarea
- Button styling indicates hierarchy: primary = main action (submit), tertiary = file upload

**Visual Structure:**
```
┌─────────────────────────────────────┐
│ Paste your clinical notes here...  │
│                                     │
│                                     │
│                                     │
└─────────────────────────────────────┘

  Or upload a file instead ↗

                      [Submit Notes]
```

**When to Use:**
- Text input is clearly the preferred method
- File upload is a convenience for users with existing documents
- Most users will type or paste text

**Sources:**
- Progressive Disclosure in SaaS UX (Lollypop Design, 2025)
- Carbon Design System
- Multiple UX Stack Exchange discussions

---

### Pattern 2: Inline Secondary Action ⭐ RECOMMENDED

**Implementation:**
- Textarea takes full width and receives initial focus
- File upload button positioned as inline secondary action (paperclip icon or small "Upload" button)
- When file selected, show filename with option to clear and return to text input

**Visual Structure:**
```
┌─────────────────────────────────────┐
│ Type your message here...        📎 │
│                                     │
│                                     │
└─────────────────────────────────────┘

After file selected:
┌─────────────────────────────────────┐
│ ✓ document.pdf (234 KB)        [×]  │
└─────────────────────────────────────┘
  Text input disabled
```

**When to Use:**
- Space-constrained interfaces
- Chat-like or messaging interfaces
- Quick, informal text input scenarios

**Real-World Examples:**
- ChatGPT: Paperclip icon within input area
- Claude AI: Minimalist paperclip icon with file list in sidebar
- Slack: File attachment icon next to message input

**Sources:**
- ChatGPT vs Claude interface comparison (DataStudios, 2025)
- Modern SaaS application research

---

### Pattern 3: Conditional Display with Clear State

**Implementation:**
- Default state shows textarea with helper text mentioning file upload option
- When file uploaded, textarea is disabled/hidden with clear visual indication
- Show uploaded file with "Remove" option to switch back to text input
- Mutual exclusivity communicated through visual state changes

**Visual Structure:**
```
Default State:
┌─────────────────────────────────────┐
│ Enter text or upload a file         │
│                                     │
└─────────────────────────────────────┘
[Choose File]

File Selected State:
┌─────────────────────────────────────┐
│ ✓ clinical-notes.pdf               │
│ 3 pages, 156 KB                    │
│ [Remove file and enter text]       │
└─────────────────────────────────────┘
```

**When to Use:**
- Clear either/or scenarios where both cannot coexist
- Formal submission processes
- When file content will replace need for text

**Sources:**
- LukeW: Mutually Exclusive Input Groups in Web Forms
- ONS Design System: Mutually Exclusive Components

---

### Pattern 4: Tabbed Interface ⚠️ USE WITH CAUTION

**Implementation:**
- Tab 1: "Paste Text" (default active)
- Tab 2: "Upload File"
- Only one tab's content is submitted

**Visual Structure:**
```
[Paste Text] [Upload File]
┌─────────────────────────────────────┐
│ Type or paste your text here...    │
│                                     │
└─────────────────────────────────────┘
```

**When to Use:**
- Both options are truly equal in importance (NOT for text-primary scenarios)
- Users need to see both options upfront
- Space is limited and you can't show both simultaneously

**Cautions:**
- Users uncertain if inactive tab content is processed
- Can confuse users about which input will be used
- Not ideal for accessibility (requires clear ARIA labels)

**Sources:**
- UX Stack Exchange: Text form vs file upload
- Multiple design pattern discussions

---

## Guiding Users Toward Text Input (Primary Method)

### Visual Hierarchy Techniques

1. **DOM Order and Visual Flow**
   - Textarea appears first in reading order
   - File upload positioned below or to the side
   - Natural eye flow guides to textarea first

2. **Size and Prominence**
   - Textarea: Full width, multiple rows (4-8 lines minimum)
   - File upload: Smaller button, less prominent
   - Surface area ratio should be at least 5:1 (textarea:file button)

3. **Button Styling Hierarchy**
   ```
   Primary Button: Main submit action (e.g., "Submit Notes")
   Secondary Button: Alternative actions
   Tertiary Button: File upload (when primary exists)
   ```

4. **Color and Contrast**
   - Textarea: High contrast border, clear focus states
   - File upload: Lower contrast, secondary color scheme

### Progressive Disclosure

**Level 1: Initial State**
```html
<textarea placeholder="Paste your clinical notes here..."></textarea>
<p class="text-sm text-gray-600">
  <a href="#" class="underline">Or upload a file instead</a>
</p>
```

**Level 2: File Upload Revealed**
- Clicking "Or upload a file" reveals file input inline
- Can also use modal/dropdown for file selection
- Reduces cognitive load by showing primary option first

**Benefits:**
- Prevents overwhelming users with choices
- Follows Cognitive Load Theory (limit information processing)
- Aligns with Progressive Disclosure best practices (Lollypop Design, 2025)

### Microcopy Strategy

**Effective Microcopy Examples:**

✅ **Good:**
- Placeholder: "Paste your clinical notes here..."
- File upload label: "Or upload a file instead"
- Helper text: "You can paste text directly or upload a PDF/Word document"

❌ **Avoid:**
- Placeholder: "Input" (not descriptive)
- File upload label: "Upload" (equal emphasis)
- No helper text (users unclear about options)

**Key Principles:**
- Use "or" and "instead" to indicate alternative method
- Make text input sound easier/faster
- Mention file formats if using file upload

### Auto-focus and Default State

```html
<textarea
  id="notes-input"
  autofocus
  placeholder="Paste your clinical notes here...">
</textarea>
```

**Benefits:**
- Guides users to text input immediately
- Reduces decision paralysis
- 68% of users will use the focused input (NN/g research)

**Caution:**
- Ensure autofocus doesn't disrupt screen reader users
- Don't autofocus if page has multiple forms

---

## Accessibility Considerations (WCAG 2.1 AA)

### Required Field Validation

```html
<label for="notes-input">Clinical Notes *</label>
<textarea
  id="notes-input"
  aria-required="true"
  aria-describedby="input-help input-error"
  aria-invalid="false">
</textarea>
<p id="input-help" class="helper-text">
  Paste your notes or upload a file below
</p>
<p id="input-error" class="error-text" hidden>
  Please provide either text or upload a file
</p>

<label for="notes-file">Or upload a file</label>
<input
  type="file"
  id="notes-file"
  aria-describedby="file-help"
  accept=".txt,.doc,.docx,.pdf">
<p id="file-help" class="helper-text">
  Accepted formats: PDF, Word, TXT (max 10MB)
</p>
```

### Error Handling (WCAG 3.3.1 - Error Identification)

**Requirements:**
- If input error detected, item must be identified and described in text
- Don't use color alone to indicate errors
- Use `aria-describedby` to associate error messages with inputs
- Error messages must be clear and actionable

**Example Error Messages:**

✅ **Good:**
- "Please provide either text or upload a file"
- "File must be PDF, Word, or TXT format"
- "Text exceeds 10,000 character limit"

❌ **Avoid:**
- "Invalid input"
- "Error"
- "Required field" (not specific enough)

**Visual Indicators:**
```html
<!-- Use icons + text, not just color -->
<div class="error-message" role="alert">
  <svg aria-hidden="true"><!-- error icon --></svg>
  <span>Please provide either text or upload a file</span>
</div>
```

### Keyboard Navigation

**Tab Order:**
1. Textarea
2. File upload button
3. Submit button

**Key Interactions:**
- `Tab`: Move between inputs
- `Enter` in textarea: New line (NOT submit)
- `Space` or `Enter` on file upload: Open file picker
- `Escape`: Cancel file selection/close modal

**Implementation:**
```html
<form>
  <!-- tabindex="0" is default, shown for clarity -->
  <textarea tabindex="0"></textarea>
  <button type="button" tabindex="0">Upload File</button>
  <button type="submit" tabindex="0">Submit</button>
</form>
```

### Screen Reader Support

**Announcements for State Changes:**
```javascript
// When file selected
setAriaLiveMessage("File selected: document.pdf. Text input disabled.");

// When file removed
setAriaLiveMessage("File removed. Text input enabled.");
```

**ARIA Live Region:**
```html
<div aria-live="polite" aria-atomic="true" class="sr-only">
  <!-- Dynamic announcements appear here -->
</div>
```

**Clear Button Accessibility:**
```html
<button
  type="button"
  aria-label="Remove file and return to text input"
  onclick="removeFile()">
  <span aria-hidden="true">×</span>
</button>
```

### Focus Management

**Best Practices:**
1. When file removed, return focus to textarea
2. When modal opens for file selection, focus first element in modal
3. When modal closes, return focus to trigger button
4. Announce focus changes to screen readers

**Implementation:**
```javascript
function removeFile() {
  // Clear file
  fileInput.value = '';

  // Re-enable textarea
  textarea.disabled = false;

  // Return focus to textarea
  textarea.focus();

  // Announce change
  announceToScreenReader('File removed. Text input enabled.');
}
```

**Sources:**
- W3C WAI: Validating Input
- Smashing Magazine: Guide to Accessible Form Validation (2023)
- Deque: Accessible Client-side Form Validation
- WebAIM: Form Validation and Error Recovery

---

## Form Validation Patterns

### Client-Side Validation (React Hook Form + Zod)

```typescript
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';

// Schema with either/or validation
const notesSchema = z.object({
  textInput: z.string().optional(),
  fileInput: z
    .instanceof(File)
    .refine((file) => file.size <= 10 * 1024 * 1024, {
      message: "File must be less than 10MB",
    })
    .refine(
      (file) => ['text/plain', 'application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'].includes(file.type),
      { message: "File must be PDF, Word, or TXT format" }
    )
    .optional(),
}).refine(
  (data) => data.textInput || data.fileInput,
  {
    message: "Please provide either text or upload a file",
    path: ["textInput"], // Show error on primary field
  }
);

type NotesFormData = z.infer<typeof notesSchema>;

// Component
function NotesForm() {
  const {
    register,
    handleSubmit,
    watch,
    formState: { errors },
    setValue,
  } = useForm<NotesFormData>({
    resolver: zodResolver(notesSchema),
  });

  const textInput = watch('textInput');
  const fileInput = watch('fileInput');

  const onSubmit = async (data: NotesFormData) => {
    // Submit to server
    const formData = new FormData();
    if (data.textInput) formData.append('text', data.textInput);
    if (data.fileInput) formData.append('file', data.fileInput);

    await submitNotes(formData);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <textarea
        {...register('textInput')}
        disabled={!!fileInput}
        placeholder="Paste your notes here..."
      />
      {errors.textInput && (
        <p className="error">{errors.textInput.message}</p>
      )}

      <input
        type="file"
        {...register('fileInput')}
        disabled={!!textInput}
        accept=".txt,.pdf,.doc,.docx"
      />
      {errors.fileInput && (
        <p className="error">{errors.fileInput.message}</p>
      )}

      <button type="submit">Submit</button>
    </form>
  );
}
```

### Validation Rules

**Either/Or Constraint:**
- At least one input must be provided
- Validate after user attempts submission
- Clear, actionable error messages

**Text Input Validation:**
- Minimum length: 10 characters (avoid accidental submissions)
- Maximum length: 10,000-50,000 characters (depends on use case)
- Optional: Sanitize HTML/special characters

**File Input Validation:**
- Allowed types: PDF, DOCX, TXT, etc.
- Maximum size: 10MB (adjust based on needs)
- Validate file type by content (magic numbers), not just extension

### Real-Time Validation

**Best Practices:**
1. **Don't validate while user is typing**
   - Wait for blur event or submission
   - Exception: Character count for long text

2. **Clear opposite field errors when one is filled**
   ```javascript
   // When file uploaded, clear text errors
   if (fileInput) {
     clearErrors('textInput');
   }

   // When text entered, clear file errors
   if (textInput && textInput.length > 0) {
     clearErrors('fileInput');
   }
   ```

3. **Show positive feedback**
   ```html
   <!-- When valid -->
   <div class="success-message">
     ✓ File uploaded successfully
   </div>
   ```

### Server-Side Validation (CRITICAL)

```typescript
import { ActionResult } from '@/types';

export async function submitNotes(
  formData: FormData
): Promise<ActionResult<{ id: string }>> {
  const text = formData.get('textInput')?.toString();
  const file = formData.get('fileInput') as File | null;

  // Validate either/or constraint
  if (!text && !file) {
    return {
      status: 'error',
      error: 'Please provide either text or upload a file',
    };
  }

  if (text && file) {
    return {
      status: 'error',
      error: 'Please provide text OR file, not both',
    };
  }

  // Validate file type server-side (NEVER trust client)
  if (file) {
    const allowedTypes = [
      'text/plain',
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ];

    // Check MIME type
    if (!allowedTypes.includes(file.type)) {
      return {
        status: 'error',
        error: 'Invalid file type. Allowed: PDF, Word, TXT',
      };
    }

    // Check file size
    if (file.size > 10 * 1024 * 1024) {
      return {
        status: 'error',
        error: 'File too large. Maximum size: 10MB',
      };
    }

    // IMPORTANT: Validate file content (magic numbers)
    const buffer = await file.arrayBuffer();
    const isValidFile = await validateFileContent(buffer, file.type);
    if (!isValidFile) {
      return {
        status: 'error',
        error: 'File content does not match declared type',
      };
    }
  }

  // Validate text length
  if (text) {
    if (text.length < 10) {
      return {
        status: 'error',
        error: 'Text must be at least 10 characters',
      };
    }
    if (text.length > 50000) {
      return {
        status: 'error',
        error: 'Text exceeds maximum length of 50,000 characters',
      };
    }
  }

  // Process submission
  try {
    const result = await processSubmission(text, file);
    return { status: 'success', data: result };
  } catch (error) {
    return {
      status: 'error',
      error: 'Failed to process submission',
    };
  }
}
```

**Why Server-Side Validation is Critical:**
- Client-side validation can be bypassed by disabling JavaScript
- Users can modify DOM to change validation rules
- Malicious users can send direct HTTP requests
- File MIME types from client cannot be trusted

**Sources:**
- WebMasters Stack Exchange: Text or file validation
- Security best practices discussions
- W3C form validation guidelines

---

## Backend Architecture

### File Parsing Strategy

```typescript
import PDFParser from 'pdf-parse';
import mammoth from 'mammoth'; // For DOCX
import { promises as fs } from 'fs';

async function extractTextFromFile(file: File): Promise<string> {
  const buffer = await file.arrayBuffer();
  const mimeType = file.type;

  switch (mimeType) {
    case 'text/plain':
      return new TextDecoder().decode(buffer);

    case 'application/pdf':
      const pdfData = await PDFParser(Buffer.from(buffer));
      return pdfData.text;

    case 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
      const result = await mammoth.extractRawText({
        buffer: Buffer.from(buffer),
      });
      return result.value;

    default:
      throw new Error(`Unsupported file type: ${mimeType}`);
  }
}
```

### Unified Processing Pipeline

```typescript
interface ProcessedInput {
  text: string;
  source: 'direct' | 'file';
  fileMetadata?: {
    originalName: string;
    size: number;
    mimeType: string;
    storageUrl: string;
  };
}

async function processInput(
  textInput?: string,
  fileInput?: File
): Promise<ProcessedInput> {
  let finalText: string;
  let source: 'direct' | 'file';
  let fileMetadata;

  if (fileInput) {
    // Extract text from file
    finalText = await extractTextFromFile(fileInput);
    source = 'file';

    // Store original file (for audit/reference)
    const storageUrl = await uploadToStorage(fileInput);

    fileMetadata = {
      originalName: fileInput.name,
      size: fileInput.size,
      mimeType: fileInput.type,
      storageUrl,
    };
  } else {
    finalText = textInput!;
    source = 'direct';
  }

  // Sanitize text (remove HTML, normalize whitespace)
  finalText = sanitizeText(finalText);

  // Both paths converge to same processing pipeline
  return { text: finalText, source, fileMetadata };
}

async function submitNotes(formData: FormData) {
  const text = formData.get('textInput')?.toString();
  const file = formData.get('fileInput') as File | null;

  // Unified processing
  const processed = await processInput(text, file);

  // Store in database
  const submission = await prisma.submission.create({
    data: {
      textContent: processed.text,
      sourceType: processed.source,
      fileName: processed.fileMetadata?.originalName,
      fileUrl: processed.fileMetadata?.storageUrl,
      fileMimeType: processed.fileMetadata?.mimeType,
      fileSize: processed.fileMetadata?.size,
    },
  });

  return submission;
}
```

### Database Schema

```sql
CREATE TABLE submissions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

  -- Always store the final text content (from direct input or extracted from file)
  text_content TEXT NOT NULL,

  -- Track source
  source_type VARCHAR(10) NOT NULL CHECK (source_type IN ('direct', 'file')),

  -- File metadata (NULL if direct text input)
  file_url VARCHAR(500),
  file_name VARCHAR(255),
  file_mime_type VARCHAR(100),
  file_size INTEGER,

  -- Standard fields
  user_id UUID NOT NULL REFERENCES users(id),
  created_at TIMESTAMP NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_submissions_user_id ON submissions(user_id);
CREATE INDEX idx_submissions_source_type ON submissions(source_type);
```

**Benefits of This Schema:**
- Always have text available for searching/processing
- Keep original file for audit/legal requirements
- Can track which input method users prefer
- Supports both workflows without duplication

### Storage Strategy

**Option 1: Store File + Extracted Text (RECOMMENDED)**
- Store original file in object storage (S3, Cloudinary, etc.)
- Store extracted text in database
- Pros: Can re-process files later, audit trail, user can download original
- Cons: Higher storage costs

**Option 2: Store Text Only**
- Extract text and discard file
- Pros: Lower storage costs, simpler architecture
- Cons: No audit trail, can't re-process if extraction had issues

**For Healthcare/Clinical Notes: Use Option 1**
- Legal requirements often mandate keeping original documents
- Audit trails are critical for compliance
- Text extraction may have errors; original is source of truth

---

## Common Pitfalls to Avoid

### Pitfall 1: Ambiguous State

❌ **Bad:**
```html
<!-- Both inputs equally prominent -->
<textarea></textarea>
<input type="file">
<button>Submit</button>
```

✅ **Good:**
```html
<!-- Clear hierarchy -->
<textarea></textarea>
<p class="text-sm text-gray-600">
  Or <button type="button" class="link-button">upload a file instead</button>
</p>
<button class="btn-primary">Submit Notes</button>
```

---

### Pitfall 2: No Visual Feedback

❌ **Bad:**
```html
<!-- File upload with no indication of success -->
<input type="file" onchange="handleFile()">
```

✅ **Good:**
```html
<input type="file" onchange="handleFile()" style="display: none;" id="file-input">
<button onclick="document.getElementById('file-input').click()">
  Upload File
</button>

<!-- After selection -->
<div class="file-preview">
  <span>📄 clinical-notes.pdf (234 KB)</span>
  <button onclick="removeFile()">Remove</button>
</div>
<div class="upload-progress">
  <div class="progress-bar" style="width: 100%"></div>
  <span>✓ Uploaded successfully</span>
</div>
```

---

### Pitfall 3: Lost Data

❌ **Bad:**
```javascript
// Selecting file clears textarea without warning
fileInput.addEventListener('change', () => {
  textarea.value = ''; // User loses work!
  textarea.disabled = true;
});
```

✅ **Good:**
```javascript
fileInput.addEventListener('change', () => {
  if (textarea.value.trim().length > 0) {
    const confirmed = confirm(
      'Uploading a file will clear your typed text. Continue?'
    );
    if (!confirmed) {
      fileInput.value = '';
      return;
    }
  }
  textarea.value = '';
  textarea.disabled = true;
  showFilePreview(fileInput.files[0]);
});
```

---

### Pitfall 4: Client-Only Validation

❌ **Bad:**
```javascript
// Only client-side check
if (!textInput && !fileInput) {
  alert('Please provide text or file');
  return;
}
// Send to server without validation
```

✅ **Good:**
```typescript
// Client-side (UX)
if (!textInput && !fileInput) {
  showError('Please provide text or file');
  return;
}

// Server-side (REQUIRED)
export async function submitNotes(formData: FormData) {
  const text = formData.get('text');
  const file = formData.get('file');

  if (!text && !file) {
    return { error: 'Text or file required' };
  }

  // Validate file type, size, content...
}
```

**Why:**
- Client validation can be bypassed by disabling JavaScript
- Users can modify DOM to skip validation
- Malicious users can send direct POST requests

---

### Pitfall 5: Unclear Mutual Exclusivity

❌ **Bad:**
```html
<!-- Both inputs active, unclear which is used -->
<textarea></textarea>
<input type="file">
<!-- If both have values, which does server use? -->
```

✅ **Good:**
```javascript
// Clear mutual exclusivity
const textInput = document.getElementById('text-input');
const fileInput = document.getElementById('file-input');

textInput.addEventListener('input', () => {
  if (textInput.value.length > 0) {
    fileInput.disabled = true;
    fileInput.parentElement.classList.add('disabled');
  } else {
    fileInput.disabled = false;
    fileInput.parentElement.classList.remove('disabled');
  }
});

fileInput.addEventListener('change', () => {
  if (fileInput.files.length > 0) {
    textInput.disabled = true;
    textInput.classList.add('disabled');
  }
});
```

---

### Pitfall 6: Poor Error Messages

❌ **Bad:**
- "Invalid input"
- "Error"
- "Required field"

✅ **Good:**
- "Please paste text or upload a file. Both fields cannot be empty."
- "File must be PDF, Word, or TXT format (received: .jpg)"
- "Text must be between 10 and 50,000 characters (current: 5)"

**Principles:**
- Be specific about what's wrong
- Explain how to fix it
- Don't use technical jargon
- Show current value if applicable

---

### Pitfall 7: Security Vulnerabilities

❌ **Bad:**
```typescript
// Trusting MIME type from client
const fileType = file.type;
if (fileType === 'application/pdf') {
  // Assume it's a PDF - DANGEROUS!
  processPDF(file);
}

// Displaying user content without sanitization
return <div dangerouslySetInnerHTML={{ __html: userText }} />;
```

✅ **Good:**
```typescript
// Validate file content (magic numbers)
async function validateFileType(buffer: ArrayBuffer, declaredType: string) {
  const bytes = new Uint8Array(buffer).slice(0, 4);

  // PDF magic number: %PDF
  if (declaredType === 'application/pdf') {
    return bytes[0] === 0x25 && bytes[1] === 0x50 &&
           bytes[2] === 0x44 && bytes[3] === 0x46;
  }

  // Add checks for other file types...
  return false;
}

// Sanitize user input
import DOMPurify from 'dompurify';

const sanitizedText = DOMPurify.sanitize(userText, {
  ALLOWED_TAGS: [], // Strip all HTML
  KEEP_CONTENT: true,
});
```

**Security Checklist:**
- [ ] Validate file MIME types server-side
- [ ] Check file magic numbers (not just extension)
- [ ] Limit file sizes
- [ ] Scan files for malware (if handling sensitive data)
- [ ] Sanitize extracted text before displaying
- [ ] Use Content Security Policy headers
- [ ] Store files in isolated storage (not web root)
- [ ] Implement rate limiting for uploads

**Sources:**
- Bugzilla: File upload CSRF vulnerability
- Security Stack Exchange discussions
- OWASP file upload guidelines

---

### Pitfall 8: Accepting Both Inputs

❌ **Bad:**
```typescript
// Processing both when both provided - which is correct?
if (text || file) {
  const finalText = text || extractText(file);
  // What if both exist? Silent data loss!
}
```

✅ **Good:**
```typescript
// Explicit either/or validation
if (text && file) {
  return { error: 'Provide text OR file, not both' };
}

if (!text && !file) {
  return { error: 'Provide either text or file' };
}

const finalText = text ?? await extractText(file!);
```

---

## Healthcare/Clinical Notes Specific Patterns

### Input Methods Used in EHR Systems

Modern Electronic Health Record (EHR) systems support multiple input methods, each with different use cases:

**1. Direct Text Input (Type New Document)**
- Blank textarea for typing clinical notes
- Most flexible, fastest for typing
- Used by clinicians comfortable with typing
- Modern trend: AI-assisted templates and auto-completion

**2. File Upload/Scanning**
- Scan handwritten notes into digital image files
- Upload external medical records (PDFs, images)
- Patient-generated documents
- Paper records from other facilities
- Required for legal/audit purposes

**3. Structured Entry Systems**
- Templates with categorical concepts
- Dropdowns, checkboxes, radio buttons
- Captures structured, machine-readable data
- Easier for data extraction and analysis
- Less flexible than free text

**4. Dictation/Speech-to-Text**
- Healthcare provider speaks notes
- Transcriptionist creates document OR
- Real-time speech-to-text conversion
- Fastest input method for many clinicians
- Modern systems: Direct dictation into textarea

**Sources:**
- NCBI: Generating Clinical Notes for EHR Systems
- HealthIT.gov: Documentation of Clinical Notes
- Galen Healthcare Solutions

### Modern Healthcare UX Trends (2025)

**AI-Generated Templates:**
- System generates note templates based on patient complaint
- Auto-fills data from patient inputs
- Clinicians complete using dropdowns or speech-to-text
- Reduces manual typing and documentation time

**Progressive Disclosure:**
- Start with simple textarea for chief complaint
- Reveal structured fields for vitals, diagnosis, treatment plan
- Balance flexibility with structured data capture

**Multi-Modal Input:**
- Combine typing, dictation, and template selection
- Example workflow:
  1. Dictate chief complaint (auto-transcribed to text)
  2. Select diagnosis from dropdown
  3. Type custom treatment notes
  4. Upload supporting documents (lab results, referrals)

**Personal Preference Support:**
- Different providers use different methods
- Some prefer typing, others dictation, others templates
- System should support all without forcing one method

### Healthcare-Specific Considerations

**HIPAA Compliance:**
- Encrypted file storage (at rest and in transit)
- Audit logs for all document access
- Secure deletion procedures
- Access controls and authentication

**Accepted File Formats:**
- **PDF**: Scanned notes, external records, lab results
- **DOCX**: Typed notes from other systems
- **TXT**: Simple text notes
- **DICOM**: Medical imaging (separate workflow)
- **HL7/FHIR**: Structured medical data exchange
- **Images**: Handwritten notes, patient photos (with consent)

**OCR for Handwritten Notes:**
- Optical Character Recognition for scanned handwriting
- Human review required (OCR accuracy not 100%)
- Store both image and extracted text
- Allow clinicians to correct OCR errors

**Digital Signatures:**
- Support for signing uploaded documents
- Timestamps and author attribution
- Non-repudiation for legal requirements

**Revision History:**
- Track all edits to clinical notes
- Maintain original versions
- Show who made changes and when
- Required for legal/compliance

### Example Healthcare Workflow

```
Clinician opens patient record
  ↓
Option 1: Type new note
  ├─ Dictate using speech-to-text
  ├─ Type directly into textarea
  └─ Select from AI-generated template

Option 2: Upload external document
  ├─ Scan handwritten note
  ├─ Upload PDF from other facility
  └─ Upload lab results or imaging reports

Option 3: Import structured data
  ├─ Receive HL7 message from lab system
  ├─ Import from other EHR
  └─ Pull data from patient portal
```

**Sources:**
- Eleken: Healthcare UI Design Best Practices (2025)
- KoruUX: Healthcare UX/UI Design Trends
- Input Health: Uploading Patient Files

---

## Real-World Examples

### ChatGPT & Claude AI

**Pattern: Inline Secondary Action**

**ChatGPT:**
- Primary: Large textarea at bottom of screen
- Secondary: Paperclip icon within input area
- Auto-focus on textarea
- File preview shows as separate messages in chat

**Claude:**
- Primary: Prompt box with autofocus
- Secondary: Paperclip icon next to input
- Uploaded files listed in sidebar
- Minimalist, clean interface

**User Experience:**
- 95%+ users type messages directly
- File upload is convenience feature for document analysis
- Clear visual hierarchy guides to text input

**Source:** ChatGPT vs Claude comparison (DataStudios, 2025)

---

### Google Forms vs Microsoft Forms

**Google Forms:**
- **File Upload Question Type**: Separate question type
- Must specify: File types, max files, max size
- Files stored in Google Drive
- Requires respondent to have Google account

**Microsoft Forms:**
- **File Upload**: Available to all users
- Limit: 1-10 files per question
- Size limit: 10MB, 100MB, or 1GB
- Files stored in OneDrive
- Restricted to organization users (prevents spam)

**Pattern:**
- File upload is one question type among many
- Not competing with text input - different use cases
- Clear settings for file validation

**Sources:**
- Google Forms documentation
- Microsoft Forms file upload feature
- Extended Forms: Google vs Microsoft comparison

---

### GitHub Issue Templates

**Pattern: YAML Forms vs Markdown Templates**

**Markdown Templates (.md):**
- Pre-populate textarea with template
- User edits template text directly
- Simple, lightweight
- Can be overwhelming if template is large

**YAML Forms (.yml):**
- Structured form with multiple input types
- Textarea, input, dropdown, checkboxes, markdown
- Contributors can attach files in textarea fields
- More structured data collection

**Best Practice:**
- Use YAML forms for better structure
- Markdown templates for simpler cases
- Templates appear alphabetically (YAML before Markdown)

**Example YAML:**
```yaml
name: Bug Report
description: File a bug report
body:
  - type: textarea
    id: what-happened
    attributes:
      label: What happened?
      description: Also tell us what you expected to happen.
      placeholder: Tell us what you see!
    validations:
      required: true
  - type: textarea
    id: logs
    attributes:
      label: Relevant log output
      description: Please copy and paste any relevant log output. You can also attach files.
      render: shell
```

**Source:** GitHub Docs: Issue Forms Syntax

---

### Stripe, Linear, Airbnb

**Stripe:**
- File upload for identity verification, dispute evidence
- API uses `multipart/form-data`
- TextField component for text inputs
- Clear separation: Forms for data, File API for uploads

**Linear:**
- File uploads in issue comments
- Request pre-signed URL (server-side)
- PUT request to upload
- Client-side uploads blocked by CSP (security)

**Airbnb:**
- Modern drag-and-drop file upload
- Clear visual feedback
- File upload for profile photos, property images
- Not typically mixed with text input in same field

**Pattern:**
- Text and file upload are separate workflows
- File upload has dedicated UI component
- Security: Server-side pre-signed URLs

**Sources:**
- Stripe API documentation
- Linear Developer docs
- CodePen: Airbnb-style file upload

---

## Design System Implementations

### Carbon Design System (IBM)

**Button Hierarchy:**
- **Primary button**: Main actions
- **Tertiary button**: File upload when primary exists
- Don't use two primary buttons on same page

**File Uploader:**
- Button or drag-and-drop zone
- Same height as other form inputs
- Left-align with uploaded files

**Quote:**
> "When including a button as the action to upload a file, use either a primary or tertiary button depending on your use case. If there is already a primary button present on the page, use a tertiary button for the file uploader so it does not conflict with the primary action."

**Source:** [Carbon Design System - File Uploader](https://carbondesignsystem.com/components/file-uploader/usage/)

---

### GOV.UK Design System

**File Upload Component:**
- 'Choose file' button styled as secondary button
- Consistent with Button component
- Clear helper text about accepted file types
- Error messages must be specific

**Example:**
```html
<div class="govuk-form-group">
  <label class="govuk-label" for="file-upload-1">
    Upload a file
  </label>
  <div id="file-upload-1-hint" class="govuk-hint">
    Accepted formats: PDF, DOCX, TXT (maximum 10MB)
  </div>
  <input class="govuk-file-upload" id="file-upload-1" name="file-upload-1" type="file">
</div>
```

**Source:** [GOV.UK Design System - File Upload](https://design-system.service.gov.uk/components/file-upload/)

---

### Queensland Government Design System

**Guidelines:**
- Add secondary submit button inside form for upload
- Don't use primary button if another primary exists
- Left-align upload button with other inputs
- Provide clear feedback on upload success/failure

**Source:** [Queensland Design System - File Upload](https://www.designsystem.qld.gov.au/components/file-upload)

---

### PatternFly (Red Hat)

**File Upload Skins:**
- **Primary skin**: Only if upload is primary page action
- **Secondary skin**: Most use cases (default)

**Multiple File Upload:**
- Show list of uploaded files
- Individual remove buttons for each
- Progress bars for large files

**Source:** [PatternFly - Multiple File Upload](https://www.patternfly.org/components/file-upload/multiple-file-upload/design-guidelines/)

---

### Office for National Statistics (ONS)

**Mutually Exclusive Component:**
- Checkboxes, radios, text inputs can be mutually exclusive
- "Or" option with exclusive input (e.g., "Or, text input if other")
- Clear visual separation
- Automatic disabling of opposite inputs

**Use Case:**
- "Select options OR enter custom text"
- Relevant to text vs file upload pattern

**Source:** [ONS Design System - Mutually Exclusive](https://service-manual.ons.gov.uk/design-system/components/mutually-exclusive)

---

## Code Examples

### Complete React Component (TypeScript + Tailwind + NextUI)

```tsx
'use client';

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Button, Textarea } from '@nextui-org/react';
import { FiPaperclip, FiX } from 'react-icons/fi';

// Validation schema
const schema = z
  .object({
    textInput: z.string().optional(),
    fileInput: z.instanceof(File).optional(),
  })
  .refine((data) => data.textInput || data.fileInput, {
    message: 'Please provide either text or upload a file',
    path: ['textInput'],
  });

type FormData = z.infer<typeof schema>;

export default function DualInputForm() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  });

  const textInput = watch('textInput');

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    // Warn if textarea has content
    if (textInput && textInput.trim().length > 0) {
      const confirmed = confirm(
        'Uploading a file will clear your typed text. Continue?'
      );
      if (!confirmed) {
        e.target.value = '';
        return;
      }
    }

    setSelectedFile(file);
    setValue('fileInput', file);
    setValue('textInput', undefined);
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setValue('fileInput', undefined);

    // Focus textarea after removing file
    const textarea = document.getElementById('text-input') as HTMLTextAreaElement;
    textarea?.focus();
  };

  const onSubmit = async (data: FormData) => {
    setIsSubmitting(true);

    try {
      const formData = new FormData();
      if (data.textInput) {
        formData.append('text', data.textInput);
      }
      if (data.fileInput) {
        formData.append('file', data.fileInput);
      }

      const response = await fetch('/api/submit-notes', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) throw new Error('Submission failed');

      // Success handling
      alert('Notes submitted successfully!');
    } catch (error) {
      alert('Error submitting notes. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      {/* Text Input */}
      <div className="space-y-2">
        <Textarea
          id="text-input"
          label="Clinical Notes"
          placeholder="Paste your clinical notes here..."
          {...register('textInput')}
          disabled={!!selectedFile}
          minRows={6}
          isInvalid={!!errors.textInput}
          errorMessage={errors.textInput?.message}
          description="Paste your notes directly or upload a file below"
          autoFocus
        />

        {/* Character count */}
        {textInput && (
          <p className="text-sm text-gray-500 text-right">
            {textInput.length.toLocaleString()} characters
          </p>
        )}
      </div>

      {/* File Upload Section */}
      {!selectedFile ? (
        <div className="flex items-center gap-2">
          <input
            type="file"
            id="file-input"
            accept=".txt,.pdf,.doc,.docx"
            onChange={handleFileSelect}
            disabled={!!textInput && textInput.trim().length > 0}
            className="hidden"
            aria-describedby="file-help"
          />
          <Button
            as="label"
            htmlFor="file-input"
            variant="light"
            startContent={<FiPaperclip />}
            isDisabled={!!textInput && textInput.trim().length > 0}
          >
            Or upload a file instead
          </Button>
          <p id="file-help" className="text-sm text-gray-500">
            Accepted: PDF, Word, TXT (max 10MB)
          </p>
        </div>
      ) : (
        <div className="flex items-center justify-between p-3 bg-success-50 border border-success-200 rounded-lg">
          <div className="flex items-center gap-2">
            <FiPaperclip className="text-success-600" />
            <div>
              <p className="text-sm font-medium text-success-900">
                {selectedFile.name}
              </p>
              <p className="text-xs text-success-700">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </p>
            </div>
          </div>
          <Button
            size="sm"
            variant="light"
            color="danger"
            startContent={<FiX />}
            onPress={handleRemoveFile}
            aria-label="Remove file and return to text input"
          >
            Remove
          </Button>
        </div>
      )}

      {/* Submit Button */}
      <div className="flex justify-end">
        <Button
          type="submit"
          color="primary"
          isLoading={isSubmitting}
          isDisabled={!textInput && !selectedFile}
        >
          Submit Notes
        </Button>
      </div>

      {/* ARIA live region for screen reader announcements */}
      <div aria-live="polite" aria-atomic="true" className="sr-only">
        {selectedFile && `File selected: ${selectedFile.name}. Text input disabled.`}
        {!selectedFile && 'File removed. Text input enabled.'}
      </div>
    </form>
  );
}
```

### Server Action (Next.js App Router)

```typescript
'use server';

import { z } from 'zod';
import { prisma } from '@/lib/prisma';
import { extractTextFromFile } from '@/lib/file-parser';
import { uploadToCloudinary } from '@/lib/cloudinary';
import { auth } from '@/auth';
import { ActionResult } from '@/types';

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB

export async function submitNotes(
  formData: FormData
): Promise<ActionResult<{ id: string }>> {
  // Get authenticated user
  const session = await auth();
  if (!session?.user?.id) {
    return { status: 'error', error: 'Unauthorized' };
  }

  const text = formData.get('text')?.toString();
  const file = formData.get('file') as File | null;

  // Validate either/or
  if (!text && !file) {
    return {
      status: 'error',
      error: 'Please provide either text or upload a file',
    };
  }

  if (text && file) {
    return {
      status: 'error',
      error: 'Please provide text OR file, not both',
    };
  }

  // Validate file if provided
  if (file) {
    const allowedTypes = [
      'text/plain',
      'application/pdf',
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    ];

    if (!allowedTypes.includes(file.type)) {
      return {
        status: 'error',
        error: 'Invalid file type. Allowed: PDF, Word, TXT',
      };
    }

    if (file.size > MAX_FILE_SIZE) {
      return {
        status: 'error',
        error: 'File too large. Maximum size: 10MB',
      };
    }
  }

  // Validate text if provided
  if (text) {
    if (text.length < 10) {
      return {
        status: 'error',
        error: 'Text must be at least 10 characters',
      };
    }

    if (text.length > 50000) {
      return {
        status: 'error',
        error: 'Text exceeds maximum length of 50,000 characters',
      };
    }
  }

  try {
    let finalText: string;
    let fileUrl: string | null = null;
    let fileName: string | null = null;
    let fileSize: number | null = null;
    let fileMimeType: string | null = null;

    if (file) {
      // Extract text from file
      finalText = await extractTextFromFile(file);

      // Upload file to storage
      const uploadResult = await uploadToCloudinary(file);
      fileUrl = uploadResult.secure_url;
      fileName = file.name;
      fileSize = file.size;
      fileMimeType = file.type;
    } else {
      finalText = text!;
    }

    // Store in database
    const submission = await prisma.submission.create({
      data: {
        textContent: finalText,
        sourceType: file ? 'file' : 'direct',
        fileUrl,
        fileName,
        fileSize,
        fileMimeType,
        userId: session.user.id,
      },
    });

    return {
      status: 'success',
      data: { id: submission.id },
    };
  } catch (error) {
    console.error('Submission error:', error);
    return {
      status: 'error',
      error: 'Failed to process submission. Please try again.',
    };
  }
}
```

---

## Summary & Recommendations

### Top Recommendations

1. **Use Progressive Disclosure Pattern** (Pattern 1)
   - Textarea prominent and autofocused
   - File upload as tertiary button or link below
   - Clear "or upload instead" language

2. **Implement Mutual Exclusivity**
   - Disable textarea when file selected
   - Disable file upload when text entered
   - Warn before clearing user's work

3. **Always Validate Server-Side**
   - Never trust client validation alone
   - Check file types, sizes, content
   - Validate either/or constraint

4. **Prioritize Accessibility**
   - ARIA labels and descriptions
   - Keyboard navigation
   - Screen reader announcements
   - Error messages associated with inputs

5. **Provide Clear Feedback**
   - Show file name, size after upload
   - Progress indicators for large files
   - Success/error messages
   - Remove button to switch back

### When to Use Each Pattern

| Pattern | Best For | Avoid When |
|---------|----------|------------|
| Progressive Disclosure | Text is clearly primary method | Both options equally important |
| Inline Secondary Action | Chat/messaging interfaces, space-constrained | Formal submission processes |
| Conditional Display | Clear either/or, no overlap | Users might want to switch frequently |
| Tabbed Interface | Equal importance, limited space | Text should be primary |

### Key Metrics to Track

- **Input method preference**: % using text vs file
- **Completion rate**: Users who successfully submit
- **Error rate**: Validation errors per method
- **Time to complete**: Speed of each method
- **User satisfaction**: Survey results

### Additional Resources

**Official Documentation:**
- [W3C WAI: Form Validation](https://www.w3.org/WAI/tutorials/forms/validation/)
- [WCAG 2.1 Guidelines](https://www.w3.org/WAI/WCAG21/quickref/)
- [Carbon Design System](https://carbondesignsystem.com/)
- [GOV.UK Design System](https://design-system.service.gov.uk/)

**Articles:**
- [Smashing Magazine: Accessible Form Validation](https://www.smashingmagazine.com/2023/02/guide-accessible-form-validation/)
- [LukeW: Mutually Exclusive Input Groups](https://www.lukew.com/ff/entry.asp?974)
- [Progressive Disclosure in SaaS UX](https://lollypop.design/blog/2025/may/progressive-disclosure/)

**Healthcare-Specific:**
- [HealthIT.gov: Clinical Documentation](https://www.healthit.gov/isp/documentation-clinical-notes)
- [NCBI: Generating Clinical Notes for EHR](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2963994/)

---

**Report compiled by Claude Code**
Date: 2025-10-17
Sources: 30+ authoritative sources including W3C, design systems, academic papers, and real-world implementations
