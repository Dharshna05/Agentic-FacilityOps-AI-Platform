"""
Central application configuration.
Reads from environment variables (.env) with sane local defaults so the
service runs out-of-the-box during development.
"""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/

# CRITICAL: without this, backend/.env is never actually read — os.getenv()
# only sees variables set in the shell's own environment, so AI_PROVIDER=groq
# and GROQ_API_KEY in .env would silently have no effect and everything
# would keep falling back to "mock". load_dotenv() must run before Settings
# reads any os.getenv() calls below.
load_dotenv(BASE_DIR / ".env")

class Settings:
    PROJECT_NAME: str = "Agentic FacilityOps AI Platform"
    API_V1_PREFIX: str = "/api"

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", f"sqlite:///{BASE_DIR / 'data' / 'facilityops.db'}"
    )

    # Data ingestion source (Milestone 1: utility/IoT data integration).
    # Points at the processed CSV that stands in for a real utility/IoT feed.
    ENERGY_RAW_CSV: Path = BASE_DIR / "data" / "raw" / "energy_readings_raw.csv"

    # Analytics tuning
    ANOMALY_ZSCORE_THRESHOLD: float = 2.5   # hourly reading flagged if |z| exceeds this
    OFF_HOURS_START: int = 20               # 8 PM
    OFF_HOURS_END: int = 6                  # 6 AM
    BASELINE_WASTE_THRESHOLD_PCT: float = 15.0  # off-hours load vs daytime avg

    CORS_ORIGINS: list = ["http://localhost:5173", "http://localhost:3000"]

    # LLM provider for the Intelligence Engine's briefing/investigation.
    # "mock" (default) works with no API key. "groq" (recommended real
    # provider — fast, generous free tier) needs GROQ_API_KEY. "gemini" is
    # also supported and needs GEMINI_API_KEY.
    AI_PROVIDER: str = os.getenv("AI_PROVIDER", "mock")


settings = Settings()
