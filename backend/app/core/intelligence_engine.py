"""
Intelligence Engine — the LLM reasoning layer that sits above individual
agents (Energy, and later Maintenance/Occupancy/Security/Cost).

Two distinct capabilities live here:

1. summarize_energy_analysis() — a single-shot LLM call that takes the
   Energy Agent's already-computed rule-based output and writes a plain-
   English briefing. Useful, but NOT agentic: we decided what to compute
   and just asked the model to narrate it.

2. investigate_energy() — a genuinely agentic run. The model is given a
   goal and a set of real tools (app/core/agent_tools.py) and DECIDES for
   itself which analyses to run, in what order, and whether the evidence
   warrants flagging the finding to another agent. This is the actual
   "agentic AI" component of the platform, as distinct from a fixed
   pipeline or a single summarization call.
"""
import logging
from app.services.ai_providers.factory import get_ai_provider
from app.services.ai_providers.mock_provider import MockProvider
from app.core.agent_tools import ALL_TOOLS
from app.core.maintenance_tools import ALL_TOOLS as MAINTENANCE_TOOLS
from app.core.occupancy_tools import ALL_TOOLS as OCCUPANCY_TOOLS
from app.core.security_tools import ALL_TOOLS as SECURITY_TOOLS
from app.core.cost_tools import ALL_TOOLS as COST_TOOLS

# Every domain's tools combined, deduplicated by function identity — this
# is what makes the Facility Intelligence Agent below "cross-domain": it is
# the exact same real tool functions each single-domain agent uses (so a
# handoff it makes is a genuine action, not a simulated one), just handed
# to one model at once instead of five separate ones.
CROSS_DOMAIN_TOOLS = list(dict.fromkeys(
    ALL_TOOLS + MAINTENANCE_TOOLS + OCCUPANCY_TOOLS + SECURITY_TOOLS + COST_TOOLS
))

logger = logging.getLogger(__name__)


def _safe_generate(provider, provider_name: str, system_prompt: str, user_prompt: str) -> tuple[str, str]:
    """Runs provider.generate() but never lets a runtime API failure (bad
    key, rate limit, network blip) crash the request — falls back to
    MockProvider's deterministic output with a clear note, the same way
    factory.py already falls back when the key is missing entirely."""
    try:
        return provider.generate(system_prompt, user_prompt), provider_name
    except Exception as e:
        logger.warning(f"{provider_name} generate() call failed at runtime ({e}); falling back to MockProvider.")
        fallback = MockProvider().generate(system_prompt, user_prompt)
        return f"{fallback}\n\n[Note: {provider_name} API call failed ({e}); showing mock fallback instead.]", f"{provider_name} (call failed)"


def _safe_agentic_task(provider, provider_name: str, system_prompt: str, task_prompt: str, tools: list) -> tuple[dict, str]:
    """Same runtime-failure safety net as _safe_generate(), for the
    agentic tool-calling path."""
    try:
        return provider.run_agentic_task(system_prompt, task_prompt, tools), provider_name
    except Exception as e:
        logger.warning(f"{provider_name} run_agentic_task() call failed at runtime ({e}); falling back to MockProvider.")
        result = MockProvider().run_agentic_task(system_prompt, task_prompt, tools)
        result["final_text"] = f"{result['final_text']}\n\n[Note: {provider_name} API call failed ({e}); showing mock fallback instead.]"
        return result, f"{provider_name} (call failed)"

SUMMARY_SYSTEM_PROMPT = (
    "You are the Intelligence Engine of a facility operations AI platform. "
    "You receive structured analytics and rule-based recommendations from a "
    "domain agent (e.g. the Energy Agent) and must synthesize them into a "
    "short, prioritized, plain-English briefing for a facility manager. "
    "Be concrete and reference the actual numbers given. Do not invent data "
    "that wasn't provided. Keep it under 200 words."
)

