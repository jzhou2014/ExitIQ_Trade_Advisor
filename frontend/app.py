import streamlit as st
import requests
import pandas as pd
import os
from datetime import date

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ExitIQ — AI Exit Advisor",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─── Styles ───────────────────────────────────────────────────────────────────
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

# ─── API helpers ──────────────────────────────────────────────────────────────

def api_post(path: str, payload: dict) -> dict:
    resp = requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def api_get(path: str) -> dict:
    resp = requests.get(f"{BACKEND_URL}{path}", timeout=30)
    resp.raise_for_status()
    return resp.json()


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📈 ExitIQ")
    st.markdown(
        "<p style='color:#909094;margin-top:-10px;margin-bottom:24px;'>"
        "AI-Powered Exit Advisor</p>",
        unsafe_allow_html=True,
    )

    ticker_raw = st.text_input(
        "Ticker Symbol",
        placeholder="AAPL",
        help="Enter stock ticker (AAPL, NVDA, BTC-USD, FXAIX)",
    )
    ticker_input = ticker_raw.upper().strip() if ticker_raw else ""

    buy_price_input = st.number_input(
        "Buy Price ($)", min_value=0.01, step=0.01, value=100.00,
        help="Your average cost per share",
    )

    buy_date_input = st.date_input(
        "Buy Date", max_value=date.today(), value=date(2024, 1, 1),
        help="Date you first purchased this position",
    )

    shares_input = st.number_input(
        "Shares / Units", min_value=0.001, step=0.001, value=10.0, format="%.3f",
        help="Total shares or units owned",
    )

    risk_tolerance_input = st.selectbox(
        "Risk Tolerance", ["Low", "Medium", "High"], index=1,
        help="Low = protect gains, High = ride volatility",
    )

    account_type_input = st.selectbox(
        "Account Type", ["Taxable", "Retirement"],
        help="Affects tax alert logic",
    )

    portfolio_value_input = st.number_input(
        "Portfolio Value ($) — optional", min_value=0.0, step=100.0, value=0.0,
        help="Your total portfolio size for concentration scoring (leave 0 to skip)",
    )

    analyze_clicked = st.button(
        "🔍 Analyze Position", type="primary", use_container_width=True
    )

# ─── Main header ──────────────────────────────────────────────────────────────
st.markdown("# 📈 ExitIQ — AI Exit Advisor")
st.markdown(
    "<p style='color:#909094;'>Make smarter exit decisions with AI-driven "
    "technical, macro, and sentiment analysis.</p>",
    unsafe_allow_html=True,
)

if not analyze_clicked:
    st.info(
        "👈 Fill in your position details in the sidebar and click "
        "**Analyze Position** to get started."
    )
    st.stop()

if not ticker_input:
    st.error("Please enter a ticker symbol in the sidebar.")
    st.stop()

# ─── Call backend ─────────────────────────────────────────────────────────────
with st.spinner("Analyzing position..."):
    try:
        result = api_post("/analyze", {
            "ticker": ticker_input,
            "buy_price": float(buy_price_input),
            "buy_date": buy_date_input.strftime("%Y-%m-%d"),
            "shares": float(shares_input),
            "risk_tolerance": risk_tolerance_input,
            "account_type": account_type_input,
        })
    except requests.exceptions.ConnectionError:
        st.error(f"Cannot connect to the backend at {BACKEND_URL}. Make sure it's running.")
        st.stop()
    except requests.exceptions.HTTPError as e:
        st.error(f"Backend error: {e.response.text}")
        st.stop()

    try:
        macro_result = api_get("/macro")
    except Exception:
        macro_result = {"macro_score": 50, "signals": ["Macro data unavailable"]}

    try:
        sentiment_result = api_get(f"/sentiment/{ticker_input}")
    except Exception:
        sentiment_result = {"sentiment_score": 0.0, "sentiment_label": "Neutral", "headlines": []}

# ─── Unpack result ────────────────────────────────────────────────────────────
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

# ─── Recommendation card ──────────────────────────────────────────────────────
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
      <div class="score-value" style="color:{color};">{sell_score}
        <span style="font-size:1rem;color:#909094;">/ 100</span>
      </div>
    </div>
    <div>
      <div class="score-label">CONFIDENCE</div>
      <div class="score-value">{confidence}
        <span style="font-size:1rem;color:#909094;">/ 100</span>
      </div>
    </div>
    <div>
      <div class="score-label">TICKER</div>
      <div class="score-value">{result['ticker']}</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ─── Metrics row ──────────────────────────────────────────────────────────────
col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Current Price", f"${current_price:,.2f}")
col2.metric("Gain / Loss", f"{gain_pct:+.2f}%", delta=f"{gain_pct:+.2f}%", delta_color="normal")
col3.metric("P&L", f"${unrealized_pnl:,.2f}")
col4.metric("Position Value", f"${position_value:,.2f}")
col5.metric("Hold Days", f"{hold_days} days")

st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

# ─── Alerts ───────────────────────────────────────────────────────────────────
if short_term_tax and gain_pct > 0:
    st.warning(
        "⚠️ **Short-term tax alert:** Selling now triggers ordinary income tax rates. "
        "Consider holding past 1 year to qualify for long-term capital gains treatment."
    )
if gain_pct < 0:
    st.info(
        "📉 **Underwater position:** Your position is currently at a loss. "
        "Review your stop-loss strategy and consider your original investment thesis before acting."
    )
if hold_days < 30:
    st.info(
        "🕐 **Very recent position:** You've held this position for less than 30 days. "
        "Technical signals may not yet reflect a clear trend."
    )

