import subprocess, sys

def _install(pkg):
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', pkg, '-q'])

# Install all required packages at runtime
for _pkg in ['nltk', 'yfinance', 'plotly', 'requests', 'numpy', 'pandas', 'scikit-learn']:
    _install(_pkg)

# ─── Write requirements.txt ───────────────────────────────────────────────────
import os as _os
_req = """nltk>=3.8.0
yfinance>=0.2.36
plotly>=5.18.0
pandas>=2.0.0
numpy>=1.24.0
requests>=2.31.0
scikit-learn>=1.3.0
streamlit>=1.32.0
"""
_req_path = _os.path.join(_os.path.dirname(__file__), "requirements.txt")
with open(_req_path, "w") as _f:
    _f.write(_req)

# ─── Standard Imports ─────────────────────────────────────────────────────────
import streamlit as st
import pandas as pd
import numpy as np
import requests
import json
import os
import nltk
from datetime import datetime, date

# ─── NLTK Setup ──────────────────────────────────────────────────────────────
os.environ["NLTK_DATA"] = "/tmp/nltk_data"
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

# ─── Block 1: Decision Engine ─────────────────────────────────────────────────

def _fetch_price_history(ticker: str) -> pd.Series:
    """Return a pd.Series of daily closes for the last 1y."""
    try:
        import yfinance as yf
        hist = yf.Ticker(ticker).history(period="1y")
        if not hist.empty:
            return hist["Close"]
    except Exception:
        pass
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?range=1y&interval=1d&includePrePost=false"
    )
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=15)
    r.raise_for_status()
    data = r.json()
    result = data["chart"]["result"][0]
    timestamps = result["timestamp"]
    closes = result["indicators"]["quote"][0]["close"]
    idx = pd.to_datetime(timestamps, unit="s")
    return pd.Series(closes, index=idx, name="Close").dropna()


def compute_rsi(series: pd.Series, period: int = 14) -> float:
    delta = series.diff()
    gain = delta.clip(lower=0).rolling(period).mean()
    loss = (-delta.clip(upper=0)).rolling(period).mean()
    rs = gain / loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    return round(float(rsi.iloc[-1]), 1)


