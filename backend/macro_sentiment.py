"""
Macro & Sentiment — FRED macro signals and Yahoo Finance news sentiment.
"""
import os
import requests
import numpy as np
import pandas as pd
from io import StringIO

# ─── NLTK / VADER setup ───────────────────────────────────────────────────────
os.environ.setdefault("NLTK_DATA", "/tmp/nltk_data")

import nltk
nltk.data.path.insert(0, "/tmp/nltk_data")
try:
    nltk.data.find("sentiment/vader_lexicon.zip")
except LookupError:
    nltk.download("vader_lexicon", download_dir="/tmp/nltk_data", quiet=True)

try:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    _VADER_AVAILABLE = True
except Exception:
    _VADER_AVAILABLE = False

# ─── Keyword fallback ─────────────────────────────────────────────────────────
_POSITIVE_WORDS = {
    "beat", "surge", "rally", "record", "profit", "growth", "gain",
    "strong", "upgrade", "bullish", "outperform", "exceeds", "positive",
}
_NEGATIVE_WORDS = {
    "miss", "fall", "crash", "recession", "loss", "weak", "downgrade",
    "bearish", "underperform", "decline", "risk", "sell", "layoff",
}


def _keyword_sentiment(text: str) -> float:
    words = set(text.lower().split())
    pos = len(words & _POSITIVE_WORDS)
    neg = len(words & _NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 3)


# ─── FRED helper ──────────────────────────────────────────────────────────────
_FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"


def _fred_series(series_id: str, n_obs: int = 30) -> pd.Series:
    url = f"{_FRED_BASE}?id={series_id}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    r.raise_for_status()
    df = pd.read_csv(StringIO(r.text), parse_dates=["DATE"])
    df = df[df.iloc[:, 1] != "."]
    df.iloc[:, 1] = df.iloc[:, 1].astype(float)
    return df.set_index("DATE").iloc[:, 0].dropna().iloc[-n_obs:]


# ─── Macro Signals ────────────────────────────────────────────────────────────

def get_macro_signals() -> dict:
    macro_score = 50
    signals = []

    # Fed Funds Rate
    try:
        ff = _fred_series("FEDFUNDS", 12)
        ff_current = float(ff.iloc[-1])
        ff_prev = float(ff.iloc[-6])
        if ff_current > 5.0:
            macro_score += 10
            signals.append(f"Fed Funds Rate {ff_current:.2f}% — elevated, restricting growth")
        elif ff_current > 3.0:
            macro_score += 5
            signals.append(f"Fed Funds Rate {ff_current:.2f}% — moderately restrictive")
        else:
            macro_score -= 5
            signals.append(f"Fed Funds Rate {ff_current:.2f}% — accommodative policy")
        if ff_current > ff_prev:
            macro_score += 5
            signals.append("Rate trend rising — tightening cycle ongoing")
        else:
            macro_score -= 3
            signals.append("Rate trend easing — policy loosening")
    except Exception as e:
        signals.append(f"Fed Funds data unavailable: {e}")

    # Yield Curve (10Y-2Y)
    try:
        yc = _fred_series("T10Y2Y", 30)
        yc_current = float(yc.iloc[-1])
        if yc_current < 0:
            macro_score += 15
            signals.append(f"Yield curve inverted ({yc_current:+.2f}%) — recession risk elevated")
        elif yc_current < 0.5:
            macro_score += 5
            signals.append(f"Yield curve flat ({yc_current:+.2f}%) — caution advised")
        else:
            macro_score -= 5
            signals.append(f"Yield curve positive ({yc_current:+.2f}%) — normal conditions")
    except Exception as e:
        signals.append(f"Yield curve data unavailable: {e}")

    # VIX
    try:
        url = "https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX?range=5d&interval=1d"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        vix_closes = r.json()["chart"]["result"][0]["indicators"]["quote"][0]["close"]
        vix = float([v for v in vix_closes if v is not None][-1])
        if vix > 30:
            macro_score += 15
            signals.append(f"VIX {vix:.1f} — high fear / volatility spike")
        elif vix > 20:
            macro_score += 5
            signals.append(f"VIX {vix:.1f} — elevated market uncertainty")
        else:
            macro_score -= 5
            signals.append(f"VIX {vix:.1f} — calm market conditions")
    except Exception as e:
        signals.append(f"VIX data unavailable: {e}")

    macro_score = max(0, min(100, macro_score))
    return {"macro_score": int(macro_score), "signals": signals}


# ─── News Sentiment ───────────────────────────────────────────────────────────

def get_news_sentiment(ticker: str) -> dict:
    if _VADER_AVAILABLE:
        sia = SentimentIntensityAnalyzer()
        score_fn = lambda t: sia.polarity_scores(t)["compound"]
    else:
        score_fn = _keyword_sentiment

    headlines = []
    scores = []

    # Primary: Yahoo Finance news API
    url = f"https://query2.finance.yahoo.com/v2/finance/news?tickers={ticker}&count=10"
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        items = r.json().get("items", {}).get("result", [])
        for item in items[:10]:
            title = item.get("title", "")
            if title:
                sc = score_fn(title)
                headlines.append({"title": title, "score": round(sc, 3)})
                scores.append(sc)
    except Exception:
        pass

    # Fallback: Yahoo Finance search API
    if not scores:
        try:
            url2 = f"https://query1.finance.yahoo.com/v1/finance/search?q={ticker}&newsCount=10"
            r2 = requests.get(url2, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            news_items = r2.json().get("news", [])
            for item in news_items[:10]:
                title = item.get("title", "")
                if title:
                    sc = score_fn(title)
                    headlines.append({"title": title, "score": round(sc, 3)})
                    scores.append(sc)
        except Exception:
            pass

    if not scores:
        return {"sentiment_score": 0.0, "sentiment_label": "Neutral", "headlines": []}

    avg_score = float(np.mean(scores))
    label = "Positive" if avg_score > 0.05 else "Negative" if avg_score < -0.05 else "Neutral"
    return {
        "sentiment_score": round(avg_score, 3),
        "sentiment_label": label,
        "headlines": headlines,
    }