INVESTIGATION_SYSTEM_PROMPT = (
    "You are the Energy Agent of a facility operations AI platform, "
    "investigating a building's energy efficiency. You have tools to pull "
    "consumption data, submeter breakdowns, anomalies, temperature and "
    "occupancy correlations, and an ML-based forecast (available at 1h, 6h, "
    "or 24h horizons — each backed by a separately trained model with "
    "different accuracy; the forecast tool's response includes a confidence "
    "field you should factor into how much weight you give the prediction, "
    "especially at 24h where accuracy is only marginal). You do NOT have to "
    "call every tool — decide which ones are actually relevant based on "
    "what you learn as you go, and only check longer forecast horizons if "
    "the near-term signal actually warrants it. If you find evidence "
    "suggesting an equipment fault (e.g. multiple high-severity anomalies) "
    "rather than a scheduling issue, use the flag_for_maintenance_review "
    "tool to hand it off. When you have enough information, write a short "
    "(under 200 words) plain-English investigation summary explaining what "
    "you checked, why, and what you found. Reference actual numbers from "
    "the tool results."
)


MAINTENANCE_INVESTIGATION_SYSTEM_PROMPT = (
    "You are the Maintenance Agent of a facility operations AI platform, "
    "investigating the health of a building's equipment fleet. You have "
    "tools to pull the fleet-wide health summary, drill into a specific "
    "asset's ML-predicted health (remaining useful life, health score, "
    "predicted maintenance date, and the model's own confidence), list the "
    "assets currently most at risk, and open a real maintenance work order. "
    "You do NOT have to call every tool — start broad (fleet summary), "
    "narrow to at-risk assets only if the fleet summary suggests a problem, "
    "and only open work orders for assets where the evidence is clear "
    "(Critical status, or Warning with limited remaining life) — do not "
    "open work orders speculatively for every asset you inspect. When you "
    "have enough information, write a short (under 200 words) plain-"
    "English investigation summary explaining what you checked, why, and "
    "what you found, referencing actual numbers from the tool results."
)


OCCUPANCY_INVESTIGATION_SYSTEM_PROMPT = (
    "You are the Occupancy Agent of a facility operations AI platform, "
    "investigating space utilization across a building. You have tools to "
    "pull the building-wide occupancy summary, drill into a specific "
    "zone's current status, list zones currently overcrowded, check the "
    "status of restricted zones specifically (e.g. server rooms — worth "
    "checking even when nowhere near the general overcrowding threshold, "
    "since ANY occupancy there is unusual), and — important — flag a "
    "restricted zone for Security review if it shows occupancy, since "
    "headcount data alone can't confirm who is present or whether their "
    "access was authorized. Only use the security handoff tool for "
    "zone_type='restricted' zones with actual current occupancy, not for "
    "ordinary workspace/meeting-room overcrowding. When you have enough "
    "information, write a short (under 200 words) plain-English "
    "investigation summary explaining what you checked, why, and what you "
    "found, referencing actual numbers from the tool results."
)


SECURITY_INVESTIGATION_SYSTEM_PROMPT = (
    "You are the Security Agent of a facility operations AI platform, "
    "investigating access-control activity across a building. You have "
    "tools to pull the building-wide security summary, list recent events "
    "the anomaly detector flagged (with an anomaly score — higher means "
    "more statistically unusual), check a specific access point's "
    "configured risk level (low/medium/high), and open a real security "
    "alert. The anomaly detector is honest but imperfect (see its own "
    "precision/recall in the tool results if surfaced) — weigh anomaly "
    "score together with the access point's risk level, and only open "
    "alerts where the evidence is clear (a high anomaly score at a "
    "medium/high-risk access point, or a repeated-denial pattern) rather "
    "than for every flagged event. When you have enough information, "
    "write a short (under 200 words) plain-English investigation summary "
    "explaining what you checked, why, and what you found, referencing "
    "actual numbers from the tool results."
)


COST_INVESTIGATION_SYSTEM_PROMPT = (
    "You are the Cost Optimization Agent of a facility operations AI "
    "platform, investigating facility spend. You have tools to pull the "
    "overall spend summary, check budget compliance by category "
    "(budgets are assumption-based, not a real published figure — the "
    "tool result says so), list invoices the anomaly detector flagged as "
    "statistically unusual (no labeled ground truth exists for this real "
    "invoice data, so treat a flag as a lead, not a confirmed error), "
    "check the ML spend-trend forecast (only ~27 weeks of real training "
    "data — weigh its reported confidence), check vendor concentration "
    "risk, and open a real cost alert. Only open alerts where the "
    "evidence is clear (a category clearly over budget, or a "
    "high-confidence flagged invoice at a concentrated vendor) — not for "
    "every data point you check. When you have enough information, write "
    "a short (under 200 words) plain-English investigation summary "
    "explaining what you checked, why, and what you found, referencing "
    "actual numbers from the tool results."
)


