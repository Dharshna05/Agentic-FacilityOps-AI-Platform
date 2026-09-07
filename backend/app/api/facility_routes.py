"""
Facility Intelligence Engine (Milestone 4).

Aggregates insights from all five agents (Energy, Maintenance, Occupancy,
Security, Cost) into the executive-level views the handout's "Facility
Analytics & Intelligence Engine" module calls for: a single facility
health score, a unified alert feed across every source table, and the
executive dashboard's KPI bundle. This is deliberately a thin
aggregation layer — it reuses each agent's own analyze()/list_alerts()
rather than re-deriving anything, so it can never drift from what each
domain dashboard already shows.

HONEST SCORING NOTE: the 0-100 composite is a simple equal-weighted
average of five rule-derived subscores (one already ML-derived —
Maintenance's avg_health_score comes straight from the RUL model). It is
a readable executive summary, not a validated single metric — the
per-domain breakdown is always returned alongside it so nothing is
hidden behind one number.
"""
from fastapi import APIRouter, Query, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.intelligence_engine import investigate_facility
from app.agents.energy_agent import EnergyAgent
from app.agents.maintenance_agent import MaintenanceAgent
from app.agents.occupancy_agent import OccupancyAgent
from app.agents.security_agent import SecurityAgent
from app.agents.cost_agent import CostAgent
from app.services import maintenance_service, security_service, cost_service
from app.models.maintenance_models import Asset
from app.models.occupancy_models import Zone
from app.models.security_models import AccessPoint, SecurityAlert
from app.models.cost_models import CostVendor, CostAlert

router = APIRouter(prefix="/facility", tags=["facility"])

DEFAULT_BUILDING = "BLD-HQ-01"


def _energy_subscore(analysis: dict) -> float:
    off_hours_pct = analysis["off_hours"].get("waste_ratio_pct", 0) or 0
    anomaly_penalty = min(len(analysis.get("anomalies", [])) * 2, 20)
    return round(max(0.0, 100 - off_hours_pct * 0.5 - anomaly_penalty), 1)


def _maintenance_subscore(analysis: dict) -> float:
    return float(analysis["fleet"].get("avg_health_score", 100) or 100)


def _occupancy_subscore(analysis: dict) -> float:
    b = analysis["building"]
    zones = b.get("zones_monitored") or 1
    overcrowded = b.get("overcrowded_zones", 0)
    return round(max(0.0, 100 - (overcrowded / zones) * 100), 1)


def _security_subscore(analysis: dict) -> float:
    b = analysis["building"]
    events = b.get("events_last_24h") or 0
    flagged = b.get("flagged_last_24h", 0)
    if events == 0:
        return 100.0
    return round(max(0.0, 100 - (flagged / events) * 200), 1)


def _cost_subscore(analysis: dict) -> float:
    compliance = analysis.get("budget_compliance", [])
    if not compliance:
        return 100.0
    over_count = sum(1 for c in compliance if c["status"] == "over")
    at_risk_count = sum(1 for c in compliance if c["status"] == "at_risk")
    penalty = over_count * 15 + at_risk_count * 6
    return round(max(0.0, 100 - penalty), 1)


