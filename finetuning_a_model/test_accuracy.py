import os
import json
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

# Configurations
MODEL_PATH = "merged_model"
print(f"Loading merged model from: {MODEL_PATH}...")
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}")

# Load model and tokenizer
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH, trust_remote_code=True)
model = AutoModelForCausalLM.from_pretrained(
    MODEL_PATH,
    torch_dtype=torch.float16,
    device_map="auto" if device == "cuda" else None,
    trust_remote_code=True
)

# Test cases representing the 4 pipeline agents
TEST_CASES = [
    {
        "agent": "Intent Agent",
        "system_prompt": "You are the Intent Agent for Sentinel Forge: AI Log Analyzer. Transform the user prompt into structured JSON matching the Intent schema. Respond ONLY with raw JSON.",
        "user_prompt": "Check if there are any brute force attacks on the ssh daemon from 192.168.1.50 in the last 15m",
        "expected_keys": ["intent_class", "entities", "conditions"],
        "validate_values": lambda data: data.get("intent_class") == "Security" and data.get("entities", {}).get("ip_address") == "192.168.1.50"
    },
    {
        "agent": "Analysis Agent",
        "system_prompt": "You are the Analysis Agent for Sentinel Forge. Evaluate log metrics and normalized logs to extract structured anomalies, trends, findings, and severity rating. Respond ONLY with valid JSON matching the Analysis schema.",
        "user_prompt": 'Intent: Security\nMetrics: {"total_records": 3, "filtered_records": 3, "error_count": 1, "warning_count": 2}\nLogs: [{"timestamp": "2026-06-13T00:20:15", "level": "WARN", "source_ip": "192.168.1.50", "user": "admin", "service": "sshd", "message": "Failed password for admin from 192.168.1.50 port 51221 ssh2"}, {"timestamp": "2026-06-13T00:20:17", "level": "WARN", "source_ip": "192.168.1.50", "user": "admin", "service": "sshd", "message": "Failed password for admin from 192.168.1.50 port 51224 ssh2"}, {"timestamp": "2026-06-13T00:20:19", "level": "CRITICAL", "source_ip": "192.168.1.50", "user": "admin", "service": "sshd", "message": "Multiple authentication failures from IP 192.168.1.50 - user account locked"}]',
        "expected_keys": ["anomalies", "trend", "severity", "confidence_score", "findings"],
        "validate_values": lambda data: data.get("severity") in ["HIGH", "CRITICAL"] and len(data.get("anomalies", [])) > 0
    },
    {
        "agent": "Report Agent",
        "system_prompt": "You are the Report Agent for Sentinel Forge. Generate an executive security report markdown summary, overall health status, and recommendations based on the analysis. Respond ONLY with valid JSON matching the FinalReport schema.",
        "user_prompt": 'Analysis Result: {"anomalies": [{"timestamp": "2026-06-13T00:20:19", "metric": "Activity count", "details": "Threshold exceeded"}], "trend": "Authentication failures mounting rapidly on sshd", "severity": "HIGH", "confidence_score": 0.95, "findings": ["Identified security threat from IP address 192.168.1.50", "Service state degraded due to resource threshold violations"]}',
        "expected_keys": ["status", "summary", "recommendations", "affected_resources"],
        "validate_values": lambda data: data.get("status") == "Bad" and "recommendations" in data
    },
    {
        "agent": "Response Agent",
        "system_prompt": "You are the Response Agent for Sentinel Forge. Generate specific, actionable mitigation CLI commands and playbooks based on the executive report. Respond ONLY with valid JSON matching the ResponseObject schema.",
        "user_prompt": 'Final Report: {"status": "Bad", "summary": "### Critical Threat Alert\\n\\nActive brute force scanning identified targeting service sshd from source host 192.168.1.50.", "recommendations": "1. Immediately block the attacker IP address 192.168.1.50.\\n2. Hard restart sshd daemon.", "affected_resources": ["sshd"]}',
        "expected_keys": ["mitigation_actions", "alert_triggered", "response_summary"],
        "validate_values": lambda data: data.get("alert_triggered") is True and len(data.get("mitigation_actions", [])) > 0
    }
]

print("\n" + "="*50)
print("STARTING DUAL EVALUATION (ACCURACY & JSON SCHEMA VALIDITY)")
print("="*50)

passed_tests = 0

for i, test in enumerate(TEST_CASES, 1):
    print(f"\nTest #{i}: {test['agent']}")
    print(f"Prompt: {test['user_prompt']}")
    
    # Format according to chat template
    messages = [
        {"role": "system", "content": test["system_prompt"]},
        {"role": "user", "content": test["user_prompt"]}
    ]
    text = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    
    # Run inference
    inputs = tokenizer(text, return_tensors="pt").to(device)
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=512,
            do_sample=False,  # Greedy decoding for consistency
            pad_token_id=tokenizer.eos_token_id
        )
    
    # Decode response
    generated_text = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).strip()
    print(f"Model Output:\n{generated_text}")
    
    # Validation 1: JSON Parsing
    try:
        parsed_json = json.loads(generated_text)
        print("[OK] JSON parsing: SUCCESS")
    except json.JSONDecodeError as e:
        print(f"[FAIL] JSON parsing: FAILED ({e})")
        continue
        
    # Validation 2: Keys verification
    missing_keys = [k for k in test["expected_keys"] if k not in parsed_json]
    if not missing_keys:
        print("[OK] Schema matching: PASS")
    else:
        print(f"[FAIL] Schema matching: FAILED (missing keys: {missing_keys})")
        continue
        
    # Validation 3: Value semantics verification
    if test["validate_values"](parsed_json):
        print("[OK] Value semantics: PASS")
        passed_tests += 1
    else:
        print("[FAIL] Value semantics: FAILED (semantic mismatch)")

print("\n" + "="*50)
print(f"EVALUATION OVERVIEW: {passed_tests}/{len(TEST_CASES)} PASSED")
print("="*50)