def compute_macd(series: pd.Series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd_line = ema12 - ema26
    signal_line = macd_line.ewm(span=9, adjust=False).mean()
    histogram = macd_line - signal_line
    return float(macd_line.iloc[-1]), float(signal_line.iloc[-1]), float(histogram.iloc[-1])


def compute_momentum(series: pd.Series, period: int = 20) -> float:
    if len(series) < period + 1:
        return 0.0
    return round(float((series.iloc[-1] / series.iloc[-period - 1] - 1) * 100), 2)


def run_exit_analysis(
    ticker: str,
    buy_price: float,
    buy_date: str,
    shares: float,
    risk_tolerance: str,
    account_type: str,
) -> dict:
    ticker = ticker.upper().strip()
    close = _fetch_price_history(ticker)

    if close is None or len(close) == 0:
        return {"error": f"No data found for ticker '{ticker}'."}

    current_price = float(close.iloc[-1])
    buy_dt = datetime.strptime(buy_date, "%Y-%m-%d")
    hold_days = (datetime.now() - buy_dt).days
    hold_years = hold_days / 365.25
    gain_pct = (current_price - buy_price) / buy_price * 100
    position_value = current_price * shares
    unrealized_pnl = position_value - buy_price * shares
    short_term_tax = (account_type == "Taxable") and (hold_years < 1)

    rsi = compute_rsi(close)
    macd_val, macd_sig, macd_hist = compute_macd(close)
    momentum_20 = compute_momentum(close, 20)
    sma50  = float(close.rolling(50).mean().iloc[-1])
    sma200 = float(close.rolling(200).mean().iloc[-1])

    sell_pressure = 0
    signals = []

    if gain_pct > 50:
        sell_pressure += 25
        signals.append(f"Position up {gain_pct:.1f}% — significant profit, consider taking gains")
    elif gain_pct > 25:
        sell_pressure += 15
        signals.append(f"Position up {gain_pct:.1f}% — healthy gain achieved")
    elif gain_pct > 10:
        sell_pressure += 5
        signals.append(f"Position up {gain_pct:.1f}%")
    elif gain_pct < -10:
        sell_pressure -= 10
        signals.append(f"Position down {abs(gain_pct):.1f}% — review stop-loss strategy")
    else:
        signals.append(f"Position {gain_pct:+.1f}% — near breakeven")

    if rsi > 75:
        sell_pressure += 20
        signals.append(f"RSI {rsi} — severely overbought")
    elif rsi > 65:
        sell_pressure += 12
        signals.append(f"RSI {rsi} — overbought territory")
    elif rsi < 35:
        sell_pressure -= 15
        signals.append(f"RSI {rsi} — oversold, possible bounce")
    else:
        signals.append(f"RSI {rsi} — neutral momentum")

    if macd_hist < 0 and macd_val < macd_sig:
        sell_pressure += 15
        signals.append("MACD histogram negative — bearish momentum divergence")
    elif macd_hist > 0 and macd_val > macd_sig:
        sell_pressure -= 10
        signals.append("MACD histogram positive — bullish momentum")
    else:
        signals.append("MACD signal mixed / neutral")

    if momentum_20 < -5:
        sell_pressure += 10
        signals.append(f"20-day momentum {momentum_20:+.1f}% — negative trend")
    elif momentum_20 > 10:
        sell_pressure -= 5
        signals.append(f"20-day momentum {momentum_20:+.1f}% — strong uptrend")
    else:
        signals.append(f"20-day momentum {momentum_20:+.1f}%")

    if current_price < sma50:
        sell_pressure += 10
        signals.append("Price below 50-day SMA — short-term downtrend")
    if current_price < sma200:
        sell_pressure += 10
        signals.append("Price below 200-day SMA — long-term downtrend")
    if current_price > sma50 > sma200:
        sell_pressure -= 5
        signals.append("Price above both SMAs — uptrend intact")

    if short_term_tax and gain_pct > 10:
        sell_pressure -= 8
        signals.append(f"Short-term hold ({hold_days}d) — selling triggers ordinary income rates")

    sell_pressure += {"Low": 10, "Medium": 0, "High": -10}.get(risk_tolerance, 0)
    if risk_tolerance == "Low":
        signals.append("Low risk tolerance — bias toward protecting gains")
    elif risk_tolerance == "High":
        signals.append("High risk tolerance — comfortable riding volatility")

    sell_pressure = max(0, min(100, sell_pressure))

    if sell_pressure >= 60:
        action, color = "Full Sell", "#f04438"
        confidence = min(95, 50 + sell_pressure // 2)
    elif sell_pressure >= 40:
        action, color = "Sell 50%", "#FFB482"
        confidence = min(90, 45 + sell_pressure // 2)
    elif sell_pressure >= 20:
        action, color = "Sell 25%", "#ffd400"
        confidence = min(85, 40 + sell_pressure // 2)
    else:
        action, color = "Hold", "#17b26a"
        confidence = min(90, 70 - sell_pressure)

    price_hist_df = close.reset_index()
    price_hist_df.columns = ["date", "price"]
    price_hist_df["date"] = pd.to_datetime(price_hist_df["date"]).dt.strftime("%Y-%m-%d")

    return {
        "ticker": ticker,
        "action": action,
        "confidence": int(confidence),
        "color": color,
        "sell_pressure_score": int(sell_pressure),
        "signals": signals,
        "metrics": {
            "current_price": round(current_price, 2),
            "buy_price": round(buy_price, 2),
            "gain_pct": round(gain_pct, 2),
            "position_value": round(position_value, 2),
            "unrealized_pnl": round(unrealized_pnl, 2),
            "hold_days": hold_days,
            "rsi": rsi,
            "macd": round(macd_val, 3),
            "macd_signal": round(macd_sig, 3),
            "macd_histogram": round(macd_hist, 3),
            "momentum_20d": momentum_20,
            "sma50": round(sma50, 2),
            "sma200": round(sma200, 2),
            "short_term_tax": short_term_tax,
        },
        "price_history": price_hist_df,
    }


# ─── Block 2: Macro & Sentiment ───────────────────────────────────────────────

_POSITIVE_WORDS = {"beat", "surge", "rally", "record", "profit", "growth", "gain",
                   "strong", "upgrade", "bullish", "outperform", "exceeds", "positive"}
_NEGATIVE_WORDS = {"miss", "fall", "crash", "recession", "loss", "weak", "downgrade",
                   "bearish", "underperform", "decline", "risk", "sell", "layoff"}

def _keyword_sentiment(text: str) -> float:
    words = set(text.lower().split())
    pos = len(words & _POSITIVE_WORDS)
    neg = len(words & _NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return round((pos - neg) / total, 3)


_FRED_BASE = "https://fred.stlouisfed.org/graph/fredgraph.csv"

def _fred_series(series_id: str, n_obs: int = 30) -> pd.Series:
    url = f"{_FRED_BASE}?id={series_id}"
    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
    r.raise_for_status()
    from io import StringIO
    df = pd.read_csv(StringIO(r.text), parse_dates=["DATE"])
    df = df[df.iloc[:, 1] != "."]
    df.iloc[:, 1] = df.iloc[:, 1].astype(float)
    return df.set_index("DATE").iloc[:, 0].dropna().iloc[-n_obs:]


def get_macro_signals() -> dict:
    macro_score = 50
    signals = []

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


def get_news_sentiment(ticker: str) -> dict:
    if _VADER_AVAILABLE:
        sia = SentimentIntensityAnalyzer()
        score_fn = lambda t: sia.polarity_scores(t)["compound"]
    else:
        score_fn = _keyword_sentiment

    headlines = []
    scores = []

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


# ─── Streamlit App ────────────────────────────────────────────────────────────

st.set_page_config(
    page_title="ExitIQ — AI Exit Advisor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for dark theme matching Zerve design system
st.markdown("""
<style>
  .recommendation-card {
    border-radius: 12px;
    padding: 28px 36px;
    margin-bottom: 24px;
  }
  .action-badge {
    display: inline-block;
    padding: 8px 22px;
    border-radius: 8px;
    font-size: 1.6rem;
    font-weight: 800;
    letter-spacing: 0.5px;
    margin-bottom: 12px;
  }
  .score-label {
    font-size: 0.85rem;
    color: #909094;
    margin-bottom: 2px;
  }
  .score-value {
    font-size: 2rem;
    font-weight: 700;
    color: #fbfbff;
  }
  .divider { border-top: 1px solid #333; margin: 18px 0; }
  .signal-bullet { padding: 5px 0; font-size: 0.95rem; line-height: 1.5; }
  .footer-text { color: #909094; font-size: 0.78rem; text-align: center; margin-top: 20px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 ExitIQ")
    st.markdown("<p style='color:#909094;margin-top:-10px;margin-bottom:24px;'>AI-Powered Exit Advisor</p>", unsafe_allow_html=True)

    ticker_raw = st.text_input(
        "Ticker Symbol",
        placeholder="AAPL",
        help="Enter stock ticker (AAPL, NVDA, BTC-USD, FXAIX)"
    )
    ticker_input = ticker_raw.upper().strip() if ticker_raw else ""

    buy_price_input = st.number_input(
        "Buy Price ($)",
        min_value=0.01,
        step=0.01,
        value=100.00,
        help="Your average cost per share"
    )

    buy_date_input = st.date_input(
        "Buy Date",
        max_value=date.today(),
        value=date(2024, 1, 1),
        help="Date you first purchased this position"
    )

    shares_input = st.number_input(
        "Shares / Units",
        min_value=0.001,
        step=0.001,
        value=10.0,
        format="%.3f",
        help="Total shares or units owned"
    )

    risk_tolerance_input = st.selectbox(
        "Risk Tolerance",
        ["Low", "Medium", "High"],
        index=1,
        help="Low = protect gains, High = ride volatility"
    )

    account_type_input = st.selectbox(
        "Account Type",
        ["Taxable", "Retirement"],
        help="Affects tax alert logic"
    )

    portfolio_value_input = st.number_input(
        "Portfolio Value ($) — optional",
        min_value=0.0,
        step=100.0,
        value=0.0,
        help="Your total portfolio size for concentration scoring (leave 0 to skip)"
    )

    analyze_clicked = st.button("🔍 Analyze Position", type="primary", use_container_width=True)

# ── Main Area ─────────────────────────────────────────────────────────────────
st.markdown("# 📈 ExitIQ — AI Exit Advisor")
st.markdown("<p style='color:#909094;'>Make smarter exit decisions with AI-driven technical, macro, and sentiment analysis.</p>", unsafe_allow_html=True)

if not analyze_clicked:
    st.info("👈 Fill in your position details in the sidebar and click **Analyze Position** to get started.")
    st.stop()

if not ticker_input:
    st.error("Please enter a ticker symbol in the sidebar.")
    st.stop()

# ── Run Analysis ──────────────────────────────────────────────────────────────
with st.spinner("Analyzing position..."):
    result = run_exit_analysis(
        ticker=ticker_input,
        buy_price=float(buy_price_input),
        buy_date=buy_date_input.strftime("%Y-%m-%d"),
        shares=float(shares_input),
        risk_tolerance=risk_tolerance_input,
        account_type=account_type_input,
    )

    if "error" in result:
        st.error(f"❌ {result['error']} — please check the ticker and try again.")
        st.stop()

    macro_result = get_macro_signals()
    sentiment_result = get_news_sentiment(ticker_input)

m = result["metrics"]
action = result["action"]
color = result["color"]
sell_score = result["sell_pressure_score"]
confidence = result["confidence"]
gain_pct = m["gain_pct"]
hold_days = m["hold_days"]
short_term_tax = m["short_term_tax"]
current_price = m["current_price"]
position_value = m["position_value"]
unrealized_pnl = m["unrealized_pnl"]

# ── Recommendation Card ───────────────────────────────────────────────────────
tint_map = {
    "#17b26a": "rgba(23,178,106,0.10)",
    "#ffd400": "rgba(255,212,0,0.10)",
    "#FFB482": "rgba(255,180,130,0.10)",
    "#f04438": "rgba(240,68,56,0.10)",
}
bg_tint = tint_map.get(color, "rgba(255,255,255,0.05)")
text_color = "#000" if color == "#ffd400" else "#fff"

st.markdown(f"""
<div class="recommendation-card" style="background:{bg_tint}; border: 1.5px solid {color};">
  <div style="display:flex; align-items:flex-start; gap:40px; flex-wrap:wrap;">
    <div>
      <div class="score-label">RECOMMENDATION</div>
      <div class="action-badge" style="background:{color}; color:{text_color};">{action}</div>
    </div>
    <div>
      <div class="score-label">SELL PRESSURE SCORE</div>
      <div class="score-value" style="color:{color};">{sell_score} <span style="font-size:1rem;color:#909094;">/ 100</span></div>
    </div>
    <div>
      <div class="score-label">CONFIDENCE</div>
      <div class="score-value">{confidence} <span style="font-size:1rem;color:#909094;">/ 100</span></div>
    </div>
    <div>
      <div class="score-label">TICKER</div>
      <div class="score-value">{result['ticker']}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── Metrics Row ───────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Current Price", f"${current_price:,.2f}")
col2.metric(
    "Gain / Loss",
    f"{gain_pct:+.2f}%",
    delta=f"{gain_pct:+.2f}%",
    delta_color="normal"
)
col3.metric("P&L", f"${unrealized_pnl:,.2f}")
col4.metric("Position Value", f"${position_value:,.2f}")
col5.metric("Hold Days", f"{hold_days} days")

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# ── Alerts ────────────────────────────────────────────────────────────────────
if short_term_tax and gain_pct > 0:
    st.warning("⚠️ **Short-term tax alert:** Selling now triggers ordinary income tax rates. Consider holding past 1 year to qualify for long-term capital gains treatment.")

if gain_pct < 0:
    st.info("📉 **Underwater position:** Your position is currently at a loss. Review your stop-loss strategy and consider your original investment thesis before acting.")

if hold_days < 30:
    st.info("🕐 **Very recent position:** You've held this position for less than 30 days. Technical signals may not yet reflect a clear trend.")

# ── Three Tabs ────────────────────────────────────────────────────────────────
import plotly.graph_objects as go

tab1, tab2, tab3 = st.tabs(["📊 Analysis", "🔍 Signals", "📈 Historical"])

# ── TAB 1: Analysis ───────────────────────────────────────────────────────────
with tab1:
    # Derive factor scores
    rsi_val = m["rsi"]
    tech_score = 50
    if rsi_val > 70: tech_score += 30
    elif rsi_val > 60: tech_score += 15
    elif rsi_val < 35: tech_score -= 20
    if m["macd"] < m["macd_signal"]: tech_score += 15
    elif m["macd"] > m["macd_signal"]: tech_score -= 10
    if m["momentum_20d"] < -5: tech_score += 15
    elif m["momentum_20d"] > 10: tech_score -= 10
    tech_score = max(0, min(100, tech_score))

    profit_score = min(100, max(0, gain_pct + 50))
    sentiment_score_val = min(100, max(0, int((1 - sentiment_result["sentiment_score"]) * 50)))
    macro_score_val = macro_result["macro_score"]
    concentration_score = 0
    if portfolio_value_input > 0:
        concentration_pct = (position_value / portfolio_value_input) * 100
        concentration_score = min(100, int(concentration_pct * 2))
    else:
        concentration_score = 30  # neutral if not provided

    factors = ["Technical Trend", "Profit Size", "Sentiment", "Macro Risk", "Concentration"]
    weights = [0.30, 0.20, 0.20, 0.15, 0.15]
    scores = [tech_score, profit_score, sentiment_score_val, macro_score_val, concentration_score]
    weight_labels = ["30%", "20%", "20%", "15%", "15%"]
    colors_bar = ["#A1C9F4", "#8DE5A1", "#D0BBFF", "#FFB482", "#FF9F9B"]

    fig_factors = go.Figure(go.Bar(
        x=scores,
        y=[f"{f} ({w})" for f, w in zip(factors, weight_labels)],
        orientation="h",
        marker_color=colors_bar,
        text=[f"{s:.0f}" for s in scores],
        textposition="outside",
        textfont=dict(color="#fbfbff", size=12),
    ))
    fig_factors.update_layout(
        title=dict(text="5-Factor Sell Pressure Scoring", font=dict(color="#fbfbff", size=16)),
        paper_bgcolor="#1D1D20",
        plot_bgcolor="#1D1D20",
        font=dict(color="#fbfbff"),
        xaxis=dict(range=[0, 120], showgrid=False, zeroline=False, tickfont=dict(color="#909094")),
        yaxis=dict(showgrid=False, tickfont=dict(color="#fbfbff", size=12)),
        margin=dict(l=10, r=40, t=50, b=20),
        height=320,
    )
    st.plotly_chart(fig_factors, use_container_width=True)

    col_gauge, col_table = st.columns([1, 1])

    with col_gauge:
        fig_rsi = go.Figure(go.Indicator(
            mode="gauge+number",
            value=rsi_val,
            title=dict(text="RSI (14)", font=dict(color="#fbfbff", size=14)),
            number=dict(font=dict(color="#fbfbff", size=32)),
            gauge=dict(
                axis=dict(range=[0, 100], tickcolor="#909094", tickfont=dict(color="#909094")),
                bar=dict(color="#A1C9F4"),
                bgcolor="#2a2a2e",
                borderwidth=0,
                steps=[
                    dict(range=[0, 30], color="#f04438"),
                    dict(range=[30, 70], color="#17b26a"),
                    dict(range=[70, 100], color="#f04438"),
                ],
                threshold=dict(
                    line=dict(color="#ffd400", width=3),
                    thickness=0.75,
                    value=rsi_val,
                ),
            ),
        ))
        fig_rsi.update_layout(
            paper_bgcolor="#1D1D20",
            font=dict(color="#fbfbff"),
            height=280,
            margin=dict(l=20, r=20, t=50, b=20),
        )
        st.plotly_chart(fig_rsi, use_container_width=True)

    with col_table:
        price_vs_sma50 = ((current_price / m["sma50"]) - 1) * 100
        price_vs_sma200 = ((current_price / m["sma200"]) - 1) * 100
        tech_df = pd.DataFrame({
            "Indicator": ["RSI (14)", "MACD", "MACD Signal", "MACD Histogram",
                          "Momentum 20d", "SMA 50", "SMA 200", "vs SMA50", "vs SMA200"],
            "Value": [
                f"{m['rsi']}",
                f"{m['macd']:.3f}",
                f"{m['macd_signal']:.3f}",
                f"{m['macd_histogram']:.3f}",
                f"{m['momentum_20d']:+.2f}%",
                f"${m['sma50']:,.2f}",
                f"${m['sma200']:,.2f}",
                f"{price_vs_sma50:+.2f}%",
                f"{price_vs_sma200:+.2f}%",
            ]
        })
        st.markdown("**Technical Indicators**")
        st.dataframe(tech_df, hide_index=True, use_container_width=True)

# ── TAB 2: Signals ─────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### 📋 Exit Signals")
    _bullish_kw = {"up", "positive", "strong", "above", "bullish", "outperform", "profit", "uptrend", "intact"}
    _bearish_kw = {"down", "negative", "weak", "below", "bearish", "underperform", "loss", "downtrend", "inverted", "recession", "oversold", "overbought"}

    for sig in result["signals"]:
        sig_lower = sig.lower()
        if any(k in sig_lower for k in _bullish_kw):
            bullet_color = "#17b26a"
            emoji = "🟢"
        elif any(k in sig_lower for k in _bearish_kw):
            bullet_color = "#f04438"
            emoji = "🔴"
        else:
            bullet_color = "#909094"
            emoji = "⚪"
        st.markdown(
            f"<div class='signal-bullet'>{emoji} <span style='color:#fbfbff;'>{sig}</span></div>",
            unsafe_allow_html=True
        )

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    macro_score_display = macro_result["macro_score"]
    macro_color = "#f04438" if macro_score_display > 65 else "#ffd400" if macro_score_display > 40 else "#17b26a"
    with st.expander(f"🌍 Macro Environment — Score: {macro_score_display}/100", expanded=False):
        st.markdown(
            f"<span style='background:{macro_color};color:#000;padding:4px 12px;border-radius:6px;font-weight:700;'>"
            f"Macro Risk: {macro_score_display}/100</span>",
            unsafe_allow_html=True
        )
        st.markdown("")
        for ms in macro_result["signals"]:
            st.markdown(f"• {ms}")

    sent_score = sentiment_result["sentiment_score"]
    sent_label = sentiment_result["sentiment_label"]
    sent_color = "#17b26a" if sent_label == "Positive" else "#f04438" if sent_label == "Negative" else "#909094"
    with st.expander(f"📰 News Sentiment — {sent_label} ({sent_score:+.3f})", expanded=False):
        st.markdown(
            f"<span style='background:{sent_color};color:#fff;padding:4px 12px;border-radius:6px;font-weight:700;'>"
            f"{sent_label} · Score: {sent_score:+.3f}</span>",
            unsafe_allow_html=True
        )
        st.markdown("")
        for hl in sentiment_result["headlines"]:
            hl_color = "#17b26a" if hl["score"] > 0.05 else "#f04438" if hl["score"] < -0.05 else "#909094"
            st.markdown(
                f"<div style='display:flex;align-items:flex-start;gap:10px;margin-bottom:6px;'>"
                f"<span style='background:{hl_color};color:#fff;padding:2px 8px;border-radius:4px;"
                f"font-size:0.78rem;font-weight:700;white-space:nowrap;'>{hl['score']:+.2f}</span>"
                f"<span style='color:#fbfbff;font-size:0.9rem;'>{hl['title']}</span></div>",
                unsafe_allow_html=True
            )

# ── TAB 3: Historical ─────────────────────────────────────────────────────────
with tab3:
    price_hist = result["price_history"].copy()
    price_hist["date"] = pd.to_datetime(price_hist["date"])
    prices = price_hist["price"]
    price_hist["sma50"] = prices.rolling(50).mean()
    price_hist["sma200"] = prices.rolling(200).mean()

    fig_hist = go.Figure()

    fig_hist.add_trace(go.Scatter(
        x=price_hist["date"], y=price_hist["price"],
        mode="lines", name="Price",
        line=dict(color="#A1C9F4", width=2),
    ))
    fig_hist.add_trace(go.Scatter(
        x=price_hist["date"], y=price_hist["sma50"],
        mode="lines", name="SMA-50",
        line=dict(color="#FFB482", width=1.5, dash="dot"),
    ))
    fig_hist.add_trace(go.Scatter(
        x=price_hist["date"], y=price_hist["sma200"],
        mode="lines", name="SMA-200",
        line=dict(color="#D0BBFF", width=1.5, dash="dash"),
    ))
    fig_hist.add_hline(
        y=float(buy_price_input),
        line_dash="dash",
        line_color="#ffd400",
        annotation_text=f"Buy Price ${float(buy_price_input):,.2f}",
        annotation_font_color="#ffd400",
        annotation_position="top left",
    )

    fig_hist.update_layout(
        title=dict(text=f"{ticker_input} — 1 Year Price History", font=dict(color="#fbfbff", size=16)),
        paper_bgcolor="#1D1D20",
        plot_bgcolor="#1D1D20",
        font=dict(color="#fbfbff"),
        height=500,
        legend=dict(
            font=dict(color="#fbfbff"),
            bgcolor="rgba(29,29,32,0.8)",
            bordercolor="#333",
            borderwidth=1,
        ),
        xaxis=dict(
            showgrid=False,
            tickfont=dict(color="#909094"),
            rangeselector=dict(
                bgcolor="#2a2a2e",
                activecolor="#A1C9F4",
                font=dict(color="#fbfbff"),
                buttons=[
                    dict(count=1, label="1M", step="month", stepmode="backward"),
                    dict(count=3, label="3M", step="month", stepmode="backward"),
                    dict(count=6, label="6M", step="month", stepmode="backward"),
                    dict(count=1, label="1Y", step="year", stepmode="backward"),
                ]
            ),
            type="date",
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="#2a2a2e",
            tickfont=dict(color="#909094"),
            tickprefix="$",
        ),
        margin=dict(l=10, r=10, t=60, b=20),
    )
    st.plotly_chart(fig_hist, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown("<hr style='border-color:#333;margin-top:32px;'>", unsafe_allow_html=True)
st.markdown(
    "<p class='footer-text'>ExitIQ is for informational purposes only. Not financial advice. "
    "Data sourced from Yahoo Finance and FRED.</p>",
    unsafe_allow_html=True
)