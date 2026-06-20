"""Verdict delivery with fallback: try Telegram, then email.

`deliver_verdict` returns the name of the channel that succeeded, or raises
DeliveryError with the per-channel failures if every configured channel fails.
"""

from . import email, telegram


class DeliveryError(RuntimeError):
    """Raised when no delivery channel succeeds."""


def deliver_verdict(dossier: dict, verdict: dict) -> str:
    """Deliver one verdict. Returns the channel used ('telegram' or 'email')."""
    errors: dict[str, str] = {}

    # Primary: Telegram.
    if telegram.is_configured():
        try:
            telegram.deliver_verdict(dossier, verdict)
            return "telegram"
        except Exception as exc:  # noqa: BLE001 - record and fall through
            errors["telegram"] = f"{type(exc).__name__}: {exc}"
    else:
        errors["telegram"] = "not configured"

    # Fallback: email.
    if email.is_configured():
        try:
            email.deliver_verdict(dossier, verdict)
            return "email"
        except Exception as exc:  # noqa: BLE001
            errors["email"] = f"{type(exc).__name__}: {exc}"
    else:
        errors["email"] = "not configured"

    raise DeliveryError(
        "All delivery channels failed: "
        + "; ".join(f"{k}: {v}" for k, v in errors.items())
    )
