import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="ExitIQ Trade Advisor",
    page_icon="📈",
    layout="wide",
)

# ── Styles ────────────────────────────────────────────────────────────────────
st.markdown(
    """
    <style>
    .rec-hold  { background:#1a472a; color:#6fcf97; padding:12px 24px;
                 border-radius:8px; font-size:2rem; font-weight:700; display:inline-block; }
    .rec-trim  { background:#4a3800; color:#f2c94c; padding:12px 24px;
                 border-radius:8px; font-size:2rem; font-weight:700; display:inline-block; }
    .rec-sell  { background:#4a1010; color:#eb5757; padding:12px 24px;
                 border-radius:8px; font-size:2rem; font-weight:700; display:inline-block; }
    .factor-item { padding:4px 0; border-bottom:1px solid #2d2d2d; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📈 ExitIQ Trade Advisor")
st.caption("AI-powered exit signals — Hold, Trim, or Sell your positions with confidence.")
st.divider()

# ── Input Form ────────────────────────────────────────────────────────────────
with st.form("advisor_form"):
    st.subheader("🗂 Portfolio Position")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        ticker = st.text_input("Ticker Symbol", value="AAPL", max_chars=10).upper()
    with col2:
        shares = st.number_input("Shares Held", min_value=0.01, value=10.0, step=1.0)
    with col3:
        avg_cost = st.number_input("Avg Cost / Share ($)", min_value=0.01, value=150.0, step=1.0)
    with col4:
        current_price = st.number_input("Current Price ($)", min_value=0.01, value=175.0, step=1.0)

    col5, col6 = st.columns(2)
    with col5:
        sector = st.text_input("Sector (optional)", placeholder="e.g. Technology")
    with col6:
        risk_tolerance = st.selectbox("Risk Tolerance", ["Low", "Medium", "High"], index=1)

    st.divider()
    st.subheader("📊 Market Signals (optional)")
    col7, col8, col9, col10 = st.columns(4)
    with col7:
        rsi = st.number_input("RSI", min_value=0.0, max_value=100.0, value=55.0, step=0.5)
        use_rsi = st.checkbox("Include RSI", value=True)
    with col8:
        pe_ratio = st.number_input("P/E Ratio", min_value=0.0, value=28.0, step=0.5)
        use_pe = st.checkbox("Include P/E", value=True)
    with col9:
        ma50 = st.number_input("50-day MA ($)", min_value=0.0, value=170.0, step=1.0)
        use_ma = st.checkbox("Include MAs", value=True)
    with col10:
        ma200 = st.number_input("200-day MA ($)", min_value=0.0, value=160.0, step=1.0)
        analyst_rating = st.selectbox("Analyst Rating", ["", "Buy", "Hold", "Sell"])

    st.divider()
    st.subheader("🌍 Macro Conditions (optional)")
    col11, col12, col13, col14 = st.columns(4)
    with col11:
        interest_rate_trend = st.selectbox("Interest Rate Trend", ["", "Rising", "Stable", "Falling"])
    with col12:
        inflation_rate = st.number_input("Inflation Rate (%)", min_value=0.0, value=3.2, step=0.1)
        use_inflation = st.checkbox("Include Inflation", value=True)
    with col13:
        market_sentiment = st.selectbox("Market Sentiment", ["", "Bullish", "Neutral", "Bearish"])
    with col14:
        recession_risk = st.selectbox("Recession Risk", ["", "Low", "Medium", "High"])

    st.divider()
    st.subheader("💬 Sentiment (optional)")
    col15, col16, col17 = st.columns(3)
    with col15:
        news_sentiment = st.selectbox("News Sentiment", ["", "Positive", "Neutral", "Negative"])
    with col16:
        social_sentiment = st.selectbox("Social Sentiment", ["", "Positive", "Neutral", "Negative"])
    with col17:
        insider_activity = st.selectbox("Insider Activity", ["", "Buying", "Neutral", "Selling"])

    submitted = st.form_submit_button("🔍 Get Recommendation", use_container_width=True, type="primary")

# ── API Call & Results ────────────────────────────────────────────────────────
if submitted:
    payload = {
        "portfolio": {
            "ticker": ticker,
            "shares": shares,
            "avg_cost": avg_cost,
            "current_price": current_price,
            "sector": sector or None,
        },
        "risk_tolerance": risk_tolerance,
        "market_signals": {
            "rsi": rsi if use_rsi else None,
            "pe_ratio": pe_ratio if use_pe else None,
            "moving_avg_50": ma50 if use_ma else None,
            "moving_avg_200": ma200 if use_ma else None,
            "analyst_rating": analyst_rating or None,
        },
        "macro_conditions": {
            "interest_rate_trend": interest_rate_trend or None,
            "inflation_rate": inflation_rate if use_inflation else None,
            "market_sentiment": market_sentiment or None,
            "recession_risk": recession_risk or None,
        },
        "sentiment": {
            "news_sentiment": news_sentiment or None,
            "social_sentiment": social_sentiment or None,
            "insider_activity": insider_activity or None,
        },
    }

    with st.spinner("Analyzing position..."):
        try:
            response = requests.post(f"{BACKEND_URL}/advise", json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to the backend. Make sure it's running on " + BACKEND_URL)
            st.stop()
        except requests.exceptions.HTTPError as e:
            st.error(f"Backend error: {e.response.text}")
            st.stop()

    st.divider()
    st.subheader(f"📋 Recommendation for **{data['ticker']}**")

    rec = data["recommendation"]
    css_class = {"HOLD": "rec-hold", "TRIM": "rec-trim", "SELL": "rec-sell"}[rec]
    icon = {"HOLD": "✅", "TRIM": "✂️", "SELL": "🚨"}[rec]

    col_rec, col_conf, col_pnl, col_pnl_pct = st.columns(4)

    with col_rec:
        st.markdown(f'<div class="{css_class}">{icon} {rec}</div>', unsafe_allow_html=True)

    with col_conf:
        st.metric("Confidence", f"{data['confidence'] * 100:.0f}%")

    with col_pnl:
        pnl = data["unrealized_pnl"]
        st.metric("Unrealized P&L", f"${pnl:,.2f}", delta=f"${pnl:,.2f}")

    with col_pnl_pct:
        pnl_pct = data["unrealized_pnl_pct"]
        st.metric("P&L %", f"{pnl_pct:.2f}%", delta=f"{pnl_pct:.2f}%")

    st.markdown(f"**Reasoning:** {data['reasoning']}")

    st.subheader("🔑 Key Factors")
    for factor in data["key_factors"]:
        st.markdown(f"- {factor}")
