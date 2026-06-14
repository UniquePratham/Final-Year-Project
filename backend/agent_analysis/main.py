import os
import sys
import json
import concurrent.futures
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Adjust Python Path to find backend shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.shared.types import IntentObject, NormalizedLog, AnalysisResult
from backend.shared.ai_adapter import AIAdapter
from backend.shared.json_utils import extract_json
from backend.shared.utils import get_logger, get_config

logger = get_logger("AnalysisAgent")

app = FastAPI(title="Sentinel Forge - Analysis Agent Service")

class AnalysisRequest(BaseModel):
    intent: IntentObject
    logs: List[NormalizedLog]
    metrics: Dict[str, Any]
    provider: Optional[str] = None
    model: Optional[str] = None
    api_key: Optional[str] = None
    api_base_url: Optional[str] = None

SYSTEM_INSTRUCTION = """You are the Analysis Agent for Sentinel Forge: AI Log Analyzer.
Your role is to perform deep log intelligence analysis using pre-computed log metrics, statistical distributions, a sample of log records, and the user's intent.

You will also receive a "Rule-Based Pre-Analysis" section containing heuristic findings from the rule engine.
Treat these as strong evidence — refine and elaborate on them, do NOT contradict them unless you have overwhelming evidence from the logs.

Identify anomalies, security failures, performance bottlenecks, access violations, or availability issues.
Determine the overall severity and confidence score based on the evidence.

IMPORTANT: Pay close attention to the metrics. If error_count is high relative to total_records, this IS an anomaly.
If top_ips shows a single IP with many hits, this IS suspicious for Security intents.
If level_distribution shows most logs are ERROR, the situation IS serious.

Response Schema (Strict JSON):
{
  "anomalies": [
    {
      "description": "string description",
      "timestamp": "string or null",
      "source_ip": "string or null",
      "severity": "LOW | MEDIUM | HIGH | CRITICAL"
    }
  ],
  "trend": "degrading | stable | improving",
  "severity": "LOW | MEDIUM | HIGH | CRITICAL",
  "confidence_score": float,
  "findings": [
    "finding 1",
    "finding 2"
  ]
}

Provide ONLY the raw JSON block. Do not include markdown fences, comments, or extra text.
"""

# ---------------------------------------------------------------------------
# Rule-based analysis engine
# ---------------------------------------------------------------------------

SEVERITY_RANK = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}


