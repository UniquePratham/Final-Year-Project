import os
import sys
import re
import csv
import json
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Adjust Python Path to find backend shared modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from backend.shared.types import IntentObject, NormalizedLog
from backend.shared.utils import get_logger

logger = get_logger("DataAgent")

app = FastAPI(title="Sentinel Forge - Data Agent Service")

class DataProcessRequest(BaseModel):
    intent: IntentObject
    logs_raw: str
    log_format: str = "Syslog"  # Syslog, JSON, XML, CSV, TXT

class DataProcessResponse(BaseModel):
    logs_normalized: List[NormalizedLog]
    metrics: Dict[str, Any]

# Regex for Syslog parsing (matches common RFC 3164 / 5424 timestamps and patterns)
SYSLOG_REGEX = re.compile(
    r'^(?P<timestamp>\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2}|\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?)\s+'
    r'(?P<host>[^\s]+)\s+'
    r'(?:(?P<service>[a-zA-Z0-9_\-\./]+)(?:\[(?P<pid>\d+)\])?:?\s+)?'
    r'(?P<message>.*)$'
)

# Regex to detect IP addresses
IP_REGEX = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')

def parse_syslog(raw_data: str) -> List[NormalizedLog]:
    normalized = []
    lines = raw_data.strip().splitlines()
    
    for line in lines:
        if not line.strip():
            continue
        match = SYSLOG_REGEX.match(line)
        if match:
            gd = match.groupdict()
            # Timestamp normalization
            ts_str = gd["timestamp"]
            ts = parse_timestamp(ts_str)
            
            # Detect source IP in message or host
            message = gd["message"]
            host = gd["host"]
            source_ip = None
            ip_match = IP_REGEX.search(message) or IP_REGEX.search(host)
            if ip_match:
                source_ip = ip_match.group(0)
                
            # Detect user if present in message (simple heuristic)
            user = None
            user_match = re.search(r'(?:user|user=|for)\s+([a-zA-Z0-9_\-\.]+)', message, re.IGNORECASE)
            if user_match:
                user = user_match.group(1)
                
            normalized.append(NormalizedLog(
                timestamp=ts,
                level="INFO" if "fail" not in message.lower() and "error" not in message.lower() else "ERROR",
                source_ip=source_ip,
                user=user,
                service=gd.get("service") or "syslog",
                message=message,
                raw=line
            ))
        else:
            # Fallback for unparseable syslog line
            normalized.append(NormalizedLog(
                timestamp=datetime.utcnow(),
                level="INFO",
                message=line,
                raw=line
            ))
    return normalized

def parse_json_logs(raw_data: str) -> List[NormalizedLog]:
    normalized = []
    lines = raw_data.strip().splitlines()
    for line in lines:
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            # Find common timestamp keys
            ts_val = data.get("timestamp") or data.get("time") or data.get("@timestamp")
            ts = parse_timestamp(str(ts_val)) if ts_val else datetime.utcnow()
            
            normalized.append(NormalizedLog(
                timestamp=ts,
                level=data.get("level") or data.get("status") or "INFO",
                source_ip=data.get("source_ip") or data.get("ip") or data.get("client_ip"),
                user=data.get("user") or data.get("username"),
                service=data.get("service") or data.get("app"),
                message=data.get("message") or data.get("msg") or str(data),
                raw=line,
                metadata=data
            ))
        except Exception:
            normalized.append(NormalizedLog(
                timestamp=datetime.utcnow(),
                level="INFO",
                message=line,
                raw=line
            ))
    return normalized

def parse_csv_logs(raw_data: str) -> List[NormalizedLog]:
    normalized = []
    reader = csv.DictReader(raw_data.strip().splitlines())
    for row in reader:
        # Find timestamp
        ts_val = row.get("timestamp") or row.get("time") or row.get("date")
        ts = parse_timestamp(str(ts_val)) if ts_val else datetime.utcnow()
        
        # Build message from all columns if message column doesn't exist
        message = row.get("message") or row.get("msg") or ", ".join([f"{k}={v}" for k, v in row.items()])
        
        normalized.append(NormalizedLog(
            timestamp=ts,
            level=row.get("level") or "INFO",
            source_ip=row.get("source_ip") or row.get("ip"),
            user=row.get("user") or row.get("username"),
            service=row.get("service") or "csv_import",
            message=message,
            raw=json.dumps(row)
        ))
    return normalized

def parse_xml_logs(raw_data: str) -> List[NormalizedLog]:
    normalized = []
    try:
        root = ET.fromstring(f"<root>{raw_data}</root>")
        for log_entry in root:
            data = {child.tag: child.text for child in log_entry}
            ts_val = data.get("timestamp") or data.get("time")
            ts = parse_timestamp(str(ts_val)) if ts_val else datetime.utcnow()
            normalized.append(NormalizedLog(
                timestamp=ts,
                level=data.get("level") or "INFO",
                source_ip=data.get("source_ip") or data.get("ip"),
                user=data.get("user") or data.get("username"),
                service=data.get("service") or log_entry.tag,
                message=data.get("message") or data.get("msg") or str(data),
                raw=ET.tostring(log_entry, encoding="utf-8").decode("utf-8")
            ))
    except Exception as e:
        logger.warning(f"XML parsing failed: {e}. Falling back to TXT line-by-line.")
        return parse_txt_logs(raw_data)
    return normalized

