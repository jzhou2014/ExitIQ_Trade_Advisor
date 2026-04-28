# ExitIQ Trade Advisor

AI-powered investment exit advisor that tells retail investors whether to **Hold**, **Trim**, or **Sell** — using portfolio data, market signals, macro conditions, and sentiment.

---

## Stack

| Layer    | Technology                                      |
|----------|-------------------------------------------------|
| Frontend | Streamlit (pure UI — no business logic)         |
| Backend  | FastAPI + Uvicorn                               |
| Language | Python 3.11+                                    |

---

## Project Structure

```
├── backend/
│   ├── main.py              # FastAPI app & all routes
│   ├── models.py            # Pydantic request/response models
│   ├── advisor.py           # Manual-input scoring & recommendation logic
│   ├── analysis.py          # Decision Engine: live price fetch, RSI/MACD/SMA, exit scoring
│   ├── macro_sentiment.py   # Macro signals (FRED, VIX) & news sentiment (VADER)
│   └── requirements.txt
├── frontend/
│   ├── app.py               # Streamlit UI — calls backend APIs only
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

## API Endpoints

Interactive docs available at **http://localhost:8000/docs** once the backend is running.

### `POST /analyze` — Decision Engine
Fetches live price history and returns a full exit analysis.

```json
// Request
{
  "ticker": "AAPL",
  "buy_price": 150.0,
  "buy_date": "2024-01-01",
  "shares": 10,
  "risk_tolerance": "Medium",
  "account_type": "Taxable"
}

// Response
{
  "ticker": "AAPL",
  "action": "Hold",
  "confidence": 72,
  "color": "#17b26a",
  "sell_pressure_score": 15,
  "signals": ["Position up 16.7%", "RSI 55 — neutral momentum", ...],
  "metrics": { "current_price": 175.0, "rsi": 55.0, "sma50": 170.0, ... },
  "price_history": [{ "date": "2024-01-02", "price": 185.2 }, ...]
}
```

### `GET /macro` — Macro Signals
Returns live Fed Funds Rate, yield curve, and VIX signals from FRED and Yahoo Finance.

```json
{
  "macro_score": 55,
  "signals": ["Fed Funds Rate 4.33% — moderately restrictive", "VIX 18.2 — calm market conditions", ...]
}
```

### `GET /sentiment/{ticker}` — News Sentiment
Scores the latest Yahoo Finance headlines using VADER sentiment analysis.

```json
{
  "sentiment_score": 0.142,
  "sentiment_label": "Positive",
  "headlines": [{ "title": "Apple beats earnings...", "score": 0.62 }, ...]
}
```

### `POST /advise` — Manual Advisor (legacy)
Accepts manually entered market signals and returns a HOLD / TRIM / SELL recommendation.
