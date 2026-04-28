from models import (
    AdvisorRequest,
    AdvisorResponse,
    Recommendation,
    MarketSignals,
    MacroConditions,
    SentimentData,
)


def _score_pnl(pnl_pct: float) -> tuple[float, str]:
    """Score based on unrealized P&L percentage."""
    if pnl_pct >= 50:
        return -2.0, f"Large gain of {pnl_pct:.1f}% — consider taking profits"
    elif pnl_pct >= 20:
        return -1.0, f"Solid gain of {pnl_pct:.1f}% — trimming may lock in profits"
    elif pnl_pct >= 0:
        return 0.5, f"Modest gain of {pnl_pct:.1f}% — position is healthy"
    elif pnl_pct >= -10:
        return 0.0, f"Small loss of {pnl_pct:.1f}% — within normal volatility"
    else:
        return -1.5, f"Significant loss of {pnl_pct:.1f}% — review thesis"


def _score_market_signals(signals: MarketSignals | None) -> tuple[float, list[str]]:
    if signals is None:
        return 0.0, []

    score = 0.0
    factors = []

    if signals.rsi is not None:
        if signals.rsi > 70:
            score -= 1.5
            factors.append(f"RSI {signals.rsi:.0f} — overbought territory")
        elif signals.rsi < 30:
            score += 1.5
            factors.append(f"RSI {signals.rsi:.0f} — oversold, potential bounce")
        else:
            score += 0.5
            factors.append(f"RSI {signals.rsi:.0f} — neutral momentum")

    if signals.moving_avg_50 and signals.moving_avg_200:
        if signals.moving_avg_50 > signals.moving_avg_200:
            score += 1.0
            factors.append("Golden cross: 50-day MA above 200-day MA (bullish)")
        else:
            score -= 1.0
            factors.append("Death cross: 50-day MA below 200-day MA (bearish)")

    if signals.analyst_rating:
        rating_map = {"Buy": 1.0, "Hold": 0.0, "Sell": -1.5}
        score += rating_map.get(signals.analyst_rating, 0.0)
        factors.append(f"Analyst consensus: {signals.analyst_rating}")

    if signals.pe_ratio is not None:
        if signals.pe_ratio > 40:
            score -= 1.0
            factors.append(f"P/E ratio {signals.pe_ratio:.1f} — elevated valuation")
        elif signals.pe_ratio < 15:
            score += 0.5
            factors.append(f"P/E ratio {signals.pe_ratio:.1f} — attractive valuation")

    return score, factors


def _score_macro(macro: MacroConditions | None) -> tuple[float, list[str]]:
    if macro is None:
        return 0.0, []

    score = 0.0
    factors = []

    trend_map = {"Rising": -1.0, "Stable": 0.5, "Falling": 1.0}
    if macro.interest_rate_trend:
        score += trend_map.get(macro.interest_rate_trend, 0.0)
        factors.append(f"Interest rates: {macro.interest_rate_trend}")

    sentiment_map = {"Bullish": 1.0, "Neutral": 0.0, "Bearish": -1.5}
    if macro.market_sentiment:
        score += sentiment_map.get(macro.market_sentiment, 0.0)
        factors.append(f"Market sentiment: {macro.market_sentiment}")

    recession_map = {"Low": 0.5, "Medium": -0.5, "High": -2.0}
    if macro.recession_risk:
        score += recession_map.get(macro.recession_risk, 0.0)
        factors.append(f"Recession risk: {macro.recession_risk}")

    if macro.inflation_rate is not None:
        if macro.inflation_rate > 5:
            score -= 1.0
            factors.append(f"High inflation at {macro.inflation_rate:.1f}%")
        elif macro.inflation_rate < 2.5:
            score += 0.5
            factors.append(f"Inflation under control at {macro.inflation_rate:.1f}%")

    return score, factors


def _score_sentiment(sentiment: SentimentData | None) -> tuple[float, list[str]]:
    if sentiment is None:
        return 0.0, []

    score = 0.0
    factors = []

    sent_map = {"Positive": 1.0, "Neutral": 0.0, "Negative": -1.0}

    if sentiment.news_sentiment:
        score += sent_map.get(sentiment.news_sentiment, 0.0)
        factors.append(f"News sentiment: {sentiment.news_sentiment}")

    if sentiment.social_sentiment:
        score += sent_map.get(sentiment.social_sentiment, 0.0) * 0.5
        factors.append(f"Social sentiment: {sentiment.social_sentiment}")

    insider_map = {"Buying": 1.5, "Neutral": 0.0, "Selling": -1.5}
    if sentiment.insider_activity:
        score += insider_map.get(sentiment.insider_activity, 0.0)
        factors.append(f"Insider activity: {sentiment.insider_activity}")

    return score, factors


def _apply_risk_tolerance(score: float, risk_tolerance: str) -> float:
    multiplier = {"Low": 1.3, "Medium": 1.0, "High": 0.7}
    return score * multiplier.get(risk_tolerance, 1.0)


def _score_to_recommendation(score: float) -> tuple[Recommendation, float]:
    """Convert numeric score to recommendation and confidence."""
    if score >= 2.0:
        rec = Recommendation.HOLD
        confidence = min(0.95, 0.6 + (score - 2.0) * 0.05)
    elif score >= 0.0:
        rec = Recommendation.TRIM
        confidence = min(0.85, 0.5 + abs(score) * 0.05)
    else:
        rec = Recommendation.SELL
        confidence = min(0.95, 0.5 + abs(score) * 0.05)

    return rec, round(confidence, 2)


def analyze(request: AdvisorRequest) -> AdvisorResponse:
    portfolio = request.portfolio

    # Calculate P&L
    unrealized_pnl = (portfolio.current_price - portfolio.avg_cost) * portfolio.shares
    unrealized_pnl_pct = (
        (portfolio.current_price - portfolio.avg_cost) / portfolio.avg_cost
    ) * 100

    all_factors: list[str] = []

    # Score each dimension
    pnl_score, pnl_factor = _score_pnl(unrealized_pnl_pct)
    all_factors.append(pnl_factor)

    market_score, market_factors = _score_market_signals(request.market_signals)
    all_factors.extend(market_factors)

    macro_score, macro_factors = _score_macro(request.macro_conditions)
    all_factors.extend(macro_factors)

    sentiment_score, sentiment_factors = _score_sentiment(request.sentiment)
    all_factors.extend(sentiment_factors)

    total_score = pnl_score + market_score + macro_score + sentiment_score
    total_score = _apply_risk_tolerance(total_score, request.risk_tolerance or "Medium")

    recommendation, confidence = _score_to_recommendation(total_score)

    reasoning_map = {
        Recommendation.HOLD: (
            f"The overall signal for {portfolio.ticker} is positive. "
            "Fundamentals and market conditions support continuing to hold this position."
        ),
        Recommendation.TRIM: (
            f"Mixed signals for {portfolio.ticker} suggest reducing exposure. "
            "Consider trimming 25–50% of the position to lock in gains or limit downside."
        ),
        Recommendation.SELL: (
            f"Multiple negative signals for {portfolio.ticker} indicate elevated risk. "
            "Exiting the position may be prudent given current conditions."
        ),
    }

    return AdvisorResponse(
        ticker=portfolio.ticker,
        recommendation=recommendation,
        confidence=confidence,
        unrealized_pnl=round(unrealized_pnl, 2),
        unrealized_pnl_pct=round(unrealized_pnl_pct, 2),
        reasoning=reasoning_map[recommendation],
        key_factors=all_factors,
    )
