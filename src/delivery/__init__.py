"""The delivery router — get the verdict to the human, with a backup plan.

`deliver_verdict()` tries Telegram first; if that isn't set up or fails, it
falls back to email. It returns the name of the channel that actually worked
("telegram" or "email"), or raises DeliveryError if every channel failed.

WHY a router: the caller just says "deliver this" and doesn't worry about which
channel is up. (This matters in practice — Telegram is banned in India right now,
so email quietly takes over.)
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
