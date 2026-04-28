from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from models import AdvisorRequest, AdvisorResponse
from advisor import analyze

app = FastAPI(
    title="ExitIQ Trade Advisor API",
    description="AI-powered investment exit advisor — Hold, Trim, or Sell recommendations.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "ExitIQ Trade Advisor"}


@app.post("/advise", response_model=AdvisorResponse)
def advise(request: AdvisorRequest):
    try:
        return analyze(request)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
