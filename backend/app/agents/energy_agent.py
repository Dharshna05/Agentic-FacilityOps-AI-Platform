"""
Energy Agent (Milestone 1).

Responsible for everything energy-domain: reading ingested data, running
analytics, detecting anomalies, and turning findings into concrete,
prioritized efficiency recommendations. This mirrors the pattern the other
domain agents (maintenance, occupancy, security, cost) will follow, so this
file is a template for how future agents should be structured:

  1. __init__ pulls in the data it needs for a building
  2. analyze() runs the domain-specific analytics
  3. recommend() turns analysis into ranked, actionable output
  4. run() is the single entrypoint the API/other agents call
"""
from sqlalchemy.orm import Session

from app.services.data_service import get_readings_df
from app.utils.energy_analytics import (
    consumption_summary,
    submeter_breakdown,
    trend_pct,
    detect_anomalies,
    off_hours_baseline_waste,
    temperature_correlation,
    occupancy_correlation,
)


class EnergyAgent:
    def __init__(self, db: Session, building_id: str, limit: int | None = None):
        self.db = db
        self.building_id = building_id
        df = get_readings_df(db, building_id)
        # If a window is requested (e.g. "last 24h"/"last 7 days" from the
        # dashboard's range selector), trim to just that many most-recent
        # rows so KPIs/analytics reflect the selected range instead of
        # always summarizing the entire dataset regardless of what's shown.
        self.df = df.tail(limit) if limit else df

    # ---- Analysis -------------------------------------------------
    def analyze(self) -> dict:
        return {
            "consumption": consumption_summary(self.df),
            "breakdown": submeter_breakdown(self.df),
            "trend_pct_vs_prev_period": trend_pct(self.df),
            "anomalies": detect_anomalies(self.df),
            "off_hours": off_hours_baseline_waste(self.df),
            "temperature": temperature_correlation(self.df),
            "occupancy": occupancy_correlation(self.df),
        }

    # ---- Recommendations -------------------------------------------
    def recommend(self, analysis: dict | None = None) -> list[dict]:
        analysis = analysis or self.analyze()
        recs = []

        breakdown = analysis["breakdown"]
        off_hours = analysis["off_hours"]
        trend = analysis["trend_pct_vs_prev_period"]
        anomalies = analysis["anomalies"]

        # Rule 1: off-hours phantom load
        if off_hours["waste_ratio_pct"] >= 40:
            recs.append({
                "id": "REC-OFFHOURS-01",
                "title": "Reduce off-hours phantom load",
                "category": "scheduling",
                "severity": "high" if off_hours["waste_ratio_pct"] >= 55 else "medium",
                "estimated_savings_pct": round(min(off_hours["waste_ratio_pct"] * 0.25, 18), 1),
                "description": (
                    f"Off-hours consumption is running at {off_hours['waste_ratio_pct']}% "
                    f"of daytime average ({off_hours['off_hours_avg']} kWh vs "
                    f"{off_hours['daytime_avg']} kWh). This points to equipment, HVAC, or "
                    "lighting left active outside occupied hours. Set back HVAC schedules "
                    "and add lighting occupancy sensors for after-hours zones."
                ),
            })

        # Rule 2: HVAC dominant share
        if breakdown["hvac_pct"] >= 42:
            recs.append({
                "id": "REC-HVAC-01",
                "title": "Optimize HVAC scheduling and setpoints",
                "category": "hvac",
                "severity": "medium",
                "estimated_savings_pct": round((breakdown["hvac_pct"] - 35) * 0.4, 1),
                "description": (
                    f"HVAC accounts for {breakdown['hvac_pct']}% of total consumption, "
                    "above the typical 35-40% benchmark for commercial buildings. "
                    "Consider a setpoint audit, demand-controlled ventilation, and "
                    "pre-cooling/pre-heating scheduling tied to occupancy forecasts."
                ),
            })

        # Rule 3: rising trend
        if trend >= 8:
            recs.append({
                "id": "REC-TREND-01",
                "title": "Investigate rising consumption trend",
                "category": "monitoring",
                "severity": "medium" if trend < 15 else "high",
                "estimated_savings_pct": round(trend * 0.3, 1),
                "description": (
                    f"Consumption has risen {trend}% comparing the recent half of the "
                    "monitoring window to the earlier half. Check for degraded equipment "
                    "efficiency, new load additions, or seasonal drivers before it "
                    "compounds into next period's baseline."
                ),
            })

        # Rule 4: lighting share high relative to occupancy-driven norm
        if breakdown["lighting_pct"] >= 25:
            recs.append({
                "id": "REC-LIGHT-01",
                "title": "Upgrade to occupancy-based lighting control",
                "category": "lighting",
                "severity": "low",
                "estimated_savings_pct": round((breakdown["lighting_pct"] - 18) * 0.5, 1),
                "description": (
                    f"Lighting is {breakdown['lighting_pct']}% of total load. Daylight "
                    "harvesting and occupancy/vacancy sensors in low-traffic areas "
                    "typically cut lighting energy 20-30% with minimal capex."
                ),
            })

        # Rule 5: recurring high-severity anomalies -> possible faulty equipment
        high_sev = [a for a in anomalies if a["severity"] == "high"]
        if len(high_sev) >= 3:
            recs.append({
                "id": "REC-ANOMALY-01",
                "title": "Inspect equipment causing repeated consumption spikes",
                "category": "maintenance",
                "severity": "high",
                "estimated_savings_pct": 5.0,
                "description": (
                    f"{len(high_sev)} high-severity anomalies detected in the monitoring "
                    "window, well above expected hourly load. Repeated spikes often "
                    "indicate a stuck damper, failing compressor, or equipment short-cycling. "
                    "Flag for the Maintenance Agent to cross-check fault logs."
                ),
            })

        # Rule 6: significant unoccupied load (occupancy-aware waste)
        occupancy = analysis.get("occupancy", {})
        if occupancy.get("available") and occupancy["unoccupied_load_pct_of_occupied"] >= 50:
            recs.append({
                "id": "REC-OCCUPANCY-01",
                "title": "Cut load during zero-occupancy periods",
                "category": "occupancy",
                "severity": "high" if occupancy["unoccupied_load_pct_of_occupied"] >= 70 else "medium",
                "estimated_savings_pct": round(min(occupancy["unoccupied_load_pct_of_occupied"] * 0.2, 15), 1),
                "description": (
                    f"When the building is fully unoccupied, load still averages "
                    f"{occupancy['avg_load_when_unoccupied_kwh']} kWh — "
                    f"{occupancy['unoccupied_load_pct_of_occupied']}% of the occupied-period "
                    "average. This is a stronger signal than time-of-day scheduling alone: "
                    "tie HVAC/lighting directly to real-time occupancy sensors rather than "
                    "fixed schedules, especially for irregular hours."
                ),
            })

        # Rule 7: weak temperature correlation despite HVAC-heavy load
        # (load isn't responding to weather the way it should -> possible
        # stuck setpoint, damper fault, or HVAC running independent of demand)
        temperature = analysis.get("temperature", {})
        if (temperature.get("available") and breakdown["hvac_pct"] >= 30
                and abs(temperature["correlation"]) < 0.15):
            recs.append({
                "id": "REC-TEMP-01",
                "title": "HVAC load not tracking outdoor temperature",
                "category": "hvac",
                "severity": "medium",
                "estimated_savings_pct": 6.0,
                "description": (
                    f"Consumption shows almost no correlation with outdoor temperature "
                    f"(r={temperature['correlation']}) despite HVAC being "
                    f"{breakdown['hvac_pct']}% of load. In a well-tuned system, load should "
                    "rise on hot/cold days and fall in mild weather. Flat load regardless of "
                    "weather often means a stuck setpoint, a damper stuck open, or HVAC "
                    "running on a fixed schedule instead of demand response."
                ),
            })

        # Sort by severity then estimated savings, highest impact first
        severity_rank = {"high": 0, "medium": 1, "low": 2}
        recs.sort(key=lambda r: (severity_rank[r["severity"]], -r["estimated_savings_pct"]))
        return recs

    # ---- Entry point -------------------------------------------------
    def run(self) -> dict:
        analysis = self.analyze()
        recommendations = self.recommend(analysis)
        return {
            "building_id": self.building_id,
            "analysis": analysis,
            "recommendations": recommendations,
        }
