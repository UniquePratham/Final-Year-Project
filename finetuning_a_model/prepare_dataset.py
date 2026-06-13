import json
import random
import os

# Define folders
os.makedirs("finetuning_a_model", exist_ok=True)
output_file = "finetuning_a_model/train_data.jsonl"

print("Starting dataset synthesis...")

# ----------------- INTENT AGENT DATAPOINTS -----------------
INTENT_CLASSES = ["Security", "Performance", "Availability", "Compliance", "Usage Analytics"]
IPS = ["192.168.1.50", "10.0.0.8", "185.220.101.44", "91.200.12.33", "203.0.113.15", "45.55.12.99", "172.16.4.8"]
USERS = ["admin", "root", "ubuntu", "postgres", "pratham", "db_backup", "test_user"]
RESOURCES = ["login portal", "ssh daemon", "database server", "Nginx web balancer", "auth-gateway", "API router", "firewall", "docker service"]
TIME_WINDOWS = ["5m", "15m", "1h", "24h", "7d"]

intent_datapoints = []

# Generate Intent Agent variations
for i in range(1500):
    intent_class = random.choice(INTENT_CLASSES)
    ip = random.choice(IPS) if random.random() > 0.4 else None
    user = random.choice(USERS) if random.random() > 0.4 else None
    resource = random.choice(RESOURCES) if random.random() > 0.3 else None
    time_window = random.choice(TIME_WINDOWS) if random.random() > 0.3 else None
    threshold = random.randint(3, 100) if random.random() > 0.5 else None
    
    # Generate templates for prompt
    templates = []
    if intent_class == "Security":
        templates = [
            f"Check if there are any brute force attacks on {resource or 'the server'}",
            f"Is there unauthorized access from {ip or 'suspicious IPs'} using account {user or 'admin'}?",
            f"Scan auth logs for privilege escalation attempts in the last {time_window or '24h'}",
            f"Detect malware indicators and SSH anomalies from IP {ip or '185.220.101.44'}"
        ]
    elif intent_class == "Performance":
        templates = [
            f"Find any CPU spikes or RAM exhaustion events on {resource or 'web host'}",
            f"Check if average request latency exceeded {threshold or 500}ms",
            f"Are there any slow database queries on {resource or 'db cluster'}?",
            f"Identify bandwidth load anomalies in the last {time_window or '1h'}"
        ]
    elif intent_class == "Availability":
        templates = [
            f"Did {resource or 'the service'} crash or go offline recently?",
            f"Check if database postgresql experienced connection dropouts",
            f"Are there service downtime errors in the last {time_window or '24h'}?",
            f"Show connection limits exceeded on {resource or 'auth-server'}"
        ]
    elif intent_class == "Compliance":
        templates = [
            f"Audit system logins and policy changes on {resource or 'gateway'}",
            f"Find compliance violations matching older TLS handshakes",
            f"Verify root security credentials access log lines",
            f"Check audit trails for modifications in the last {time_window or '7d'}"
        ]
    else: # Usage Analytics
        templates = [
            f"Analyze active sessions and user volumes for {user or 'root'}",
            f"Compute total transaction queries on {resource or 'web balancer'}",
            f"What was the traffic volume from country IP {ip or '192.168.1.50'}?",
            f"List top requested paths in Nginx during the past {time_window or '24h'}"
        ]
        
    prompt = random.choice(templates)
    
    # Target Intent JSON
    target_json = {
        "intent_class": intent_class,
        "entities": {
            "ip_address": ip,
            "user": user,
            "resource": resource
        },
        "conditions": {
            "threshold": threshold,
            "time_window": time_window
        },
        "raw_prompt": prompt
    }
    
    intent_datapoints.append({
        "messages": [
            {"role": "system", "content": "You are the Intent Agent for Sentinel Forge: AI Log Analyzer. Transform the user prompt into structured JSON matching the Intent schema. Respond ONLY with raw JSON."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": json.dumps(target_json)}
        ]
    })

# ----------------- ANALYSIS AGENT DATAPOINTS -----------------
analysis_datapoints = []

# Generate Analysis Agent variations
for i in range(1200):
    intent_class = random.choice(INTENT_CLASSES)
    ip = random.choice(IPS)
    user = random.choice(USERS)
    resource = random.choice(RESOURCES)
    
    # Construct normalized logs context
    if intent_class == "Security":
        logs = [
            {"timestamp": "2026-06-13T00:20:15", "level": "WARN", "source_ip": ip, "user": user, "service": "sshd", "message": f"Failed password for {user} from {ip} port 51221 ssh2"},
            {"timestamp": "2026-06-13T00:20:17", "level": "WARN", "source_ip": ip, "user": user, "service": "sshd", "message": f"Failed password for {user} from {ip} port 51224 ssh2"},
            {"timestamp": "2026-06-13T00:20:19", "level": "CRITICAL", "source_ip": ip, "user": user, "service": "sshd", "message": f"Multiple authentication failures from IP {ip} - user account locked"}
        ]
        anomalies = [{"timestamp": "2026-06-13T00:20:19", "metric": "Failed SSH attempts count: 3", "details": f"Brute force signature matched from host {ip} on user {user}"}]
        trend = f"Credential attacks targeting sshd from {ip} spiking in 4 seconds"
        severity = "HIGH"
        confidence = 0.95
        findings = [f"Brute force targeting account {user}", f"Attacker IP {ip} should be blocked via firewall"]
    elif intent_class == "Performance":
        logs = [
            {"timestamp": "2026-06-13T00:20:15", "level": "WARN", "source_ip": ip, "user": None, "service": "systemd", "message": "High CPU utilization load average: 10.50"},
            {"timestamp": "2026-06-13T00:20:20", "level": "WARN", "source_ip": ip, "user": None, "service": "systemd", "message": "RAM utilization at 96% - OOM killer active"}
        ]
        anomalies = [{"timestamp": "2026-06-13T00:20:20", "metric": "Resource limits", "details": "RAM exhausted on node host"}]
        trend = "Memory spike triggering scheduler latency alerts"
        severity = "HIGH"
        confidence = 0.90
        findings = ["OOM killer terminated standard docker threads", "Scale partition RAM or clean cached volumes"]
    else:
        logs = [
            {"timestamp": "2026-06-13T00:20:15", "level": "INFO", "source_ip": ip, "user": user, "service": "nginx", "message": "Connection established successfully"}
        ]
        anomalies = []
        trend = "System operates within healthy standard thresholds"
        severity = "LOW"
        confidence = 0.85
        findings = ["No severe operational incidents detected"]

    metrics = {
        "total_records": len(logs),
        "filtered_records": len(logs),
        "error_count": sum(1 for l in logs if l["level"] in ["ERROR", "CRITICAL"]),
        "warning_count": sum(1 for l in logs if l["level"] == "WARN")
    }

    prompt = f"Intent: {intent_class}\nMetrics: {json.dumps(metrics)}\nLogs: {json.dumps(logs)}"
    
    target_json = {
        "anomalies": anomalies,
        "trend": trend,
        "severity": severity,
        "confidence_score": confidence,
        "findings": findings
    }
    
    analysis_datapoints.append({
        "messages": [
            {"role": "system", "content": "You are the Analysis Agent for Sentinel Forge. Evaluate log metrics and normalized logs to extract structured anomalies, trends, findings, and severity rating. Respond ONLY with valid JSON matching the Analysis schema."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": json.dumps(target_json)}
        ]
    })

# ----------------- REPORT AGENT DATAPOINTS -----------------
report_datapoints = []

# Generate Report Agent variations
for i in range(1000):
    trend = random.choice([
        "Authentication failures mounting rapidly on sshd",
        "High CPU usage coupled with database lock contention",
        "DDoS request surge causing high latency on Nginx web gateway",
        "Multiple policy violation errors due to legacy TLS handshakes"
    ])
    severity = random.choice(["LOW", "MEDIUM", "HIGH", "CRITICAL"])
    finding_1 = f"Identified security threat from IP address {random.choice(IPS)}"
    finding_2 = f"Service state degraded due to resource threshold violations"
    resource = random.choice(RESOURCES)
    
    analysis_result = {
        "anomalies": [{"timestamp": "2026-06-13T00:20:19", "metric": "Activity count", "details": "Threshold exceeded"}],
        "trend": trend,
        "severity": severity,
        "confidence_score": 0.94,
        "findings": [finding_1, finding_2]
    }
    
    prompt = f"Analysis Result: {json.dumps(analysis_result)}"
    
    status = "Bad" if severity in ["HIGH", "CRITICAL"] else ("Warning" if severity == "MEDIUM" else "Good")
    summary = f"### Executive Summary\n\nSecurity analysis confirms a `{severity}` severity event matching `{trend}`. {finding_1}.\n\n### Findings\n- {finding_1}\n- {finding_2}"
    recommendations = f"1. Restrict external firewall routing rules for affected networks.\n2. Scale local container allocations on {resource}."
    
    target_json = {
        "status": status,
        "summary": summary,
        "recommendations": recommendations,
        "affected_resources": [resource]
    }
    
    report_datapoints.append({
        "messages": [
            {"role": "system", "content": "You are the Report Agent for Sentinel Forge. Generate an executive security report markdown summary, overall health status, and recommendations based on the analysis. Respond ONLY with valid JSON matching the FinalReport schema."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": json.dumps(target_json)}
        ]
    })

# ----------------- RESPONSE AGENT DATAPOINTS -----------------
response_datapoints = []

# Generate Response Agent variations
for i in range(1000):
    ip = random.choice(IPS)
    resource = random.choice(RESOURCES)
    severity = random.choice(["HIGH", "CRITICAL"])
    
    report_obj = {
        "status": "Bad",
        "summary": f"### Critical Threat Alert\n\nActive brute force scanning identified targeting service {resource} from source host {ip}.",
        "recommendations": f"1. Immediately block the attacker IP address {ip}.\n2. Hard restart docker daemon.",
        "affected_resources": [resource]
    }
    
    prompt = f"Final Report: {json.dumps(report_obj)}"
    
    mitigation_actions = [
        {
            "action_type": "Block IP Address",
            "command": f"sudo iptables -A INPUT -s {ip} -j DROP",
            "description": f"Add local firewall DROP rule to restrict incoming connections from attacker host {ip} immediately.",
            "target": ip,
            "status": "PENDING"
        },
        {
            "action_type": "Restart Service",
            "command": f"sudo systemctl restart {resource.replace(' ', '-')}",
            "description": f"Perform a hard service daemon reload to clear blocked sockets and threads on target {resource}.",
            "target": resource,
            "status": "PENDING"
        }
    ]
    
    target_json = {
        "mitigation_actions": mitigation_actions,
        "alert_triggered": True,
        "response_summary": f"Mitigation playbook activated: Blocked IP {ip} and restarted resource {resource}."
    }
    
    response_datapoints.append({
        "messages": [
            {"role": "system", "content": "You are the Response Agent for Sentinel Forge. Generate specific, actionable mitigation CLI commands and playbooks based on the executive report. Respond ONLY with valid JSON matching the ResponseObject schema."},
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": json.dumps(target_json)}
        ]
    })

# Mix all datasets
all_datapoints = intent_datapoints + analysis_datapoints + report_datapoints + response_datapoints
random.shuffle(all_datapoints)

print(f"Synthesized datasets details:")
print(f" - Intent datapoints: {len(intent_datapoints)}")
print(f" - Analysis datapoints: {len(analysis_datapoints)}")
print(f" - Report datapoints: {len(report_datapoints)}")
print(f" - Response datapoints: {len(response_datapoints)}")
print(f" - Total lines: {len(all_datapoints)}")

# Write to file
with open(output_file, "w", encoding="utf-8") as f:
    for item in all_datapoints:
        f.write(json.dumps(item) + "\n")

print(f"Dataset compiled and exported successfully to: {output_file}")
