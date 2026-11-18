"""Allowed-domain declarations (task format Section 7)."""

from securebench.core.errors import Rejected

MAX_DOMAIN_LENGTH = 253
_LABEL_CHARS = frozenset("abcdefghijklmnopqrstuvwxyz0123456789-")


def check_domain(text: str) -> str:
    """Return the normalized domain (one trailing dot removed), or raise `Rejected`."""
    domain = text[:-1] if text.endswith(".") else text
    if domain != domain.lower():
        raise Rejected(f"domain {text!r} must be lowercase")
    if not domain or len(domain) > MAX_DOMAIN_LENGTH:
        raise Rejected(f"domain {text!r} is empty or longer than {MAX_DOMAIN_LENGTH} characters")
    labels = domain.split(".")
    if len(labels) < 2:
        raise Rejected(f"domain {text!r} must have at least two labels")
    for label in labels:
        if not 1 <= len(label) <= 63 or not set(label) <= _LABEL_CHARS:
            raise Rejected(f"domain {text!r} has an invalid label {label!r}")
        if label.startswith("-") or label.endswith("-"):
            raise Rejected(f"domain {text!r} has a label starting or ending with '-'")
    if labels[-1] == "localhost":
        raise Rejected(f"domain {text!r} names localhost")
    if all(label.isdigit() for label in labels):
        raise Rejected(f"domain {text!r} is an IP address literal")
    return domain
