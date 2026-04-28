from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Recommendation(str, Enum):
    HOLD = "HOLD"
    TRIM = "TRIM"
    SELL = "SELL"


class PortfolioEntry(BaseModel):
    ticker: str = Field(..., description="Stock ticker symbol, e.g. AAPL")
    shares: float = Field(..., gt=0, description="Number of shares held")
    avg_cost: float = Field(..., gt=0, description="Average cost per share (USD)")
    current_price: float = Field(..., gt=0, description="Current market price per share (USD)")
    sector: Optional[str] = Field(None, description="Sector, e.g. Technology")


class MarketSignals(BaseModel):
    rsi: Optional[float] = Field(None, ge=0, le=100, description="Relative Strength Index (0-100)")
    pe_ratio: Optional[float] = Field(None, description="Price-to-Earnings ratio")
    moving_avg_50: Optional[float] = Field(None, description="50-day moving average price")
    moving_avg_200: Optional[float] = Field(None, description="200-day moving average price")
    analyst_rating: Optional[str] = Field(None, description="Analyst consensus: Buy / Hold / Sell")


class MacroConditions(BaseModel):
    interest_rate_trend: Optional[str] = Field(None, description="Rising / Stable / Falling")
    inflation_rate: Optional[float] = Field(None, description="Current inflation rate (%)")
    market_sentiment: Optional[str] = Field(None, description="Bullish / Neutral / Bearish")
    recession_risk: Optional[str] = Field(None, description="Low / Medium / High")


class SentimentData(BaseModel):
    news_sentiment: Optional[str] = Field(None, description="Positive / Neutral / Negative")
    social_sentiment: Optional[str] = Field(None, description="Positive / Neutral / Negative")
    insider_activity: Optional[str] = Field(None, description="Buying / Neutral / Selling")


class AdvisorRequest(BaseModel):
    portfolio: PortfolioEntry
    market_signals: Optional[MarketSignals] = None
    macro_conditions: Optional[MacroConditions] = None
    sentiment: Optional[SentimentData] = None
    risk_tolerance: Optional[str] = Field("Medium", description="Low / Medium / High")


class AdvisorResponse(BaseModel):
    ticker: str
    recommendation: Recommendation
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score 0-1")
    unrealized_pnl: float
    unrealized_pnl_pct: float
    reasoning: str
    key_factors: list[str]


# ─── Exit Analysis models ──────────────────────────────────────────────────────

class ExitAnalysisRequest(BaseModel):
    ticker: str
    buy_price: float = Field(..., gt=0)
    buy_date: str = Field(..., description="ISO date string YYYY-MM-DD")
    shares: float = Field(..., gt=0)
    risk_tolerance: str = Field("Medium", description="Low / Medium / High")
    account_type: str = Field("Taxable", description="Taxable / Retirement")


class PricePoint(BaseModel):
    date: str
    price: float


class ExitMetrics(BaseModel):
    current_price: float
    buy_price: float
    gain_pct: float
    position_value: float
    unrealized_pnl: float
    hold_days: int
    rsi: float
    macd: float
    macd_signal: float
    macd_histogram: float
    momentum_20d: float
    sma50: float
    sma200: float
    short_term_tax: bool


class ExitAnalysisResponse(BaseModel):
    ticker: str
    action: str
    confidence: int
    color: str
    sell_pressure_score: int
    signals: list[str]
    metrics: ExitMetrics
    price_history: list[PricePoint]


# ─── Macro & Sentiment models ──────────────────────────────────────────────────

class MacroResponse(BaseModel):
    macro_score: int
    signals: list[str]


class HeadlineItem(BaseModel):
    title: str
    score: float


class SentimentResponse(BaseModel):
    sentiment_score: float
    sentiment_label: str
    headlines: list[HeadlineItem]
