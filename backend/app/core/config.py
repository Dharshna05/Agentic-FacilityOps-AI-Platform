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
    PROJECT_NAME: str = "Infosys_Agentic AI for Smart Facility Operations and Optimization"
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

    # --- Auth (Milestone: login/admin protection) ---
    # Secret used to sign JWTs. Falls back to a fixed dev-only value so the
    # app still runs out-of-the-box, but this MUST be overridden in .env for
    # anything beyond local dev — anyone with this default could forge a
    # valid token otherwise.
    JWT_SECRET_KEY: str = os.getenv("JWT_SECRET_KEY", "dev-only-insecure-secret-change-me")
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = int(os.getenv("JWT_EXPIRE_MINUTES", "120"))

    # Seeded on first boot (see main.py's lifespan) if no users exist yet —
    # this is a single-admin demo setup, not a public-registration system.
    # Change ADMIN_PASSWORD in .env before showing this to anyone else.
    ADMIN_USERNAME: str = os.getenv("ADMIN_USERNAME", "admin")
    ADMIN_PASSWORD: str = os.getenv("ADMIN_PASSWORD", "facilityops123")


settings = Settings()