# ─── Tabs ─────────────────────────────────────────────────────────────────────
import plotly.graph_objects as go

tab1, tab2, tab3 = st.tabs(["📊 Analysis", "🔍 Signals", "📈 Historical"])

# ── TAB 1: Analysis ───────────────────────────────────────────────────────────
with tab1:
    rsi_val = m["rsi"]

    # Derive factor scores for the bar chart
    tech_score = 50
    if rsi_val > 70:
        tech_score += 30
    elif rsi_val > 60:
        tech_score += 15
    elif rsi_val < 35:
        tech_score -= 20
    if m["macd"] < m["macd_signal"]:
        tech_score += 15
    elif m["macd"] > m["macd_signal"]:
        tech_score -= 10
    if m["momentum_20d"] < -5:
        tech_score += 15
    elif m["momentum_20d"] > 10:
        tech_score -= 10
    tech_score = max(0, min(100, tech_score))

    profit_score = min(100, max(0, gain_pct + 50))
    sentiment_score_val = min(100, max(0, int((1 - sentiment_result["sentiment_score"]) * 50)))
    macro_score_val = macro_result["macro_score"]
    concentration_score = (
        min(100, int((position_value / portfolio_value_input) * 200))
        if portfolio_value_input > 0
        else 30
    )

    factors = ["Technical Trend", "Profit Size", "Sentiment", "Macro Risk", "Concentration"]
    weight_labels = ["30%", "20%", "20%", "15%", "15%"]
    scores = [tech_score, profit_score, sentiment_score_val, macro_score_val, concentration_score]
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
            "Indicator": [
                "RSI (14)", "MACD", "MACD Signal", "MACD Histogram",
                "Momentum 20d", "SMA 50", "SMA 200", "vs SMA50", "vs SMA200",
            ],
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
            ],
        })
        st.markdown("**Technical Indicators**")
        st.dataframe(tech_df, hide_index=True, use_container_width=True)

# ── TAB 2: Signals ─────────────────────────────────────────────────────────────
with tab2:
    st.markdown("### 📋 Exit Signals")
    _bullish_kw = {
        "up", "positive", "strong", "above", "bullish", "outperform",
        "profit", "uptrend", "intact",
    }
    _bearish_kw = {
        "down", "negative", "weak", "below", "bearish", "underperform",
        "loss", "downtrend", "inverted", "recession", "oversold", "overbought",
    }

    for sig in result["signals"]:
        sig_lower = sig.lower()
        if any(k in sig_lower for k in _bullish_kw):
            emoji = "🟢"
        elif any(k in sig_lower for k in _bearish_kw):
            emoji = "🔴"
        else:
            emoji = "⚪"
        st.markdown(
            f"<div class='signal-bullet'>{emoji} <span style='color:#fbfbff;'>{sig}</span></div>",
            unsafe_allow_html=True,
        )

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    # Macro expander
    macro_score_display = macro_result["macro_score"]
    macro_color = (
        "#f04438" if macro_score_display > 65
        else "#ffd400" if macro_score_display > 40
        else "#17b26a"
    )
    with st.expander(f"🌍 Macro Environment — Score: {macro_score_display}/100", expanded=False):
        st.markdown(
            f"<span style='background:{macro_color};color:#000;padding:4px 12px;"
            f"border-radius:6px;font-weight:700;'>Macro Risk: {macro_score_display}/100</span>",
            unsafe_allow_html=True,
        )
        st.markdown("")
        for ms in macro_result["signals"]:
            st.markdown(f"• {ms}")

    # Sentiment expander
    sent_score = sentiment_result["sentiment_score"]
    sent_label = sentiment_result["sentiment_label"]
    sent_color = (
        "#17b26a" if sent_label == "Positive"
        else "#f04438" if sent_label == "Negative"
        else "#909094"
    )
    with st.expander(f"📰 News Sentiment — {sent_label} ({sent_score:+.3f})", expanded=False):
        st.markdown(
            f"<span style='background:{sent_color};color:#fff;padding:4px 12px;"
            f"border-radius:6px;font-weight:700;'>{sent_label} · Score: {sent_score:+.3f}</span>",
            unsafe_allow_html=True,
        )
        st.markdown("")
        for hl in sentiment_result["headlines"]:
            hl_color = (
                "#17b26a" if hl["score"] > 0.05
                else "#f04438" if hl["score"] < -0.05
                else "#909094"
            )
            st.markdown(
                f"<div style='display:flex;align-items:flex-start;gap:10px;margin-bottom:6px;'>"
                f"<span style='background:{hl_color};color:#fff;padding:2px 8px;border-radius:4px;"
                f"font-size:0.78rem;font-weight:700;white-space:nowrap;'>{hl['score']:+.2f}</span>"
                f"<span style='color:#fbfbff;font-size:0.9rem;'>{hl['title']}</span></div>",
                unsafe_allow_html=True,
            )

# ── TAB 3: Historical ─────────────────────────────────────────────────────────
with tab3:
    price_hist = pd.DataFrame(result["price_history"])
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
        title=dict(
            text=f"{ticker_input} — 1 Year Price History",
            font=dict(color="#fbfbff", size=16),
        ),
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
                ],
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

# ─── Footer ───────────────────────────────────────────────────────────────────
st.markdown("<hr style='border-color:#333;margin-top:32px;'>", unsafe_allow_html=True)
st.markdown(
    "<p class='footer-text'>ExitIQ is for informational purposes only. Not financial advice. "
    "Data sourced from Yahoo Finance and FRED.</p>",
    unsafe_allow_html=True,
)
