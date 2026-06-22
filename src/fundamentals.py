"""The company-numbers math — fundamentals facts for the AI to read (NO AI here).

This is the fundamentals twin of indicators.py. It pulls the company's real
business figures (valuation like P/E and P/B, profitability like ROE and margins,
growth, debt) from Yahoo's data and tidies them up — so the fundamentals worker
reasons over facts, not guesses.

One India-specific touch: big rupee amounts are shown in *crore* (1 crore =
10,000,000), the unit Indian investors actually read. The small `_num` / `_crore`
/ `_pct` helpers just format numbers safely (returning None when data is missing).
"""

import math


def _num(x, dp=2):
    """Round to float, or None for missing/NaN."""
    if x is None:
        return None
    try:
        f = float(x)
    except (TypeError, ValueError):
        return None
    return None if math.isnan(f) else round(f, dp)


def _crore(x):
    v = _num(x)
    return None if v is None else round(v / 1e7, 0)


def _pct(x, dp=2):
    """yfinance returns some ratios as fractions (0.27 = 27%)."""
    v = _num(x)
    return None if v is None else round(v * 100, dp)


def _yoy_growth(financials, row: str):
    """Year-over-year % growth for a financials row (newest col vs prior)."""
    try:
        if financials is None or financials.empty or row not in financials.index:
            return None
        series = financials.loc[row].dropna()
        if len(series) < 2:
            return None
        latest, prior = float(series.iloc[0]), float(series.iloc[1])
        if prior == 0:
            return None
        return round((latest / prior - 1) * 100, 2)
    except Exception:
        return None


def compute(info: dict, financials=None) -> dict:
    """Return a dict of fundamental metrics."""
    return {
        "name": info.get("longName") or info.get("shortName"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        # Valuation
        "market_cap_cr": _crore(info.get("marketCap")),
        "trailing_pe": _num(info.get("trailingPE")),
        "forward_pe": _num(info.get("forwardPE")),
        "price_to_book": _num(info.get("priceToBook")),
        "peg_ratio": _num(info.get("pegRatio") or info.get("trailingPegRatio")),
        "trailing_eps": _num(info.get("trailingEps")),
        # Profitability
        "roe_pct": _pct(info.get("returnOnEquity")),
        "roa_pct": _pct(info.get("returnOnAssets")),
        "profit_margin_pct": _pct(info.get("profitMargins")),
        "operating_margin_pct": _pct(info.get("operatingMargins")),
        "gross_margin_pct": _pct(info.get("grossMargins")),
        # Growth
        "revenue_growth_pct": _pct(info.get("revenueGrowth")),
        "earnings_growth_pct": _pct(info.get("earningsGrowth")),
        "revenue_yoy_pct": _yoy_growth(financials, "Total Revenue"),
        "net_income_yoy_pct": _yoy_growth(financials, "Net Income"),
        # Balance sheet / leverage
        "debt_to_equity": _num(info.get("debtToEquity")),
        "current_ratio": _num(info.get("currentRatio")),
        "quick_ratio": _num(info.get("quickRatio")),
        "total_cash_cr": _crore(info.get("totalCash")),
        "total_debt_cr": _crore(info.get("totalDebt")),
        # Income
        "total_revenue_cr": _crore(info.get("totalRevenue")),
        # Shareholder return.
        # NOTE: yfinance returns dividendYield already as a percent (e.g. 1.07),
        # unlike margins/ROE which are fractions. So no *100 here.
        "dividend_yield_pct": _num(info.get("dividendYield")),
        "payout_ratio_pct": _pct(info.get("payoutRatio")),
    }


def to_prompt_block(f: dict) -> str:
    def g(k):
        v = f.get(k)
        return "n/a" if v is None else v

    return (
        f"Company: {g('name')} | Sector: {g('sector')} | Industry: {g('industry')}\n"
        f"Valuation: mktcap={g('market_cap_cr')} cr, trailingPE={g('trailing_pe')}, "
        f"forwardPE={g('forward_pe')}, P/B={g('price_to_book')}, PEG={g('peg_ratio')}, "
        f"trailingEPS={g('trailing_eps')}\n"
        f"Profitability: ROE={g('roe_pct')}%, ROA={g('roa_pct')}%, "
        f"netMargin={g('profit_margin_pct')}%, opMargin={g('operating_margin_pct')}%, "
        f"grossMargin={g('gross_margin_pct')}%\n"
        f"Growth: revGrowth={g('revenue_growth_pct')}%, "
        f"earningsGrowth={g('earnings_growth_pct')}%, "
        f"revYoY(financials)={g('revenue_yoy_pct')}%, "
        f"netIncomeYoY(financials)={g('net_income_yoy_pct')}%\n"
        f"Leverage/Liquidity: D/E={g('debt_to_equity')}, "
        f"currentRatio={g('current_ratio')}, quickRatio={g('quick_ratio')}, "
        f"cash={g('total_cash_cr')} cr, debt={g('total_debt_cr')} cr\n"
        f"Income: totalRevenue={g('total_revenue_cr')} cr\n"
        f"Shareholder return: divYield={g('dividend_yield_pct')}%, "
        f"payout={g('payout_ratio_pct')}%"
    )
