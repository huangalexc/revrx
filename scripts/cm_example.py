import boto3

client = boto3.client("comprehendmedical", region_name="us-east-1")

text = """
Patient John Smith was admitted on 04/15/2024 with chest pain.
Phone: (555) 123-4567. Lives at 123 Main St.
"""

# Detect PHI
phi_response = client.detect_phi(Text=text)

# Sort entities in reverse order (to avoid messing up offsets during replacement)
entities = sorted(phi_response["Entities"], key=lambda x: x["BeginOffset"], reverse=True)

# Redact PHI with placeholders
redacted_text = text
for entity in entities:
    start, end = entity["BeginOffset"], entity["EndOffset"]
    placeholder = f"[{entity['Type']}]"
    redacted_text = redacted_text[:start] + placeholder + redacted_text[end:]

print("Original Text:")
print(text)

print("\nRedacted Text:")
print(redacted_text)