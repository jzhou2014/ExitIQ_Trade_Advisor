# ExitIQ Trade Advisor

AI-powered investment exit advisor that tells retail investors whether to **Hold**, **Trim**, or **Sell** — using portfolio data, market signals, macro conditions, and sentiment.

---

## Stack

| Layer    | Technology          |
|----------|---------------------|
| Frontend | Streamlit           |
| Backend  | FastAPI + Uvicorn   |
| Language | Python 3.11+        |

---

## Project Structure

```
├── backend/
│   ├── main.py          # FastAPI app & routes
│   ├── models.py        # Pydantic request/response models
│   ├── advisor.py       # Core scoring & recommendation logic
│   └── requirements.txt
├── frontend/
│   ├── app.py           # Streamlit UI
│   └── requirements.txt
├── .env.example
└── README.md
```

---

## Getting Started

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

API docs available at: http://localhost:8000/docs

### 2. Frontend

```bash
cd frontend
pip install -r requirements.txt
streamlit run app.py
```

UI available at: http://localhost:8501

### 3. Environment (optional)

```bash
cp .env.example .env
# Edit BACKEND_URL if your backend runs on a different host/port
```

---

## How It Works

The advisor scores a position across four dimensions:

| Dimension        | Signals                                              |
|------------------|------------------------------------------------------|
| P&L              | Unrealized gain/loss percentage                      |
| Market Signals   | RSI, P/E ratio, moving averages, analyst rating      |
| Macro Conditions | Interest rates, inflation, market sentiment, recession risk |
| Sentiment        | News, social media, insider activity                 |

Scores are aggregated, adjusted for **risk tolerance**, and mapped to one of three recommendations:

- ✅ **HOLD** — positive overall signal, stay in the position
- ✂️ **TRIM** — mixed signals, reduce exposure
- 🚨 **SELL** — negative signals, consider exiting

---

## API

### `POST /advise`

**Request body:**
```json
{
  "portfolio": {
    "ticker": "AAPL",
    "shares": 10,
    "avg_cost": 150.0,
    "current_price": 175.0,
    "sector": "Technology"
  },
  "market_signals": {
    "rsi": 65,
    "pe_ratio": 28,
    "moving_avg_50": 170,
    "moving_avg_200": 160,
    "analyst_rating": "Buy"
  },
  "macro_conditions": {
    "interest_rate_trend": "Stable",
    "inflation_rate": 3.2,
    "market_sentiment": "Bullish",
    "recession_risk": "Low"
  },
  "sentiment": {
    "news_sentiment": "Positive",
    "social_sentiment": "Neutral",
    "insider_activity": "Buying"
  },
  "risk_tolerance": "Medium"
}
```

**Response:**
```json
{
  "ticker": "AAPL",
  "recommendation": "HOLD",
  "confidence": 0.82,
  "unrealized_pnl": 250.0,
  "unrealized_pnl_pct": 16.67,
  "reasoning": "The overall signal for AAPL is positive...",
  "key_factors": [
    "Solid gain of 16.7% — trimming may lock in profits",
    "RSI 65 — neutral momentum",
    "Golden cross: 50-day MA above 200-day MA (bullish)",
    ...
  ]
}
```
