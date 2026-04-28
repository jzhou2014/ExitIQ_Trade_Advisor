from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from models import (
    AdvisorRequest,
    AdvisorResponse,
    ExitAnalysisRequest,
    ExitAnalysisResponse,
    MacroResponse,
    SentimentResponse,
)
from advisor import analyze
from analysis import run_exit_analysis
from macro_sentiment import get_macro_signals, get_news_sentiment

app = FastAPI(
    title="ExitIQ Trade Advisor API",
    description="AI-powered investment exit advisor — Hold, Trim, or Sell recommendations.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ExitIQ Trade Advisor"}


# ─── Original advisor (manual inputs) ─────────────────────────────────────────

@app.post("/advise", response_model=AdvisorResponse)
def advise(request: AdvisorRequest):
    try:
        return analyze(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Decision Engine (live market data) ───────────────────────────────────────

@app.post("/analyze", response_model=ExitAnalysisResponse)
def analyze_position(request: ExitAnalysisRequest):
    """
    Full exit analysis: fetches live price history, computes RSI / MACD /
    momentum / SMAs, and returns a Hold / Sell 25% / Sell 50% / Full Sell
    recommendation with a sell-pressure score.
    """
    try:
        result = run_exit_analysis(
            ticker=request.ticker,
            buy_price=request.buy_price,
            buy_date=request.buy_date,
            shares=request.shares,
            risk_tolerance=request.risk_tolerance,
            account_type=request.account_type,
        )
        if "error" in result:
            raise HTTPException(status_code=422, detail=result["error"])
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── Macro Signals ─────────────────────────────────────────────────────────────

@app.get("/macro", response_model=MacroResponse)
def macro():
    """
    Returns live macro signals: Fed Funds Rate (FRED), yield curve (FRED),
    and VIX (Yahoo Finance).
    """
    try:
        return get_macro_signals()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─── News Sentiment ────────────────────────────────────────────────────────────

@app.get("/sentiment/{ticker}", response_model=SentimentResponse)
def sentiment(ticker: str):
    """
    Returns VADER / keyword sentiment scored against the latest Yahoo Finance
    news headlines for the given ticker.
    """
    try:
        return get_news_sentiment(ticker.upper())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
