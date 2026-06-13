# Sentinel Forge Qwen 1.5B (8-Bit Quantized)

**Sentinel Forge Qwen 1.5B** is a custom, SFT fine-tuned log intelligence model based on `Qwen2.5-Coder-1.5B-Instruct`. It is specifically optimized to drive the 5-Agent security log analysis pipeline of the **Sentinel Forge** orchestration environment with **100% JSON compliance** and **zero rate limits**.

---

## 🚀 Key Capabilities

1. **Intent Extraction**: Parses conversational English requests into query filters, entities, and conditions matching the Intent Schema.
2. **Log & Metrics Analysis**: Processes log streams (Syslog, SSH, Nginx, PostgreSQL, etc.) and metrics to identify anomalies, trends, findings, and calculate overall threat severity.
3. **Security Report Generation**: Generates executive markdown reports and structured health statuses from raw threat findings.
4. **Mitigation Playbook Actions**: Suggests actionable, low-risk shell/CLI commands (e.g. `iptables` rules, service reloads) based on incident analysis.

---

## 🛠️ Usage in Ollama

### Run directly via command line:
```bash
ollama run UniquePratham/sentinel-forge-qwen
```

### Prompt Template (ChatML Format)
This model uses the **ChatML** template format. To ensure strict JSON outputs, feed requests using this sequence:

```
<|im_start|>system
You are the Intent Agent for Sentinel Forge: AI Log Analyzer. Transform the user prompt into structured JSON matching the Intent schema. Respond ONLY with raw JSON.<|im_end|>
<|im_start|>user
Check if there are any brute force attacks on the ssh daemon from 192.168.1.50 in the last 15m<|im_end|>
<|im_start|>assistant
```

---

## 📋 Schema Structures

### 1. Intent Schema
Returns user queries mapped to target configurations:
```json
{
  "intent_class": "Security", 
  "entities": {
    "ip_address": "192.168.1.50",
    "user": null,
    "resource": "ssh daemon"
  },
  "conditions": {
    "threshold": null,
    "time_window": "15m"
  },
  "raw_prompt": "..."
}
```

### 2. Analysis Schema
Outputs anomalies, trends, and threat severity ratings:
```json
{
  "anomalies": [
    {
      "timestamp": "2026-06-13T00:20:19",
      "metric": "Failed SSH attempts count: 3",
      "details": "Brute force signature matched from host 192.168.1.50 on user admin"
    }
  ],
  "trend": "Credential attacks targeting sshd from 192.168.1.50 spiking in 4 seconds",
  "severity": "HIGH",
  "confidence_score": 0.95,
  "findings": [
    "Brute force targeting account admin",
    "Attacker IP 192.168.1.50 should be blocked via firewall"
  ]
}
```

### 3. Final Report Schema
Builds summaries and maps affected server resources:
```json
{
  "status": "Bad",
  "summary": "### Executive Summary\n\nSecurity analysis confirms a `HIGH` severity event...",
  "recommendations": "1. Restrict external firewall routing rules for affected networks...",
  "affected_resources": ["ssh daemon"]
}
```

### 4. Response Mitigation Schema
Generates mitigation actions containing specific bash scripts:
```json
{
  "mitigation_actions": [
    {
      "action_type": "Block IP Address",
      "command": "sudo iptables -A INPUT -s 192.168.1.50 -j DROP",
      "description": "Add local firewall DROP rule to restrict incoming connections from attacker host 192.168.1.50 immediately.",
      "target": "192.168.1.50",
      "status": "PENDING"
    }
  ],
  "alert_triggered": true,
  "response_summary": "Mitigation playbook activated: Blocked IP 192.168.1.50."
}
```

---

## ⚡ Recommended Ollama Settings (Modelfile)
```dockerfile
FROM ./sentinel-forge-qwen.gguf
PARAMETER num_ctx 4096
PARAMETER temperature 0.2
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
```
