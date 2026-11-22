"""Reusable input validators. Each returns a clean value or raises ValidationError."""
import re

from .errors import ValidationError

PAYMENT_MODES = ("Cash", "UPI", "Card")


def validate_code(value):
    v = str(value).strip().upper()
    if not re.fullmatch(r"[A-Z0-9-]{2,10}", v):
        raise ValidationError("Item code: 2-10 letters/digits/hyphens (e.g. RICE01).")
    return v


def validate_text(value, label="Field", max_len=40):
    v = " ".join(str(value).split())
    if not v:
        raise ValidationError(f"{label} cannot be empty.")
    if len(v) > max_len:
        raise ValidationError(f"{label} is too long (max {max_len} characters).")
    return v


def validate_price(value):
    try:
        p = float(str(value).strip())
    except ValueError:
        raise ValidationError("Price must be a number.") from None
    if not 0 < p <= 1_000_000:
        raise ValidationError("Price must be between 0 and 10,00,000.")
    return round(p, 2)


def validate_int(value, lo, hi, label="Value"):
    try:
        n = int(str(value).strip())
    except ValueError:
        raise ValidationError(f"{label} must be a whole number.") from None
    if not lo <= n <= hi:
        raise ValidationError(f"{label} must be between {lo} and {hi}.")
    return n


def validate_phone(value):
    """Optional field: blank is allowed and returned as ''."""
    v = re.sub(r"[\s-]", "", str(value))
    if not v:
        return ""
    v = re.sub(r"^(\+91|0)", "", v)
    if not re.fullmatch(r"[6-9]\d{9}", v):
        raise ValidationError("Phone must be a 10-digit Indian mobile number.")
    return v


def validate_customer(value):
    v = " ".join(str(value).split())
    if not v:
        return "Walk-in Customer"
    if not re.fullmatch(r"[A-Za-z][A-Za-z .'-]{1,39}", v):
        raise ValidationError("Customer name must be 2-40 letters.")
    return v.title()


def validate_payment(value):
    v = str(value).strip()
    if v.isdigit() and 1 <= int(v) <= len(PAYMENT_MODES):
        return PAYMENT_MODES[int(v) - 1]
    for mode in PAYMENT_MODES:
        if mode.lower() == v.lower():
            return mode
    raise ValidationError("Choose Cash, UPI or Card.")
