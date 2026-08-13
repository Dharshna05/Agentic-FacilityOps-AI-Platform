"""
Deterministic mock provider — lets the Intelligence Engine run (and be
tested) without a real API key. Produces a template-based synthesis that's
structurally similar to what an LLM would return, so the calling code and
tests are identical regardless of which provider is wired in.
"""
from typing import Callable
from app.services.ai_providers.base import AIProvider


class MockProvider(AIProvider):
    def generate(self, system_prompt: str, user_prompt: str) -> str:
        return (
            "[MockProvider — no LLM call made, deterministic fallback for tests/no-API-key dev]\n\n"
            "Based on the current consumption pattern, the facility shows opportunities for "
            "efficiency improvement in the areas flagged by the Energy Agent's analysis below. "
            "Prioritize the highest-severity items first, as they represent the largest "
            "identified savings potential. Cross-reference off-hours and occupancy-based "
            "findings with actual building schedules before implementing changes.\n\n"
            f"(Prompt received, {len(user_prompt)} chars — swap in GeminiProvider with a real "
            "GEMINI_API_KEY for actual LLM-generated analysis.)"
        )

    def run_agentic_task(self, system_prompt: str, task_prompt: str, tools: list[Callable]) -> dict:
        """
        Simulated agentic loop — NOT real LLM reasoning. This exists so the
        investigation flow can be built, tested, and demoed without an API
        key. It follows a scripted-but-conditional decision sequence (calls
        different tools depending on what earlier tools returned) so the
        *shape* of agentic behavior — tool call, inspect result, decide
        next action — is genuine, even though the decisions themselves are
        hardcoded here rather than made by a model. Swap in GeminiProvider
        (real GEMINI_API_KEY) for the model to make these decisions itself.
        """
        tool_map = {t.__name__: t for t in tools}
        trace = []

        def call(name, **kwargs):
            if name not in tool_map:
                return None
            result = tool_map[name](**kwargs)
            trace.append({"tool": name, "args": kwargs, "result": result})
            return result

        if "get_fleet_summary" in tool_map:
            return self._simulate_maintenance_investigation(call, trace)

        consumption = call("get_consumption_summary")
        breakdown = call("get_submeter_breakdown")
        anomalies = call("get_anomalies")

        # Conditional: only dig into temperature if HVAC is a large share
        temperature = None
        if breakdown and breakdown.get("hvac_pct", 0) >= 30:
            temperature = call("get_temperature_correlation")

        occupancy = call("get_occupancy_correlation")

        # Conditional: only flag maintenance if there's real evidence
        high_sev_count = len([a for a in (anomalies or []) if a.get("severity") == "high"])
        if high_sev_count >= 2:
            call("flag_for_maintenance_review",
                 reason=f"{high_sev_count} high-severity anomalies detected in the monitoring window, "
                        "suggesting possible equipment malfunction rather than a scheduling issue.",
                 severity="high")

        # Always check the near-term (1h) forecast first — it's the
        # cheapest, most reliable signal.
        forecast_1h = call("get_ml_forecast", horizon="1h")

        # Genuine multi-step branch driven by an INTERMEDIATE RESULT: only
        # bother checking the 24h outlook if the 1h forecast suggests a
        # real change is coming (not just noise). This mirrors what a real
        # model would plausibly do — check further out only when the
        # near-term signal warrants it — rather than always calling every
        # tool regardless of what earlier results showed.
        forecast_24h = None
        if forecast_1h and forecast_1h.get("current_kwh"):
            pct_change = abs(forecast_1h["predicted_kwh"] - forecast_1h["current_kwh"]) / max(forecast_1h["current_kwh"], 1) * 100
            if pct_change >= 8:
                forecast_24h = call("get_ml_forecast", horizon="24h")

        lines = [
            "[MockProvider — simulated agentic run, not real LLM reasoning; "
            "see run_agentic_task() docstring]",
            "",
            f"Reviewed {len(trace)} data points across consumption, breakdown, anomalies"
            + (", temperature correlation" if temperature else "")
            + ", occupancy correlation, and forecast.",
        ]
        if consumption:
            lines.append(f"Total consumption: {consumption.get('total_kwh')} kWh "
                         f"(peak {consumption.get('peak_kwh')} kWh).")
        if high_sev_count >= 2:
            lines.append(f"Flagged {high_sev_count} high-severity anomalies for maintenance review "
                         "based on repeated deviation from expected load.")
        if temperature:
            lines.append(f"HVAC is {breakdown.get('hvac_pct')}% of load; checked temperature "
                         f"correlation (r={temperature.get('correlation')}).")
        if forecast_1h:
            lines.append(f"1h forecast: {forecast_1h['predicted_kwh']} kWh "
                         f"(confidence: {forecast_1h['confidence'].get('confidence', 'n/a')}).")
        if forecast_24h:
            lines.append(f"1h forecast showed a notable shift, so also checked 24h outlook: "
                         f"{forecast_24h['predicted_kwh']} kWh (confidence: "
                         f"{forecast_24h['confidence'].get('confidence', 'n/a')} — treat with caution).")

        return {"final_text": "\n".join(lines), "tool_calls": trace}

    def _simulate_maintenance_investigation(self, call, trace) -> dict:
        """Scripted-but-conditional simulation of the Maintenance Agent's
        investigation, mirroring the Energy branch above: start broad
        (fleet summary), only drill into at-risk assets if the fleet
        summary actually shows a problem, and only open a work order when
        an individual asset's evidence (Critical status) genuinely
        warrants it — not for every asset inspected."""
        fleet = call("get_fleet_summary")

        at_risk = None
        critical_assets = []
        if fleet and (fleet.get("open_critical", 0) > 0 or fleet.get("status_pct", {}).get("Warning", 0) >= 15):
            at_risk = call("get_at_risk_assets", max_health_score=50.0)
            critical_assets = [a for a in (at_risk or []) if a.get("status") == "Critical"][:2]

        detailed = []
        for a in critical_assets:
            detail = call("get_asset_health", asset_id=a["asset_id"])
            detailed.append(detail)

        work_orders = []
        for d in detailed:
            if d and d.get("status") == "Critical":
                wo = call(
                    "create_work_order",
                    asset_id=d["asset_id"],
                    reason=f"Critical health score ({d['health_score']}/100), predicted RUL "
                           f"{d['predicted_rul_cycles']} days — flagged during agentic investigation.",
                    severity="high",
                )
                work_orders.append(wo)

        lines = [
            "[MockProvider — simulated agentic run, not real LLM reasoning; "
            "see run_agentic_task() docstring]",
            "",
        ]
        if fleet:
            lines.append(
                f"Fleet summary: {fleet['assets_monitored']} assets monitored, avg health "
                f"{fleet['avg_health_score']}/100, {fleet.get('open_critical', 0)} Critical."
            )
        if at_risk:
            lines.append(f"Fleet showed enough Warning/Critical assets to warrant drilling into "
                         f"the {len(at_risk)} most at-risk assets.")
        if critical_assets:
            names = ", ".join(a["name"] for a in critical_assets)
            lines.append(f"Inspected Critical assets in detail: {names}.")
        if work_orders:
            ids = ", ".join(f"#{w['id']}" for w in work_orders if w)
            lines.append(f"Opened {len(work_orders)} work order(s) ({ids}) based on clear Critical-status evidence.")
        elif fleet and fleet.get("open_critical", 0) == 0:
            lines.append("No Critical-status assets found — no work orders opened.")

        return {"final_text": "\n".join(lines), "tool_calls": trace}