CROSS_DOMAIN_INVESTIGATION_SYSTEM_PROMPT = (
    "You are the Facility Intelligence Agent of a facility operations AI "
    "platform — unlike the five domain agents (Energy, Maintenance, "
    "Occupancy, Security, Cost), which each investigate one thing, you "
    "have ALL of their tools at once and your job is specifically to look "
    "for CROSS-DOMAIN correlations a single-domain agent would never see: "
    "e.g. whether energy anomalies line up with equipment nearing failure "
    "(Energy + Maintenance), whether occupancy in a restricted zone "
    "coincides with a flagged security event (Occupancy + Security), "
    "whether a maintenance work order's asset/location matches an area "
    "with an energy or cost anomaly (Maintenance + Energy/Cost), or "
    "whether a category over budget is explained by a flagged invoice "
    "concentrated at one vendor (Cost). Start by pulling the summary tool "
    "from at least three different domains to get a baseline picture "
    "before you decide which specific correlation is worth chasing — do "
    "not just repeat one domain's own investigation. Only call the more "
    "expensive/specific tools (asset drill-downs, zone drill-downs, "
    "flagged-event lists) once a summary tool actually suggests there is "
    "something there to explain. You may use the handoff tools "
    "(flag_for_maintenance_review, flag_restricted_zone_for_security_"
    "review, create_work_order, create_security_alert, create_cost_alert) "
    "if the cross-domain evidence genuinely warrants it, but do not "
    "duplicate an action a single-domain agent would already take on "
    "unremarkable single-domain evidence — the bar here is specifically "
    "'this only makes sense when you look at two domains together'. When "
    "you have enough information, write a short (under 220 words) plain-"
    "English investigation summary explicitly naming which domains you "
    "connected and how, referencing actual numbers from the tool results. "
    "If you genuinely found no cross-domain correlation worth reporting, "
    "say so plainly rather than manufacturing a connection."
)



def summarize_energy_analysis(analysis: dict, recommendations: list[dict]) -> tuple[str, str]:
    provider, provider_name = get_ai_provider()

    consumption = analysis.get("consumption", {})
    breakdown = analysis.get("breakdown", {})
    trend = analysis.get("trend_pct_vs_prev_period")
    occupancy = analysis.get("occupancy", {})

    user_prompt = f"""
Energy analysis for this period:
- Total consumption: {consumption.get('total_kwh')} kWh
- Peak load: {consumption.get('peak_kwh')} kWh
- Trend vs previous period: {trend}%
- Load breakdown: HVAC {breakdown.get('hvac_pct')}%, Lighting {breakdown.get('lighting_pct')}%, \
Plug load {breakdown.get('plug_load_pct')}%, Other {breakdown.get('other_pct')}%
- Unoccupied-period load: {occupancy.get('unoccupied_load_pct_of_occupied', 'n/a')}% of occupied-period average

Top recommendations (already ranked by severity):
{chr(10).join(f"- [{r['severity'].upper()}] {r['title']}: {r['description']}" for r in recommendations[:5])}

Write a short briefing synthesizing the above for a facility manager.
"""
    return _safe_generate(provider, provider_name, SUMMARY_SYSTEM_PROMPT, user_prompt)


def investigate_energy(building_id: str = "BLD-HQ-01") -> dict:
    """
    Runs the agentic investigation: the model (or, with MockProvider, a
    simulated stand-in) decides which of the available tools to call and
    in what order to reach a conclusion about this building's energy
    efficiency. Returns the final narrative plus the full decision trace.
    """
    provider, provider_name = get_ai_provider()
    task_prompt = f"Investigate energy efficiency for building {building_id}."
    result, provider_name = _safe_agentic_task(provider, provider_name, INVESTIGATION_SYSTEM_PROMPT, task_prompt, ALL_TOOLS)
    return {
        "building_id": building_id,
        "final_summary": result["final_text"],
        "tool_calls": result["tool_calls"],
        "tool_call_count": len(result["tool_calls"]),
        "provider": provider_name,
    }