def parse_txt_logs(raw_data: str) -> List[NormalizedLog]:
    normalized = []
    lines = raw_data.strip().splitlines()
    for line in lines:
        if not line.strip():
            continue
        normalized.append(NormalizedLog(
            timestamp=datetime.utcnow(),
            level="INFO",
            message=line,
            raw=line
        ))
    return normalized

def parse_timestamp(ts_str: str) -> datetime:
    """Heuristic timestamp parser."""
    formats = [
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%d %H:%M:%S",
        "%b %d %H:%M:%S",
        "%d/%b/%Y:%H:%M:%S %z",
        "%Y-%m-%d"
    ]
    for fmt in formats:
        try:
            # Handle Syslog traditional (e.g., "Jun 12 15:45:20" - append current year)
            if fmt == "%b %d %H:%M:%S":
                parsed = datetime.strptime(ts_str, fmt)
                parsed = parsed.replace(year=datetime.utcnow().year)
            else:
                parsed = datetime.strptime(ts_str, fmt)
            
            if parsed.tzinfo is not None:
                parsed = parsed.astimezone(timezone.utc).replace(tzinfo=None)
            return parsed
        except Exception:
            continue
    # Fallback to current time if unparseable
    return datetime.utcnow()

def apply_filters(logs: List[NormalizedLog], intent: IntentObject) -> List[NormalizedLog]:
    filtered = []
    entities = intent.entities or {}
    conditions = intent.conditions or {}
    
    # Helper to clean string values
    def clean_val(v):
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            if s.lower() in ("null", "none", "undefined", ""):
                return None
            return s
        return v

    target_ip = clean_val(entities.get("ip_address"))
    target_user = clean_val(entities.get("user"))
    target_resource = clean_val(entities.get("resource"))
    time_window = clean_val(conditions.get("time_window"))
    
    cutoff_time = None
    if time_window:
        match = re.match(r'(\d+)([smhd])', str(time_window))
        if match:
            val, unit = int(match.group(1)), match.group(2)
            delta_map = {"s": "seconds", "m": "minutes", "h": "hours", "d": "days"}
            cutoff_time = datetime.utcnow() - timedelta(**{delta_map[unit]: val})

    for log in logs:
        # 1. Filter by cutoff time
        if cutoff_time and log.timestamp < cutoff_time:
            continue
            
        # 2. Filter by target IP
        if target_ip and log.source_ip != target_ip:
            continue
            
        # 3. Filter by User
        if target_user and log.user != target_user:
            continue
            
        # 4. Filter by resource/keyword
        if target_resource and target_resource.lower() not in log.message.lower() and target_resource.lower() not in log.service.lower():
            continue
            
        filtered.append(log)
    return filtered

def compute_metrics(all_logs: List[NormalizedLog], filtered_logs: List[NormalizedLog]) -> Dict[str, Any]:
    error_count = sum(1 for l in filtered_logs if l.level.upper() in ["ERROR", "CRITICAL", "FAIL", "FATAL"])
    warn_count = sum(1 for l in filtered_logs if l.level.upper() in ["WARN", "WARNING"])
    
    # Trace source IP distribution
    ips = {}
    for l in filtered_logs:
        if l.source_ip:
            ips[l.source_ip] = ips.get(l.source_ip, 0) + 1
            
    # Trace service distribution
    services = {}
    for l in filtered_logs:
        if l.service:
            services[l.service] = services.get(l.service, 0) + 1

    return {
        "total_records": len(all_logs),
        "filtered_records": len(filtered_logs),
        "error_count": error_count,
        "warning_count": warn_count,
        "unique_ips_count": len(ips),
        "top_ips": sorted(ips.items(), key=lambda x: x[1], reverse=True)[:5],
        "services": services
    }

@app.post("/process-data", response_model=DataProcessResponse)
async def process_data(request: DataProcessRequest):
    logger.info(f"Processing raw log data. Format={request.log_format}")
    
    fmt = request.log_format.upper()
    try:
        if fmt == "SYSLOG":
            all_logs = parse_syslog(request.logs_raw)
        elif fmt == "JSON":
            all_logs = parse_json_logs(request.logs_raw)
        elif fmt == "CSV":
            all_logs = parse_csv_logs(request.logs_raw)
        elif fmt == "XML":
            all_logs = parse_xml_logs(request.logs_raw)
        else:
            all_logs = parse_txt_logs(request.logs_raw)
            
        filtered_logs = apply_filters(all_logs, request.intent)
        metrics = compute_metrics(all_logs, filtered_logs)
        
        return DataProcessResponse(
            logs_normalized=filtered_logs,
            metrics=metrics
        )
    except Exception as e:
        logger.error(f"Error processing data in data agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
