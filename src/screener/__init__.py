"""Quantitative Nifty 500 screener — the /stock_earn_money subsystem.

Separate from the LangGraph debate desk. Scores the Nifty 500 with DETERMINISTIC
Python factor math (no LLM in the ranking path), attaches risk-defined entry/
stop/target levels + rupee position sizing, and is validated by a backtest and a
live paper-trade tracker.

Educational research only — no orders are ever placed; a human acts manually.
"""