def investigate_maintenance(building_id: str = "BLD-HQ-01") -> dict:
    """
    Same genuinely-agentic pattern as investigate_energy(), pointed at the
    Maintenance Agent's tools instead. The model (or MockProvider's
    conditional simulation) decides which assets are worth a closer look
    and whether the evidence warrants opening a real work order.
    """
    provider, provider_name = get_ai_provider()
    task_prompt = f"Investigate equipment health for building {building_id}."
    result, provider_name = _safe_agentic_task(provider, provider_name, MAINTENANCE_INVESTIGATION_SYSTEM_PROMPT, task_prompt, MAINTENANCE_TOOLS)
    return {
        "building_id": building_id,
        "final_summary": result["final_text"],
        "tool_calls": result["tool_calls"],
        "tool_call_count": len(result["tool_calls"]),
        "provider": provider_name,
    }


def investigate_occupancy(building_id: str = "BLD-HQ-01") -> dict:
    """
    Same genuinely-agentic pattern, pointed at the Occupancy Agent's tools.
    The model decides which zones are worth a closer look and whether a
    restricted zone's occupancy warrants a real handoff to Security.
    """
    provider, provider_name = get_ai_provider()
    task_prompt = f"Investigate space utilization and occupancy for building {building_id}."
    result, provider_name = _safe_agentic_task(provider, provider_name, OCCUPANCY_INVESTIGATION_SYSTEM_PROMPT, task_prompt, OCCUPANCY_TOOLS)
    return {
        "building_id": building_id,
        "final_summary": result["final_text"],
        "tool_calls": result["tool_calls"],
        "tool_call_count": len(result["tool_calls"]),
        "provider": provider_name,
    }


def investigate_security(building_id: str = "BLD-HQ-01") -> dict:
    """
    Same genuinely-agentic pattern, pointed at the Security Agent's tools.
    The model decides which flagged events warrant a real alert, weighing
    anomaly score against access-point risk level rather than alerting on
    every flag.
    """
    provider, provider_name = get_ai_provider()
    task_prompt = f"Investigate access-control activity for building {building_id}."
    result, provider_name = _safe_agentic_task(provider, provider_name, SECURITY_INVESTIGATION_SYSTEM_PROMPT, task_prompt, SECURITY_TOOLS)
    return {
        "building_id": building_id,
        "final_summary": result["final_text"],
        "tool_calls": result["tool_calls"],
        "tool_call_count": len(result["tool_calls"]),
        "provider": provider_name,
    }


def investigate_cost(building_id: str = "BLD-HQ-01") -> dict:
    """
    Same genuinely-agentic pattern, pointed at the Cost Agent's tools.
    The model decides which budget risks, flagged invoices, or vendor-
    concentration signals are worth a real cost alert.
    """
    provider, provider_name = get_ai_provider()
    task_prompt = f"Investigate facility spend and cost-optimization opportunities for building {building_id}."
    result, provider_name = _safe_agentic_task(provider, provider_name, COST_INVESTIGATION_SYSTEM_PROMPT, task_prompt, COST_TOOLS)
    return {
        "building_id": building_id,
        "final_summary": result["final_text"],
        "tool_calls": result["tool_calls"],
        "tool_call_count": len(result["tool_calls"]),
        "provider": provider_name,
    }


def investigate_facility(building_id: str = "BLD-HQ-01") -> dict:
    """
    The Facility Intelligence Agent (Milestone 4's "cross-combined" agent):
    unlike investigate_energy()/investigate_maintenance()/etc., which each
    reason over ONE domain's tools, this gives the model every domain's
    tools at once specifically to look for correlations a single-domain
    agent structurally cannot see (e.g. an energy anomaly and a
    maintenance risk signal at the same asset/time; occupancy in a
    restricted zone coinciding with a flagged security event). Returns the
    same shape as the single-domain investigate_*() functions plus
    `domains_available` so the caller can show which tools were in scope.
    """
    provider, provider_name = get_ai_provider()
    task_prompt = (
        f"Investigate building {building_id} for correlations across the Energy, "
        "Maintenance, Occupancy, Security, and Cost domains that a single-domain "
        "agent would not surface on its own."
    )
    result, provider_name = _safe_agentic_task(provider, provider_name, CROSS_DOMAIN_INVESTIGATION_SYSTEM_PROMPT, task_prompt, CROSS_DOMAIN_TOOLS)
    return {
        "building_id": building_id,
        "final_summary": result["final_text"],
        "tool_calls": result["tool_calls"],
        "tool_call_count": len(result["tool_calls"]),
        "domains_available": ["energy", "maintenance", "occupancy", "security", "cost"],
        "provider": provider_name,
    }
