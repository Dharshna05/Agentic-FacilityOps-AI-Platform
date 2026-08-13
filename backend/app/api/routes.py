from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from sqlalchemy.orm import Session
import shutil
import tempfile
from pathlib import Path

from app.core.database import get_db
from app.core.config import settings
from app.core.intelligence_engine import summarize_energy_analysis, investigate_energy
from app.services import data_service, forecast_service
from app.agents.energy_agent import EnergyAgent

router = APIRouter(prefix="/energy", tags=["energy"])

DEFAULT_BUILDING = "BLD-HQ-01"
MAX_WINDOW = 40000  # generous ceiling; actual dataset size may be less

# Shared query param: lets the frontend's range selector (24H/7D/30D/All)
# control every analytics-driven endpoint consistently, not just the raw
# chart data. None/omitted = full dataset (equivalent to "All").
LimitQuery = Query(None, ge=1, le=MAX_WINDOW, description="Most-recent-N-readings window; omit for full dataset")


@router.post("/ingest")
def ingest(db: Session = Depends(get_db)):
    """Milestone 1: integrate utility/IoT data. Loads the configured feed
    into the database. Swap the CSV source for a live connector in prod."""
    rows = data_service.ingest_from_csv(db)
    return {
        "status": "ok",
        "rows_ingested": rows,
        "building_id": DEFAULT_BUILDING,
        "source": str(settings.ENERGY_RAW_CSV.name),
    }


