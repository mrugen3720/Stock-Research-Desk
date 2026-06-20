"""Render the dossier and debate transcript into prompt-friendly text."""


def dossier_to_text(dossier: dict) -> str:
    """Format the bundled worker reports (and price) for a debater/judge prompt."""
    lines = [
        f"TICKER: {dossier.get('ticker')}",
    ]
    price = dossier.get("last_price")
    if price is not None:
        lines.append(f"CURRENT PRICE: INR {price}")
    lines.append("")

    for name in sorted(dossier.get("reports", {})):
        rep = dossier["reports"][name]
        lines.append(
            f"### {name.upper()} "
            f"(stance={rep['stance']}, confidence={rep['confidence']})"
        )
        for f in rep["findings"]:
            lines.append(f"  - {f}")
        if rep.get("sources"):
            lines.append(f"  sources: {', '.join(rep['sources'])}")
        lines.append("")
    return "\n".join(lines).strip()


def transcript_to_text(transcript: list[dict]) -> str:
    """Format the running debate so far."""
    if not transcript:
        return "(no arguments yet)"
    return "\n\n".join(
        f"Round {t['round']} — {t['side'].upper()}:\n{t['text']}" for t in transcript
    )
