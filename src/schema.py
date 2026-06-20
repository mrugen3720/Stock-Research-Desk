"""The strict JSON contract every worker returns.

This is the single source of truth for the worker output shape. The supervisor,
debaters, and judge all rely on every worker speaking exactly this language:
findings, stance, confidence, sources.
"""

from typing import List, Literal

from pydantic import BaseModel, Field


class WorkerReport(BaseModel):
    """Identical shape across the technicals, fundamentals, and news workers."""

    findings: List[str] = Field(
        ...,
        description=(
            "3-6 concise, evidence-based observations. Each should cite a "
            "specific number or fact from the provided data, not a vague claim."
        ),
    )
    stance: Literal["bullish", "bearish", "neutral"] = Field(
        ..., description="Overall directional read implied by the findings."
    )
    confidence: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description=(
            "How strongly the evidence agrees, 0-1. Conflicting signals should "
            "pull this toward the middle; align with 'neutral' when torn."
        ),
    )
    sources: List[str] = Field(
        ...,
        description="What the findings are based on (data feeds, windows, indicators).",
    )


class Verdict(BaseModel):
    """The Judge's final call after reading the Bull/Bear debate.

    No order is ever placed from this — it is a recommendation for a human.
    """

    direction: Literal["long", "short", "avoid"] = Field(
        ...,
        description=(
            "long = bullish idea worth a position, short = bearish idea, "
            "avoid = no edge / stay out."
        ),
    )
    conviction: float = Field(
        ..., ge=0.0, le=1.0, description="How strong the call is, 0-1."
    )
    thesis: str = Field(
        ..., description="One sentence stating the call and its core reason."
    )
    invalidator: str = Field(
        ...,
        description="The single most important thing that would prove the thesis wrong.",
    )
    dead_price: float = Field(
        ...,
        description=(
            "The price level (in INR) at which the idea is dead and the position "
            "should be abandoned."
        ),
    )
    dead_price_rationale: str = Field(
        ..., description="Why that specific level kills the thesis."
    )
