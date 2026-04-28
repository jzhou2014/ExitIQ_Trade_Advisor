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
