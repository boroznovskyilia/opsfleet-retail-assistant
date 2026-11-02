"""Defense in depth; database column exclusion is the primary PII boundary."""

import re

EMAIL = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
PHONE = re.compile(r"(?<![\w])\+?\d[\d ()-]{8,}\d(?![\w])")
ADDRESS = re.compile(
    r"\b\d+\s+(?:[A-Za-z]+\s+){1,4}(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln)\b", re.I
)
PRIVATE_REQUEST = re.compile(
    r"\b(?:first_name|last_name|street_address|ip_address|postal_code|latitude|longitude)\b|\b(?:customers?'?\s+(?:names?|emails?|addresses|phones?)|email addresses|phone numbers)\b",
    re.I,
)


def scrub(text: str) -> str:
    text = re.sub(r"\x1b\[[0-?]*[ -/]*[@-~]", "", text)
    text = "".join(c for c in text if c in "\n\t" or ord(c) >= 32)
    text = re.sub(r"sk-(?:or-)?[A-Za-z0-9_-]{12,}", "[REDACTED_KEY]", text)
    text = EMAIL.sub("[REDACTED_EMAIL]", text)
    # ISO dates break phone candidates; a preceding year must not absorb the date.
    parts = re.split(r"(\b\d{4}-\d{2}-\d{2}\b)", text)
    for index in range(0, len(parts), 2):
        parts[index] = PHONE.sub(
            lambda m: (
                "[REDACTED_PHONE]" if sum(c.isdigit() for c in m[0]) >= 10 else m[0]
            ),
            parts[index],
        )
    text = "".join(parts)
    return ADDRESS.sub("[REDACTED_ADDRESS]", text)
