"""Sends a verdict OUT by email — the reliable fallback channel.

Uses Python's built-in email tools (`smtplib`) — no extra library needed. It
logs into your email account (defaults suit Gmail with an "App Password") and
sends a message that has both a plain-text and an HTML version, so it looks good
in any email app.

This is the channel that "just works" in India right now (Telegram is blocked),
and it's also what the scheduled cron job uses. Like every channel, the message
states that a human approves all trades.
"""

import html
import smtplib
import ssl
from email.message import EmailMessage

from .. import config

_DIRECTION = {"long": "LONG", "short": "SHORT", "avoid": "AVOID"}


def is_configured() -> bool:
    """True if sender, password, and a recipient are all set."""
    return bool(config.EMAIL_ADDRESS and config.EMAIL_APP_PASSWORD and config.EMAIL_TO)


def _stance_summary(dossier: dict) -> list[str]:
    out = []
    for name in sorted(dossier.get("reports", {})):
        rep = dossier["reports"][name]
        out.append(f"{name}: {rep['stance']} ({rep['confidence']})")
    return out


def build_subject(dossier: dict, verdict: dict) -> str:
    direction = _DIRECTION.get(verdict["direction"], verdict["direction"])
    return (
        f"[Research Desk] {dossier.get('ticker')} — {direction} "
        f"(conviction {verdict['conviction']})"
    )


def build_text(dossier: dict, verdict: dict) -> str:
    direction = _DIRECTION.get(verdict["direction"], verdict["direction"])
    lines = [
        f"{dossier.get('ticker')} — research verdict",
        f"Current price: INR {dossier.get('last_price')}",
        "",
        f"Direction:   {direction}",
        f"Conviction:  {verdict['conviction']}",
        "",
        f"Thesis:      {verdict['thesis']}",
        f"Invalidator: {verdict['invalidator']}",
        f"Idea dead at: INR {verdict['dead_price']}",
        f"  ({verdict['dead_price_rationale']})",
        "",
        "Worker stances:",
    ]
    lines += [f"  - {s}" for s in _stance_summary(dossier)]
    lines += ["", "No order placed. Human approves all trades."]
    return "\n".join(lines)


def build_html(dossier: dict, verdict: dict) -> str:
    def e(x):
        return html.escape(str(x))

    direction = _DIRECTION.get(verdict["direction"], e(verdict["direction"]))
    stances = "".join(f"<li>{e(s)}</li>" for s in _stance_summary(dossier))
    return (
        f"<h2>{e(dossier.get('ticker'))} — research verdict</h2>"
        f"<p>Current price: <b>INR {e(dossier.get('last_price'))}</b></p>"
        f"<p style='font-size:1.1em'><b>{direction}</b> "
        f"&nbsp;·&nbsp; conviction <b>{e(verdict['conviction'])}</b></p>"
        f"<p><b>Thesis:</b> {e(verdict['thesis'])}</p>"
        f"<p><b>Invalidator:</b> {e(verdict['invalidator'])}</p>"
        f"<p><b>Idea dead at:</b> INR {e(verdict['dead_price'])}<br>"
        f"<i>{e(verdict['dead_price_rationale'])}</i></p>"
        f"<p><b>Worker stances:</b></p><ul>{stances}</ul>"
        f"<hr><p><i>No order placed. Human approves all trades.</i></p>"
    )


def send_email(subject: str, text_body: str, html_body: str):
    """Send a multipart email via SMTP. Raises if email is not configured."""
    if not is_configured():
        raise RuntimeError(
            "Email not configured. Set EMAIL_ADDRESS, EMAIL_APP_PASSWORD, "
            "and EMAIL_TO in .env."
        )

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.EMAIL_ADDRESS
    msg["To"] = config.EMAIL_TO
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    host, port = config.EMAIL_SMTP_HOST, config.EMAIL_SMTP_PORT
    ctx = ssl.create_default_context()
    if port == 465:
        with smtplib.SMTP_SSL(host, port, context=ctx, timeout=30) as s:
            s.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=30) as s:
            s.starttls(context=ctx)
            s.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
            s.send_message(msg)


def deliver_verdict(dossier: dict, verdict: dict):
    """Format and email one verdict."""
    send_email(
        build_subject(dossier, verdict),
        build_text(dossier, verdict),
        build_html(dossier, verdict),
    )
