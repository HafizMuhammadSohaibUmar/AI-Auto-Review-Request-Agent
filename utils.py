"""Small shared utilities."""
import re


STOP_WORDS = {"STOP", "UNSUBSCRIBE", "CANCEL", "QUIT", "END", "OPTOUT"}


def normalize_phone(phone: str, default_country_code: str = "+1") -> str:
    """Normalize phone input to a conservative E.164-like string."""
    raw = (phone or "").strip()
    if raw.startswith("+"):
        digits = "+" + re.sub(r"\D", "", raw)
    else:
        digits_only = re.sub(r"\D", "", raw)
        if len(digits_only) == 10:
            digits = default_country_code + digits_only
        elif digits_only.startswith("00"):
            digits = "+" + digits_only[2:]
        else:
            digits = "+" + digits_only
    if not re.fullmatch(r"\+\d{8,15}", digits):
        raise ValueError(f"Invalid phone number: {phone}")
    return digits


def is_stop_message(body: str) -> bool:
    normalized = re.sub(r"[^A-Za-z]", "", body or "").upper()
    return normalized in STOP_WORDS
