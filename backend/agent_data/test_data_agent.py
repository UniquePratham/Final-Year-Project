import os
import sys
import pytest
from fastapi.testclient import TestClient

# Adjust path to find backend and modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.agent_data.main import app

client = TestClient(app)

def test_process_data_syslog_success():
    intent_payload = {
        "intent_class": "Security",
        "entities": {
            "ip_address": "192.168.1.105",
            "user": None,
            "resource": None
        },
        "conditions": {
            "threshold": 3,
            "time_window": None
        },
        "raw_prompt": "Detect logins from 192.168.1.105"
    }
    
    # 2 syslog lines: one matches IP, one doesn't
    syslog_raw = (
        "Jun 12 15:45:20 myhost sshd[1234]: Failed password for invalid user admin from 192.168.1.105 port 54322\n"
        "Jun 12 15:46:10 myhost sshd[1234]: Accepted publickey for user admin from 192.168.1.10 port 54322\n"
    )
    
    payload = {
        "intent": intent_payload,
        "logs_raw": syslog_raw,
        "log_format": "Syslog"
    }
    
    response = client.post("/process-data", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    # Should only return the matching line
    assert len(data["logs_normalized"]) == 1
    assert data["logs_normalized"][0]["source_ip"] == "192.168.1.105"
    assert data["metrics"]["total_records"] == 2
    assert data["metrics"]["filtered_records"] == 1
    assert data["metrics"]["error_count"] == 1

def test_process_data_json_success():
    intent_payload = {
        "intent_class": "Performance",
        "entities": {},
        "conditions": {},
        "raw_prompt": "Detect performance warnings"
    }
    
    json_raw = (
        '{"timestamp": "2026-06-12T15:45:20Z", "level": "WARNING", "message": "High CPU utilization", "service": "api"}\n'
        '{"timestamp": "2026-06-12T15:46:10Z", "level": "INFO", "message": "Service normal", "service": "api"}\n'
    )
    
    payload = {
        "intent": intent_payload,
        "logs_raw": json_raw,
        "log_format": "JSON"
    }
    
    response = client.post("/process-data", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["logs_normalized"]) == 2
    assert data["metrics"]["warning_count"] == 1
    assert data["metrics"]["total_records"] == 2

def test_process_data_timezone_and_null_filters():
    intent_payload = {
        "intent_class": "Security",
        "entities": {
            "ip_address": "null",
            "user": "None",
            "resource": ""
        },
        "conditions": {
            "threshold": "null",
            "time_window": None
        },
        "raw_prompt": "Show all logs"
    }

    json_raw = (
        '{"timestamp": "13/Jun/2026:00:20:18 +0000", "level": "INFO", "message": "hello", "source_ip": "192.168.1.10"}\n'
    )

    payload = {
        "intent": intent_payload,
        "logs_raw": json_raw,
        "log_format": "JSON"
    }

    response = client.post("/process-data", json=payload)
    assert response.status_code == 200
    data = response.json()
    # With null-equivalent filters cleared, all logs should pass through
    assert len(data["logs_normalized"]) == 1
    assert data["metrics"]["total_records"] == 1


def test_process_data_windows_event():
    intent_payload = {
        "intent_class": "Security",
        "entities": {},
        "conditions": {},
        "raw_prompt": "Show all logs"
    }
    
    # Windows event log format: YYYY-MM-DD HH:MM:SS
    windows_raw = (
        "2026-06-13 22:47:09 web-lb-02 Security EventID=4625 Level=WARN Message='An account failed to log on'\n"
        "2026-06-13 22:47:10 web-lb-02 Security EventID=4624 Level=INFO Message='An account was successfully logged on'\n"
    )
    
    payload = {
        "intent": intent_payload,
        "logs_raw": windows_raw,
        "log_format": "Windows Event Logs"
    }
    
    response = client.post("/process-data", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["logs_normalized"]) == 2
    assert data["metrics"]["total_records"] == 2
    # Verify the levels are detected correctly
    assert data["logs_normalized"][0]["level"] == "ERROR"  # EventID 4625 maps to ERROR
    assert data["logs_normalized"][1]["level"] == "INFO"


def test_process_data_nginx():
    intent_payload = {
        "intent_class": "Performance",
        "entities": {},
        "conditions": {},
        "raw_prompt": "Show web server logs"
    }
    
    nginx_raw = (
        '192.168.1.50 - - [13/Jun/2026:22:47:09 +0000] "GET /api/v1/users HTTP/1.1" 200 452 "-" "Mozilla/5.0"\n'
        '192.168.1.51 - - [13/Jun/2026:22:47:10 +0000] "POST /api/v1/auth HTTP/1.1" 500 128 "-" "Mozilla/5.0"\n'
    )
    
    payload = {
        "intent": intent_payload,
        "logs_raw": nginx_raw,
        "log_format": "Nginx"
    }
    
    response = client.post("/process-data", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["logs_normalized"]) == 2
    assert data["metrics"]["total_records"] == 2
    assert data["logs_normalized"][0]["level"] == "INFO"
    assert data["logs_normalized"][0]["source_ip"] == "192.168.1.50"
    assert data["logs_normalized"][1]["level"] == "ERROR"  # status 500
    assert data["logs_normalized"][1]["source_ip"] == "192.168.1.51"


def test_process_data_auto_detect():
    intent_payload = {
        "intent_class": "Security",
        "entities": {},
        "conditions": {},
        "raw_prompt": "Show all logs"
    }
    
    # We pass "Syslog" format hint but input Nginx logs, it should auto-detect and parse as Nginx
    nginx_raw = (
        '192.168.1.50 - - [13/Jun/2026:22:47:09 +0000] "GET /api/v1/users HTTP/1.1" 200 452 "-" "Mozilla/5.0"\n'
    )
    
    payload = {
        "intent": intent_payload,
        "logs_raw": nginx_raw,
        "log_format": "Syslog"  # Wrong hint, should auto-detect Nginx
    }
    
    response = client.post("/process-data", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["logs_normalized"]) == 1
    assert data["logs_normalized"][0]["service"] == "nginx"


def test_process_data_csv_dump():
    intent_payload = {
        "intent_class": "Security",
        "entities": {},
        "conditions": {},
        "raw_prompt": "Show all logs"
    }
    
    csv_raw = (
        'Generated_Log_Line\n'
        '"""2026-06-13 22:47:09 web-lb-02 Security EventID=4625 Level=WARN Msg=Failed password for root from 185.220.101.44\\n'
        '2026-06-13 22:47:09 auth-svc-win Security EventID=4625 Level=WARN Msg=Failed password for admin from 91.200.12.33"""\n'
    )
    
    payload = {
        "intent": intent_payload,
        "logs_raw": csv_raw,
        "log_format": "CSV"
    }
    
    response = client.post("/process-data", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert len(data["logs_normalized"]) == 2
    assert data["metrics"]["total_records"] == 2
    assert data["logs_normalized"][0]["source_ip"] == "185.220.101.44"
    assert data["logs_normalized"][1]["source_ip"] == "91.200.12.33"


def test_enriched_metrics():
    """Verify level_distribution and user_distribution are computed."""
    intent_payload = {
        "intent_class": "Security",
        "entities": {},
        "conditions": {},
        "raw_prompt": "Show all logs"
    }

    syslog_raw = (
        "Jun 12 15:45:20 myhost sshd[1234]: Failed password for root from 192.168.1.105 port 54322\n"
        "Jun 12 15:45:21 myhost sshd[1234]: Failed password for admin from 192.168.1.105 port 54323\n"
        "Jun 12 15:45:22 myhost sshd[1234]: Accepted publickey for user ubuntu from 10.0.0.1 port 54324\n"
    )

    payload = {
        "intent": intent_payload,
        "logs_raw": syslog_raw,
        "log_format": "Syslog"
    }

    response = client.post("/process-data", json=payload)
    assert response.status_code == 200
    data = response.json()

    metrics = data["metrics"]
    assert "level_distribution" in metrics
    assert "user_distribution" in metrics
    assert metrics["level_distribution"]["ERROR"] == 2
    assert metrics["level_distribution"]["INFO"] == 1
    assert metrics["user_distribution"]["root"] == 1
    assert metrics["user_distribution"]["admin"] == 1


def test_brute_force_scenario_metrics():
    """Simulate a brute-force attack — verify error count and top_ips detect concentration."""
    intent_payload = {
        "intent_class": "Security",
        "entities": {},
        "conditions": {"threshold": 5},
        "raw_prompt": "Detect brute force"
    }

    # 10 failed login lines from the same IP
    lines = []
    for i in range(10):
        lines.append(f"Jun 12 15:45:{20+i:02d} myhost sshd[1234]: Failed password for root from 185.220.101.44 port {50000+i}")
    syslog_raw = "\n".join(lines)

    payload = {
        "intent": intent_payload,
        "logs_raw": syslog_raw,
        "log_format": "Syslog"
    }

    response = client.post("/process-data", json=payload)
    assert response.status_code == 200
    data = response.json()

    metrics = data["metrics"]
    assert metrics["error_count"] == 10
    assert metrics["total_records"] == 10
    assert len(metrics["top_ips"]) >= 1
    assert metrics["top_ips"][0][0] == "185.220.101.44"
    assert metrics["top_ips"][0][1] == 10
    assert metrics["level_distribution"]["ERROR"] == 10


def test_historical_time_window_filtering():
    """Verify that historical logs with past timestamps are not filtered out by time_window

    because the reference cutoff is calculated relative to the latest log in the batch.
    """
    intent_payload = {
        "intent_class": "Security",
        "entities": {},
        "conditions": {"time_window": "5m"},
        "raw_prompt": "Detect brute force in last 5m"
    }

    # Logs from 2020:
    # 2020-05-01 12:00:00 is the latest log.
    # 2020-05-01 11:59:00 is within 5 minutes.
    # 2020-05-01 11:50:00 is outside 5 minutes.
    logs_raw = (
        "2020-05-01 11:50:00 host sshd[12]: Failed password for root from 1.1.1.1\n"
        "2020-05-01 11:59:00 host sshd[12]: Failed password for root from 1.1.1.1\n"
        "2020-05-01 12:00:00 host sshd[12]: Failed password for root from 1.1.1.1\n"
    )

    payload = {
        "intent": intent_payload,
        "logs_raw": logs_raw,
        "log_format": "Windows Event Logs"
    }

    response = client.post("/process-data", json=payload)
    assert response.status_code == 200
    data = response.json()

    # The 11:59:00 and 12:00:00 logs should pass, but 11:50:00 should be filtered
    assert len(data["logs_normalized"]) == 2