@router.get("/health")
def facility_health(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    """Composite facility health score aggregated across all five agents.
    See module docstring for the honest scoring caveat."""
    energy = EnergyAgent(db, building_id).analyze()
    maintenance = MaintenanceAgent(db, building_id).analyze()
    occupancy = OccupancyAgent(db, building_id).analyze()
    security = SecurityAgent(db, building_id).analyze()
    cost = CostAgent(db, building_id).analyze()

    subscores = {
        "energy": _energy_subscore(energy),
        "maintenance": _maintenance_subscore(maintenance),
        "occupancy": _occupancy_subscore(occupancy),
        "security": _security_subscore(security),
        "cost": _cost_subscore(cost),
    }
    composite = round(sum(subscores.values()) / len(subscores), 1)
    status = "Excellent" if composite >= 85 else "Good" if composite >= 70 else "Needs Attention" if composite >= 50 else "Critical"

    return {
        "building_id": building_id,
        "composite_score": composite,
        "status": status,
        "subscores": subscores,
        "note": "Equal-weighted average of five per-agent subscores — see each domain dashboard for the full picture behind each number.",
    }


@router.get("/alerts")
def facility_alerts(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    """Unified alert feed across every agent's own alert/work-order table
    — one list for the executive dashboard, sourced from the same real
    rows each domain dashboard reads (nothing re-derived)."""
    work_orders = [{**w, "domain": "maintenance", "title": w["reason"]} for w in maintenance_service.list_work_orders(db, building_id, status="open")]
    security_alerts = [{**a, "domain": "security", "title": a["alert_type"]} for a in security_service.list_alerts(db, building_id, status="open")]
    cost_alerts = [{**a, "domain": "cost", "title": a["alert_type"]} for a in cost_service.list_alerts(db, building_id, status="open")]

    combined = work_orders + security_alerts + cost_alerts
    severity_rank = {"high": 0, "medium": 1, "low": 2}
    combined.sort(key=lambda a: (severity_rank.get(a.get("severity", "low"), 2), a.get("created_at") or ""), reverse=False)
    return {"building_id": building_id, "alerts": combined, "total_open": len(combined)}


@router.get("/kpis")
def facility_kpis(building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    """Executive dashboard KPI bundle: one headline number per domain,
    each pulled from that domain's own agent so it always matches what
    the domain dashboard shows."""
    energy = EnergyAgent(db, building_id).analyze()
    maintenance = MaintenanceAgent(db, building_id).analyze()
    occupancy = OccupancyAgent(db, building_id).analyze()
    security = SecurityAgent(db, building_id).analyze()
    cost = CostAgent(db, building_id).analyze()

    return {
        "building_id": building_id,
        "energy_total_kwh": energy["consumption"].get("total_kwh"),
        "maintenance_avg_health_score": maintenance["fleet"].get("avg_health_score"),
        "maintenance_open_critical": maintenance["fleet"].get("open_critical"),
        "occupancy_avg_utilization_pct": occupancy["building"].get("avg_utilization_pct"),
        "security_flagged_last_24h": security["building"].get("flagged_last_24h"),
        "cost_total_spend_inr": cost["summary"].get("total_spend_inr"),
        "cost_categories_over_budget": sum(1 for c in cost["budget_compliance"] if c["status"] == "over"),
    }


@router.get("/investigate")
def facility_investigate(building_id: str = Query(DEFAULT_BUILDING)):
    """
    The cross-combined agent (Milestone 4): a single agentic run with
    EVERY domain's tools available at once, specifically looking for
    correlations a single-domain investigation (see /energy/investigate,
    /maintenance/investigate, etc.) would not surface — e.g. an energy
    anomaly and a maintenance risk at the same asset, or occupancy in a
    restricted zone lining up with a flagged security event. Same
    provider-fallback and trace-transparency guarantees as every other
    /*/investigate endpoint.
    """
    return investigate_facility(building_id)


@router.get("/search")
def facility_search(q: str = Query(..., min_length=1), building_id: str = Query(DEFAULT_BUILDING), db: Session = Depends(get_db)):
    """
    Backs the header search button/Cmd+K palette (previously a static,
    non-functional button in every dashboard's header). Case-insensitive
    substring match across the named entities that make sense to jump
    straight to — equipment assets, occupancy zones, vendors, access
    points — plus currently-open Cost/Security alerts, so "find that
    thing I saw an alert about" works without knowing which dashboard it
    lives on. Each result carries a `route` the frontend navigates to
    directly; deliberately NOT full-text across every raw reading table
    (e.g. individual sensor rows), since that's a firehose of
    low-relevance matches for a quick-jump search, not a data explorer.
    """
    like = f"%{q}%"
    results = []

    for a in db.query(Asset).filter(Asset.building_id == building_id).filter(
        (Asset.asset_id.ilike(like)) | (Asset.name.ilike(like)) | (Asset.location.ilike(like))
    ).limit(6):
        results.append({
            "domain": "maintenance", "type": "asset", "id": a.asset_id,
            "label": a.name, "subtitle": f"{a.asset_type} · {a.location or 'location n/a'}",
            "route": "/maintenance",
        })

    for z in db.query(Zone).filter(Zone.building_id == building_id).filter(
        (Zone.zone_id.ilike(like)) | (Zone.name.ilike(like))
    ).limit(6):
        results.append({
            "domain": "occupancy", "type": "zone", "id": z.zone_id,
            "label": z.name, "subtitle": f"{z.zone_type} · capacity {z.capacity}",
            "route": "/occupancy",
        })

    for v in db.query(CostVendor).filter(CostVendor.building_id == building_id).filter(
        CostVendor.vendor_name.ilike(like)
    ).limit(6):
        results.append({
            "domain": "cost", "type": "vendor", "id": v.vendor_id,
            "label": v.vendor_name, "subtitle": f"{v.primary_category} · {v.order_count} orders",
            "route": "/cost",
        })

    for ap in db.query(AccessPoint).filter(AccessPoint.building_id == building_id).filter(
        (AccessPoint.access_point_id.ilike(like)) | (AccessPoint.name.ilike(like))
    ).limit(6):
        results.append({
            "domain": "security", "type": "access_point", "id": ap.access_point_id,
            "label": ap.name, "subtitle": f"{ap.risk_level} risk",
            "route": "/security",
        })

    for al in db.query(SecurityAlert).filter(
        SecurityAlert.building_id == building_id, SecurityAlert.status == "open", SecurityAlert.description.ilike(like)
    ).limit(4):
        results.append({
            "domain": "security", "type": "alert", "id": str(al.id),
            "label": al.alert_type, "subtitle": al.description,
            "route": "/security",
        })

    for al in db.query(CostAlert).filter(
        CostAlert.building_id == building_id, CostAlert.status == "open", CostAlert.description.ilike(like)
    ).limit(4):
        results.append({
            "domain": "cost", "type": "alert", "id": str(al.id),
            "label": al.alert_type, "subtitle": al.description,
            "route": "/cost",
        })

    return {"query": q, "count": len(results), "results": results}