def run_rule_engine(intent: IntentObject, metrics: Dict[str, Any], logs: List[NormalizedLog]) -> Dict[str, Any]:
    """Deterministic rule-based analysis. Fast, no LLM needed.

    Returns a dict with: findings, anomalies, severity, confidence, skip_llm.
    """
    findings: List[str] = []
    anomalies: List[Dict[str, Any]] = []
    severity = "LOW"
    confidence = 0.5
    skip_llm = False

    total = max(metrics.get("total_records", 1), 1)
    error_count = metrics.get("error_count", 0)
    warning_count = metrics.get("warning_count", 0)
    filtered = metrics.get("filtered_records", total)
    top_ips = metrics.get("top_ips", [])
    level_dist = metrics.get("level_distribution", {})
    user_dist = metrics.get("user_distribution", {})
    error_ratio = error_count / max(filtered, 1)

    def set_severity(new_sev, new_conf):
        nonlocal severity, confidence
        if SEVERITY_RANK.get(new_sev, 0) > SEVERITY_RANK.get(severity, 0):
            severity = new_sev
            confidence = new_conf
        elif SEVERITY_RANK.get(new_sev, 0) == SEVERITY_RANK.get(severity, 0):
            confidence = max(confidence, new_conf)

    # --- Step 0: Check for DDoS / DoS queries (independent of intent class classification) ---
    is_ddos_query = False
    if intent.raw_prompt:
        p_lower = intent.raw_prompt.lower()
        if any(kw in p_lower for kw in ("ddos", "dos", "denial of service", "traffic spike", "rate limit")):
            is_ddos_query = True
    if intent.entities and intent.entities.get("resource"):
        r_lower = str(intent.entities.get("resource")).lower()
        if any(kw in r_lower for kw in ("ddos", "dos", "denial of service", "traffic spike", "rate limit")):
            is_ddos_query = True
            
    bot_logs_count = sum(1 for l in logs if l.raw and any(bot_sig in l.raw for bot_sig in ("(Bot)", "Mozilla/5.0 (Bot)")))
    if bot_logs_count >= 5:
        is_ddos_query = True

    if is_ddos_query:
        threshold = intent.conditions.get("threshold")
        if threshold is not None:
            try:
                if isinstance(threshold, str) and threshold.lower() in ("null", "none", "undefined", ""):
                    threshold = 5
                else:
                    threshold = int(threshold)
            except (ValueError, TypeError):
                threshold = 5
        else:
            threshold = 5

        ddos_ips = []
        for ip_entry in top_ips:
            if isinstance(ip_entry, (list, tuple)) and len(ip_entry) >= 2:
                ip, cnt = ip_entry[0], ip_entry[1]
                if isinstance(cnt, int) and cnt >= threshold:
                    ddos_ips.append((ip, cnt))
        
        if ddos_ips:
            if len(ddos_ips) >= 3:
                findings.append(
                    f"ALERT: Distributed Denial of Service (DDoS) attack detected — {len(ddos_ips)} IPs generating high volume of requests (threshold: {threshold})."
                )
                for ip, cnt in ddos_ips:
                    anomalies.append({
                        "description": f"DDoS traffic source: {cnt} requests",
                        "timestamp": None,
                        "source_ip": str(ip),
                        "severity": "CRITICAL"
                    })
                set_severity("CRITICAL", 0.98)
            else:
                top_ip, top_count = ddos_ips[0]
                findings.append(
                    f"ALERT: Potential Denial of Service (DoS) attack from IP {top_ip} generating {top_count} requests (threshold: {threshold})."
                )
                anomalies.append({
                    "description": f"DoS attack source: {top_count} requests",
                    "timestamp": None,
                    "source_ip": str(top_ip),
                    "severity": "HIGH"
                })
                set_severity("HIGH", 0.95)

    # --- Step 1: Standard intent class rules (if not a DDoS query) ---
    else:
        # Check for high request volume spike (potential DDoS/DoS) independent of prompt text
        metric_ddos_ips = []
        for ip_entry in top_ips:
            if isinstance(ip_entry, (list, tuple)) and len(ip_entry) >= 2:
                ip, cnt = ip_entry[0], ip_entry[1]
                if isinstance(cnt, int) and cnt >= 15:
                    metric_ddos_ips.append((ip, cnt))
        
        if metric_ddos_ips:
            if len(metric_ddos_ips) >= 3:
                findings.append(
                    f"ALERT: High volume traffic pattern matching DDoS attack detected — {len(metric_ddos_ips)} IPs generating high volume of requests (15+ each)."
                )
                for ip, cnt in metric_ddos_ips:
                    anomalies.append({
                        "description": f"DDoS traffic source: {cnt} requests",
                        "timestamp": None,
                        "source_ip": str(ip),
                        "severity": "CRITICAL"
                    })
                set_severity("CRITICAL", 0.98)
            else:
                top_ip, top_count = metric_ddos_ips[0]
                findings.append(
                    f"ALERT: High volume traffic pattern matching DoS/spike detected from IP {top_ip} generating {top_count} requests."
                )
                anomalies.append({
                    "description": f"High traffic source: {top_count} requests",
                    "timestamp": None,
                    "source_ip": str(top_ip),
                    "severity": "HIGH"
                })
                set_severity("HIGH", 0.95)

        # --- Security intent rules ---
        if intent.intent_class == "Security":
            threshold = intent.conditions.get("threshold")
            if threshold is not None:
                try:
                    if isinstance(threshold, str) and threshold.lower() in ("null", "none", "undefined", ""):
                        threshold = 5
                    else:
                        threshold = int(threshold)
                except (ValueError, TypeError):
                    threshold = 5
            else:
                threshold = 5

            # Rule: brute-force threshold exceeded
            if error_count >= threshold:
                findings.append(
                    f"ALERT: {error_count} authentication failures detected (threshold: {threshold}). "
                    f"This exceeds the brute-force detection threshold."
                )
                set_severity("HIGH", 0.9)

            # Rule: single IP concentration
            if top_ips:
                top_ip, top_count = top_ips[0] if isinstance(top_ips[0], (list, tuple)) else (top_ips[0], 1)
                if isinstance(top_count, int) and top_count >= threshold:
                    findings.append(
                        f"ALERT: IP {top_ip} generated {top_count} events — concentrated attack source."
                    )
                    anomalies.append({
                        "description": f"Concentrated attack from {top_ip}: {top_count} events",
                        "timestamp": None,
                        "source_ip": str(top_ip),
                        "severity": "HIGH"
                    })
                    target_sev = "CRITICAL" if top_count >= threshold * 3 else "HIGH"
                    set_severity(target_sev, 0.95)

            # Rule: multiple IPs attacking (distributed brute-force)
            attacking_ips = [(ip, cnt) for ip, cnt in top_ips if isinstance(cnt, int) and cnt >= max(threshold // 2, 2)]
            if len(attacking_ips) >= 3:
                findings.append(
                    f"ALERT: Distributed attack detected — {len(attacking_ips)} IPs each with {threshold // 2}+ failures."
                )
                set_severity("CRITICAL", 0.95)

            # Rule: targeted user accounts
            if user_dist:
                targeted_users = [u for u, c in user_dist.items() if c >= threshold]
                if targeted_users:
                    findings.append(
                        f"ALERT: Targeted accounts: {', '.join(targeted_users[:5])}. "
                        f"Consider locking these accounts."
                    )

        # --- Performance intent rules ---
        elif intent.intent_class == "Performance":
            if warning_count > filtered * 0.3:
                findings.append(f"WARNING: {warning_count}/{filtered} logs are warnings ({warning_count/filtered:.0%}).")
                severity = "MEDIUM"
                confidence = 0.8
            if error_ratio > 0.1:
                findings.append(f"ERROR: {error_count}/{filtered} logs indicate errors ({error_ratio:.0%}).")
                severity = "HIGH"
                confidence = 0.85

        # --- Availability intent rules ---
        elif intent.intent_class == "Availability":
            if error_ratio > 0.5:
                findings.append(f"CRITICAL: {error_ratio:.0%} failure rate — service likely down.")
                severity = "CRITICAL"
                confidence = 0.95
            elif error_ratio > 0.2:
                findings.append(f"WARNING: {error_ratio:.0%} failure rate — service degraded.")
                severity = "HIGH"
                confidence = 0.85

    # --- Universal high-error-ratio rule ---
    if error_ratio > 0.5 and SEVERITY_RANK.get(severity, 1) < 4:
        findings.append(f"SYSTEM: {error_ratio:.0%} of logs indicate failures.")
        severity = "CRITICAL"
        confidence = max(confidence, 0.9)

    # Decide if rule-based analysis is confident enough to skip LLM
    if SEVERITY_RANK.get(severity, 1) >= 3 and confidence >= 0.9:
        skip_llm = True

    return {
        "findings": findings,
        "anomalies": anomalies,
        "severity": severity,
        "confidence": confidence,
        "skip_llm": skip_llm,
    }


# ---------------------------------------------------------------------------
# LLM batch analysis
# ---------------------------------------------------------------------------

def analyze_batch_with_llm(
    batch: List[NormalizedLog],
    intent: IntentObject,
    metrics: Dict[str, Any],
    rule_findings: List[str],
    provider: str,
    model: str,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
) -> Dict[str, Any]:
    """Analyze a batch of logs with LLM, informed by rule-based pre-analysis."""
    adapter = AIAdapter(provider=provider, model=model, api_key=api_key, base_url=base_url)

    # Format log sample — increased from 10 to 30 for better representation
    log_sample = "\n".join([
        f"[{l.timestamp}] {l.level} | IP={l.source_ip} | User={l.user} | Service={l.service} | Msg: {l.message}"
        for l in batch[:30]
    ])

    # Build pre-analysis section
    pre_analysis = "\n".join(f"  - {f}" for f in rule_findings) if rule_findings else "  - No rule-based alerts triggered."

    prompt = f"""
    Intent Class: {intent.intent_class}
    User Prompt: {intent.raw_prompt}

    === Pre-Computed Metrics ===
    - Total Sub-logs: {metrics.get('total_records', 0)}
    - Filtered Sub-logs: {metrics.get('filtered_records', 0)}
    - Error Sub-logs: {metrics.get('error_count', 0)}
    - Warning Sub-logs: {metrics.get('warning_count', 0)}
    - Unique Source IPs: {metrics.get('unique_ips_count', 0)}
    - Top Source IPs (IP, count): {json.dumps(metrics.get('top_ips', []))}
    - Level Distribution: {json.dumps(metrics.get('level_distribution', {}))}
    - User Distribution: {json.dumps(metrics.get('user_distribution', {}))}
    - Services: {json.dumps(metrics.get('services', {}))}

    === Rule-Based Pre-Analysis ===
{pre_analysis}

    === Sub-log Records Sample ({min(len(batch), 30)} of {len(batch)} in this batch) ===
    {log_sample}
    """

    response = adapter.generate(prompt=prompt, system_instruction=SYSTEM_INSTRUCTION, temperature=0.2)
    return extract_json(response)


@app.post("/analyze-metrics", response_model=AnalysisResult)
async def analyze_metrics(request: AnalysisRequest):
    logger.info(f"Analyzing metrics and logs. Intent Class={request.intent.intent_class}")

    provider = request.provider or get_config("DEFAULT_PROVIDER", "ollama")
    model = request.model or get_config("DEFAULT_MODEL", "llama3")

    # No logs → nothing to analyze
    if not request.logs:
        return AnalysisResult(
            anomalies=[],
            trend="stable",
            severity="LOW",
            confidence_score=1.0,
            findings=["No relevant log entries matching the filter criteria were found."]
        )

    # --- Step 1: Rule-based analysis (fast, deterministic) ---
    rule_result = run_rule_engine(request.intent, request.metrics, request.logs)
    rule_findings = rule_result["findings"]
    rule_anomalies = rule_result["anomalies"]
    rule_severity = rule_result["severity"]
    rule_confidence = rule_result["confidence"]

    logger.info(f"Rule engine: severity={rule_severity}, confidence={rule_confidence}, "
                f"findings={len(rule_findings)}, skip_llm={rule_result['skip_llm']}")

    # --- Step 2: Skip LLM if rules are confident ---
    if rule_result["skip_llm"]:
        logger.info("Rule-based analysis is high-confidence. Skipping LLM for speed.")
        trend = "degrading" if SEVERITY_RANK.get(rule_severity, 1) >= 3 else "stable"
        return AnalysisResult(
            anomalies=rule_anomalies,
            trend=trend,
            severity=rule_severity,
            confidence_score=round(rule_confidence, 2),
            findings=rule_findings
        )

    # --- Step 3: LLM analysis with rule context ---
    batch_size = 50
    batches = [request.logs[i:i + batch_size] for i in range(0, len(request.logs), batch_size)]

    try:
        results = []
        # Cap at 2 parallel workers for Ollama (reduce contention on small instances)
        max_workers = min(len(batches), 2)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_batch = {
                executor.submit(
                    analyze_batch_with_llm, batch, request.intent, request.metrics,
                    rule_findings, provider, model, request.api_key, request.api_base_url
                ): i
                for i, batch in enumerate(batches[:2])  # Cap at 2 sub-agents
            }
            for future in concurrent.futures.as_completed(future_to_batch):
                try:
                    data = future.result()
                    results.append(data)
                except Exception as ex:
                    logger.error(f"Sub-agent batch analysis failed: {ex}")

        # Fallback to rule-based if LLM fails
        if not results:
            trend = "degrading" if SEVERITY_RANK.get(rule_severity, 1) >= 3 else "stable"
            return AnalysisResult(
                anomalies=rule_anomalies,
                trend=trend,
                severity=rule_severity,
                confidence_score=round(rule_confidence, 2),
                findings=rule_findings if rule_findings else ["Rule-based analysis did not detect any systemic anomalies."]
            )

        # --- Step 4: Merge rule + LLM results ---
        all_anomalies = list(rule_anomalies)
        all_findings = list(rule_findings)
        trends = []
        severities = [rule_severity]
        confidence_scores = [rule_confidence]

        for r in results:
            all_anomalies.extend(r.get("anomalies", []))
            all_findings.extend(r.get("findings", []))
            trends.append(r.get("trend", "stable"))
            severities.append(r.get("severity", "LOW"))
            confidence_scores.append(r.get("confidence_score", 0.5))

        # Consolidated metrics — rule-based severity acts as a floor
        consolidated_trend = max(set(trends), key=trends.count) if trends else "stable"
        if SEVERITY_RANK.get(rule_severity, 1) >= 3:
            consolidated_trend = "degrading"

        highest_severity = max(severities, key=lambda s: SEVERITY_RANK.get(s, 1))
        avg_confidence = sum(confidence_scores) / len(confidence_scores)

        # Deduplicate findings
        seen_findings = set()
        unique_findings = []
        for f in all_findings:
            if f not in seen_findings:
                seen_findings.add(f)
                unique_findings.append(f)

        return AnalysisResult(
            anomalies=all_anomalies,
            trend=consolidated_trend,
            severity=highest_severity,
            confidence_score=round(avg_confidence, 2),
            findings=unique_findings
        )

    except Exception as e:
        logger.error(f"Error in analysis agent: {e}")
        trend = "degrading" if SEVERITY_RANK.get(rule_severity, 1) >= 3 else "stable"
        return AnalysisResult(
            anomalies=rule_anomalies,
            trend=trend,
            severity=rule_severity,
            confidence_score=round(max(rule_confidence, 0.6), 2),
            findings=rule_findings if rule_findings else [f"Analysis pipeline error: {e}"]
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
