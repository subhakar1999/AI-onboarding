import re

class GuardrailsService:
    # Enterprise Sanitization Regex Patterns
    EMAIL_PATTERN = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    SSN_PATTERN = r"\b\d{3}-\d{2}-\d{4}\b"
    CREDIT_CARD_PATTERN = r"\b(?:\d{4}[-\s]?){3}\d{4}\b"
    BEARER_TOKEN = r"ey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9._-]{10,}|(ghp|xoxb|akIA)[A-Za-z0-9]{20,}"

    @classmethod
    def sanitize_input(cls, text: str) -> tuple[str, bool]:
        sanitized = text
        redacted = False

        if re.search(cls.EMAIL_PATTERN, sanitized):
            sanitized = re.sub(cls.EMAIL_PATTERN, "[REDACTED_EMAIL]", sanitized)
            redacted = True
            
        if re.search(cls.SSN_PATTERN, sanitized):
            sanitized = re.sub(cls.SSN_PATTERN, "[REDACTED_SSN]", sanitized)
            redacted = True

        if re.search(cls.CREDIT_CARD_PATTERN, sanitized):
            sanitized = re.sub(cls.CREDIT_CARD_PATTERN, "[REDACTED_CARD]", sanitized)
            redacted = True

        if re.search(cls.BEARER_TOKEN, sanitized):
            sanitized = re.sub(cls.BEARER_TOKEN, "[REDACTED_API_SECRET]", sanitized)
            redacted = True

        return sanitized, redacted