@router.post("/ingest/upload")
async def ingest_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a CSV or Excel (.xlsx) file and ingest it directly — e.g. a
    teammate's Kaggle export (date, Power Consumption, Outdoor Temperature,
    Occupancy). Column names are auto-detected; no manual reformatting needed.
    """
    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".csv", ".xlsx", ".xls"):
        raise HTTPException(400, "Only .csv, .xlsx, or .xls files are supported")

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        rows = data_service.ingest_from_csv(db, csv_path=tmp_path)
    except ValueError as e:
        raise HTTPException(400, str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    return {
        "status": "ok",
        "rows_ingested": rows,
        "building_id": DEFAULT_BUILDING,
        "source": file.filename,
    }


@router.get("/consumption")
def consumption(building_id: str = Query(DEFAULT_BUILDING), limit: int = LimitQuery, db: Session = Depends(get_db)):
    agent = EnergyAgent(db, building_id, limit=limit)
    return agent.analyze()["consumption"]


@router.get("/analytics")
def analytics(building_id: str = Query(DEFAULT_BUILDING), limit: int = LimitQuery, db: Session = Depends(get_db)):
    """Full analytics payload: consumption, submeter breakdown, trend, anomalies."""
    agent = EnergyAgent(db, building_id, limit=limit)
    return agent.analyze()


@router.get("/recommendations")
def recommendations(building_id: str = Query(DEFAULT_BUILDING), limit: int = LimitQuery, db: Session = Depends(get_db)):
    agent = EnergyAgent(db, building_id, limit=limit)
    return {"building_id": building_id, "recommendations": agent.recommend()}


@router.get("/dashboard")
def dashboard(building_id: str = Query(DEFAULT_BUILDING), limit: int = LimitQuery, db: Session = Depends(get_db)):
    """
    Single call that powers the energy monitoring dashboard. Accepts the
    same `limit` window as /readings so KPI cards reflect whatever range
    the user has selected (24H/7D/30D/All), not always the full dataset.
    """
    agent = EnergyAgent(db, building_id, limit=limit)
    result = agent.run()
    analysis = result["analysis"]
    return {
        "building_id": building_id,
        "window_rows": len(agent.df),
        "consumption": analysis["consumption"],
        "breakdown": analysis["breakdown"],
        "trend_pct_vs_prev_period": analysis["trend_pct_vs_prev_period"],
        "anomaly_count": len(analysis["anomalies"]),
        "top_anomalies": analysis["anomalies"][:5],
        "top_recommendations": result["recommendations"][:5],
    }


@router.get("/readings")
def readings(
    building_id: str = Query(DEFAULT_BUILDING),
    limit: int = Query(500, le=MAX_WINDOW),
    db: Session = Depends(get_db),
):
    """Raw time-series for charting (most recent `limit` readings)."""
    df = data_service.get_readings_df(db, building_id)
    if df.empty:
        return {"building_id": building_id, "readings": []}
    tail = df.tail(limit)
    return {
        "building_id": building_id,
        "readings": tail.to_dict(orient="records"),
    }


@router.get("/forecast")
def forecast(
    building_id: str = Query(DEFAULT_BUILDING),
    horizon: str = Query("1h", description="One of: 1h, 6h, 24h"),
    db: Session = Depends(get_db),
):
    """
    ML-based multi-horizon consumption forecast (separate trained model per
    horizon — see ml_models/energy/train_forecast_model.py). Distinct from
    the rule-based recommendations — this is the actual predictive ML
    component. Response includes an honest `confidence` block based on the
    model's own held-out test accuracy for that horizon (1h/6h are strong;
    24h is only marginally better than naive — reported, not hidden).
    """
    if horizon not in forecast_service.VALID_HORIZONS:
        raise HTTPException(400, f"horizon must be one of {forecast_service.VALID_HORIZONS}")
    if not forecast_service.is_model_available(horizon):
        raise HTTPException(503, "Forecast model not trained yet. Run "
                             "ml_models/energy/train_forecast_model.py first.")
    df = data_service.get_readings_df(db, building_id)
    if df.empty:
        raise HTTPException(404, f"No data for building {building_id}")
    try:
        return forecast_service.forecast(df, horizon=horizon)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/forecast/scatter")
def forecast_scatter(horizon: str = Query("1h", description="One of: 1h, 6h, 24h")):
    """Actual-vs-predicted points on held-out test data for the winning
    model at this horizon — powers the reliability scatter chart on the
    dashboard (points near the y=x diagonal = trustworthy predictions)."""
    if horizon not in forecast_service.VALID_HORIZONS:
        raise HTTPException(400, f"horizon must be one of {forecast_service.VALID_HORIZONS}")
    try:
        return forecast_service.get_prediction_scatter(horizon)
    except FileNotFoundError as e:
        raise HTTPException(503, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/briefing")
def briefing(building_id: str = Query(DEFAULT_BUILDING), limit: int = LimitQuery, db: Session = Depends(get_db)):
    """
    LLM-generated plain-English briefing synthesizing the Energy Agent's
    analysis + recommendations (Intelligence Engine). Uses MockProvider by
    default (no API key needed); set AI_PROVIDER=groq + GROQ_API_KEY (or
    gemini + GEMINI_API_KEY) in .env for real LLM output. If a real provider
    is configured but its key is missing/invalid, this gracefully falls back
    to MockProvider instead of failing — `provider` in the response reflects
    what actually ran, not just what was configured.
    """
    agent = EnergyAgent(db, building_id, limit=limit)
    result = agent.run()
    text, provider_used = summarize_energy_analysis(result["analysis"], result["recommendations"])
    return {
        "building_id": building_id,
        "provider": provider_used,
        "briefing": text,
    }


@router.get("/investigate")
def investigate(building_id: str = Query(DEFAULT_BUILDING)):
    """
    Genuinely agentic endpoint: the model is given tools (not pre-computed
    data) and decides for itself which analyses to run, in what order, and
    whether to flag findings to another agent. Returns the final narrative
    plus a full trace of every tool call the model chose to make — this is
    the auditable "what did the AI actually decide to do" record.

    With AI_PROVIDER=mock (default), the tool-call sequence is a scripted-
    but-conditional simulation (clearly labeled) so this works with no API
    key. With AI_PROVIDER=groq or gemini + a real key, the model genuinely
    decides. `provider` in the response reflects what actually ran.
    """
    return investigate_energy(building_id)
