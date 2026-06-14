import os
import sys
import re
import csv
import io
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
    log_format: str = "Syslog"

class DataProcessResponse(BaseModel):
    logs_normalized: List[NormalizedLog]
    metrics: Dict[str, Any]

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Universal syslog-family regex: handles BSD (Jun 13 22:47:09),
# ISO 8601 (2026-06-13T22:47:09Z), and Windows Event (2026-06-13 22:47:09).
SYSLOG_REGEX = re.compile(
    r'^(?P<timestamp>'
    r'\w{3}\s+\d+\s+\d{2}:\d{2}:\d{2}'                          # BSD:   Jun 13 22:47:09
    r'|\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})?'  # ISO / Windows Event
    r')\s+'
    r'(?P<host>[^\s]+)\s+'
    r'(?:(?P<service>[a-zA-Z0-9_\-\./]+)(?:\[(?P<pid>\d+)\])?:?\s+)?'
    r'(?P<message>.*)$'
)

# Nginx / Apache combined log format
NGINX_REGEX = re.compile(
    r'^(?P<source_ip>\d+\.\d+\.\d+\.\d+)\s+\S+\s+(?P<user>\S+)\s+'
    r'\[(?P<timestamp>[^\]]+)\]\s+'
    r'"(?P<method>\w+)\s+(?P<path>\S+)\s+[^"]*"\s+'
    r'(?P<status>\d+)\s+(?P<size>\d+)'
    r'(?:\s+"(?P<referrer>[^"]*)"\s+"(?P<agent>[^"]*)")?'
)

# IP address detector
IP_REGEX = re.compile(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b')

# ---------------------------------------------------------------------------
# Level detection
# ---------------------------------------------------------------------------

def detect_log_level(message: str) -> str:
    """Detect log severity from message content using keywords and event IDs."""
    msg_lower = message.lower()

    if any(kw in msg_lower for kw in ["critical", "fatal", "emergency", "panic"]):
        return "CRITICAL"

    if any(kw in msg_lower for kw in [
        "fail", "error", "denied", "unauthorized", "refused",
        "reject", "invalid", "blocked",
    ]):
        return "ERROR"

    # Windows Security failure EventIDs
    if re.search(r'eventid=(4625|4771|4776|529|530|531|532|533|534|535|536|537|539)', msg_lower):
        return "ERROR"

    if any(kw in msg_lower for kw in [
        "warn", "warning", "locked", "timeout", "retry",
        "deprecated", "throttle",
    ]):
        return "WARNING"

    # Explicit Level= field in structured logs
    level_match = re.search(r'level=([\w]+)', message, re.IGNORECASE)
    if level_match:
        lvl = level_match.group(1).upper()
        if lvl in ("WARN", "WARNING"):
            return "WARNING"
        if lvl in ("ERROR", "ERR", "FATAL", "CRITICAL", "CRIT"):
            return "ERROR"

    return "INFO"

# ---------------------------------------------------------------------------
# Timestamp parsing
# ---------------------------------------------------------------------------

TIMESTAMP_FORMATS = [
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S.%f%z",
    "%Y-%m-%d %H:%M:%S",
    "%b %d %H:%M:%S",
    "%d/%b/%Y:%H:%M:%S %z",
    "%Y-%m-%d",
]

def parse_timestamp(ts_str: str) -> datetime:
    """Heuristic timestamp parser supporting all common log timestamp formats."""
    for fmt in TIMESTAMP_FORMATS:
        try:
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
    return datetime.utcnow()

# ---------------------------------------------------------------------------
# Format auto-detection
# ---------------------------------------------------------------------------

def auto_detect_format(raw_data: str) -> str:
    """Sniff the first non-empty lines to determine log format."""
    lines = [l.strip() for l in raw_data.strip().splitlines()[:20] if l.strip()]
    if not lines:
        return "TXT"

    first = lines[0]

    # JSON: first line starts with { or [
    if first.startswith("{") or first.startswith("["):
        return "JSON"

    # XML: first line starts with <
    if first.startswith("<"):
        return "XML"

    # CSV: first line looks like a header row (no digits at start, or known column names)
    csv_header_names = (
        "generated_log_line", "log_line", "raw_log", "log_entry",
        "timestamp", "message", "msg", "time", "date", "raw",
    )
    first_lower = first.lower().replace(" ", "_").strip('"')
    if first_lower in csv_header_names:
        return "CSV"
    # Multi-column CSV header heuristic: comma-separated words, no timestamp pattern
    if "," in first and not re.match(r'^\d{4}-\d{2}-\d{2}', first) and not re.match(r'^\w{3}\s+\d+', first):
        tokens = [t.strip().strip('"').lower().replace(" ", "_") for t in first.split(",")]
        if any(t in csv_header_names for t in tokens):
            return "CSV"

    # Nginx / Apache combined log format: starts with an IP, then ` - `
    if NGINX_REGEX.match(first):
        return "NGINX"

    # Syslog-family (BSD, Windows Event, Linux Auth, Firewall, generic)
    if SYSLOG_REGEX.match(first):
        return "SYSLOG"

    return "TXT"

# ---------------------------------------------------------------------------
# Parsers
# ---------------------------------------------------------------------------

def parse_syslog(raw_data: str) -> List[NormalizedLog]:
    """Universal syslog-family parser. Handles BSD syslog, Windows Event,
    Linux Auth, Firewall, and any line matching TIMESTAMP HOST MESSAGE."""
    normalized: List[NormalizedLog] = []
    lines = raw_data.strip().splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = SYSLOG_REGEX.match(line)
        if match:
            gd = match.groupdict()
            ts = parse_timestamp(gd["timestamp"])
            message = gd["message"]
            host = gd["host"]

            # Extract source IP from message body
            source_ip = None
            ip_patterns = [
                r'\bIP=(\d+\.\d+\.\d+\.\d+)',
                r'\bSourceAddress=(\d+\.\d+\.\d+\.\d+)',
                r'Source\s+Address:\s*(\d+\.\d+\.\d+\.\d+)',
                r'Source\s+Network\s+Address:\s*(\d+\.\d+\.\d+\.\d+)'
            ]
            for pattern in ip_patterns:
                ip_match = re.search(pattern, message, re.IGNORECASE)
                if ip_match:
                    source_ip = ip_match.group(1)
                    break
            
            if not source_ip:
                ip_match = IP_REGEX.search(message) or IP_REGEX.search(host)
                if ip_match:
                    source_ip = ip_match.group(0)

            # Extract user from User=, AccountName=, TargetUserName=, Account Name: patterns
            user = None
            user_patterns = [
                r'\bUser=([a-zA-Z0-9_\-\.]+)',
                r'\bAccountName=([a-zA-Z0-9_\-\.]+)',
                r'\bTargetUserName=([a-zA-Z0-9_\-\.]+)',
                r'Account\s+Name:\s*([a-zA-Z0-9_\-\.]+)',
                r'Target\s+User\s+Name:\s*([a-zA-Z0-9_\-\.]+)',
                r'(?:user|for)\s+([a-zA-Z0-9_\-\.]+)'
            ]
            for pattern in user_patterns:
                user_match = re.search(pattern, message, re.IGNORECASE)
                if user_match:
                    user = user_match.group(1)
                    break

            # Detect service from the regex or from the message body
            service = gd.get("service") or "syslog"

            normalized.append(NormalizedLog(
                timestamp=ts,
                level=detect_log_level(message),
                source_ip=source_ip,
                user=user,
                service=service,
                message=message,
                raw=line
            ))
        else:
            # Fallback: still extract what we can from an unparseable line
            source_ip = None
            ip_patterns = [
                r'\bIP=(\d+\.\d+\.\d+\.\d+)',
                r'\bSourceAddress=(\d+\.\d+\.\d+\.\d+)',
                r'Source\s+Address:\s*(\d+\.\d+\.\d+\.\d+)',
                r'Source\s+Network\s+Address:\s*(\d+\.\d+\.\d+\.\d+)'
            ]
            for pattern in ip_patterns:
                ip_match = re.search(pattern, line, re.IGNORECASE)
                if ip_match:
                    source_ip = ip_match.group(1)
                    break
            if not source_ip:
                ip_match = IP_REGEX.search(line)
                if ip_match:
                    source_ip = ip_match.group(0)

            user = None
            user_patterns = [
                r'\bUser=([a-zA-Z0-9_\-\.]+)',
                r'\bAccountName=([a-zA-Z0-9_\-\.]+)',
                r'\bTargetUserName=([a-zA-Z0-9_\-\.]+)',
                r'Account\s+Name:\s*([a-zA-Z0-9_\-\.]+)',
                r'Target\s+User\s+Name:\s*([a-zA-Z0-9_\-\.]+)',
                r'(?:user|for)\s+([a-zA-Z0-9_\-\.]+)'
            ]
            for pattern in user_patterns:
                user_match = re.search(pattern, line, re.IGNORECASE)
                if user_match:
                    user = user_match.group(1)
                    break

            normalized.append(NormalizedLog(
                timestamp=datetime.utcnow(),
                level=detect_log_level(line),
                source_ip=source_ip,
                user=user,
                message=line,
                raw=line
            ))
    return normalized


def parse_nginx(raw_data: str) -> List[NormalizedLog]:
    """Parse Nginx / Apache combined log format."""
    normalized: List[NormalizedLog] = []
    lines = raw_data.strip().splitlines()

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = NGINX_REGEX.match(line)
        if match:
            gd = match.groupdict()
            ts = parse_timestamp(gd["timestamp"])
            status = int(gd.get("status", 0))
            method = gd.get("method", "")
            path = gd.get("path", "")
            user = gd.get("user")
            if user == "-":
                user = None

            # Determine level from HTTP status
            if status >= 500 or status in (401, 403):
                level = "ERROR"
            elif status >= 400:
                level = "WARNING"
            else:
                level = "INFO"

            message = f"{method} {path} -> {status} ({gd.get('size', 0)}B)"

            normalized.append(NormalizedLog(
                timestamp=ts,
                level=level,
                source_ip=gd.get("source_ip"),
                user=user,
                service="nginx",
                message=message,
                raw=line
            ))
        else:
            # Fallback to syslog parser for non-matching lines
            normalized.extend(parse_syslog(line))
    return normalized


def parse_json_logs(raw_data: str) -> List[NormalizedLog]:
    """Parse newline-delimited or array-wrapped JSON log entries."""
    normalized: List[NormalizedLog] = []
    
    # Try to load as a single JSON array first (e.g. pretty-printed JSON files)
    try:
        parsed = json.loads(raw_data.strip())
        if isinstance(parsed, list):
            entries = parsed
        else:
            entries = [parsed]
    except Exception:
        # Fallback to newline-delimited JSON
        entries = []
        lines = raw_data.strip().splitlines()
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                entries.append(json.loads(line))
            except Exception:
                # Add individual raw line as fallback text log
                normalized.append(NormalizedLog(
                    timestamp=datetime.utcnow(),
                    level=detect_log_level(line),
                    message=line,
                    raw=line
                ))

    # Check if entries wraps raw log dumps containing multi-line strings
    log_dump_headers = (
        "generated_log_line", "log_line", "log", "raw_log",
        "message", "msg", "log_entry", "raw",
    )
    is_log_dump = False
    dump_col = None
    if entries and isinstance(entries[0], dict):
        for col in log_dump_headers:
            if col in entries[0]:
                val = entries[0][col]
                if isinstance(val, str) and ("\n" in val or "\\n" in val):
                    is_log_dump = True
                    dump_col = col
                    break

    if is_log_dump:
        unwrapped: List[str] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            cell = entry.get(dump_col, "")
            if cell:
                cell_clean = cell.replace("\\n", "\n")
                for line in cell_clean.strip().splitlines():
                    line_clean = line.strip().strip('"').strip("'").strip()
                    if line_clean:
                        unwrapped.append(line_clean)
        if unwrapped:
            joined = "\n".join(unwrapped)
            inner_fmt = auto_detect_format(joined)
            if inner_fmt == "NGINX":
                return parse_nginx(joined)
            if inner_fmt == "JSON":
                return parse_txt_logs(joined)
            return parse_syslog(joined)
        return normalized

    # Process standard entries
    def get_any(d: dict, keys: List[str]) -> Optional[Any]:
        for k in keys:
            if k in d:
                return d[k]
        return None

    for data in entries:
        if not isinstance(data, dict):
            continue
        try:
            ts_val = get_any(data, ["timestamp", "time", "@timestamp", "Timestamp", "Time", "date", "Date"])
            ts = parse_timestamp(str(ts_val)) if ts_val else datetime.utcnow()

            message = get_any(data, ["message", "msg", "Message", "Msg", "log", "raw"]) or str(data)
            level = get_any(data, ["level", "status", "Level", "severity", "Severity"]) or detect_log_level(message)

            normalized.append(NormalizedLog(
                timestamp=ts,
                level=str(level),
                source_ip=get_any(data, ["source_ip", "ip", "client_ip", "clientIp", "SourceIP", "IP", "sourceAddress", "SourceAddress"]),
                user=get_any(data, ["user", "username", "userName", "User", "account", "AccountName"]),
                service=get_any(data, ["service", "app", "appName", "Service", "component", "process"]),
                message=message,
                raw=json.dumps(data),
                metadata=data
            ))
        except Exception:
            normalized.append(NormalizedLog(
                timestamp=datetime.utcnow(),
                level=detect_log_level(str(data)),
                message=str(data),
                raw=json.dumps(data)
            ))
            
    return normalized


def parse_csv_logs(raw_data: str) -> List[NormalizedLog]:
    """Parse CSV log files. Auto-detects single-column log dumps and unwraps them."""
    normalized: List[NormalizedLog] = []
    lines = raw_data.strip().splitlines()
    reader = csv.DictReader(lines)
    fieldnames = reader.fieldnames or []

    # Helper to normalize keys
    def normalize_key(k: str) -> str:
        return k.strip().lower().replace(" ", "_") if k else ""

    # Detect single-column CSV that wraps raw log lines
    log_dump_headers = (
        "generated_log_line", "log_line", "log", "raw_log",
        "message", "msg", "log_entry", "raw",
    )
    is_log_dump = (
        len(fieldnames) == 1
        and normalize_key(fieldnames[0]) in log_dump_headers
    )

    if is_log_dump:
        col_name = fieldnames[0]
        unwrapped: List[str] = []
        for row in reader:
            cell = row.get(col_name, "")
            if cell:
                cell_clean = cell.replace("\\n", "\n")
                for line in cell_clean.strip().splitlines():
                    line_clean = line.strip().strip('"').strip("'").strip()
                    if line_clean:
                        unwrapped.append(line_clean)
        if unwrapped:
            joined = "\n".join(unwrapped)
            # Auto-detect the inner format
            inner_fmt = auto_detect_format(joined)
            if inner_fmt == "NGINX":
                return parse_nginx(joined)
            if inner_fmt == "JSON":
                return parse_json_logs(joined)
            return parse_syslog(joined)
        return normalized

    # Standard multi-column CSV
    for row in reader:
        norm_row = {normalize_key(k): v for k, v in row.items() if k}
        
        ts_val = norm_row.get("timestamp") or norm_row.get("time") or norm_row.get("date")
        ts = parse_timestamp(str(ts_val)) if ts_val else datetime.utcnow()

        message = norm_row.get("message") or norm_row.get("msg") or ", ".join([f"{k}={v}" for k, v in norm_row.items()])
        level = norm_row.get("level") or detect_log_level(message)

        normalized.append(NormalizedLog(
            timestamp=ts,
            level=level,
            source_ip=norm_row.get("source_ip") or norm_row.get("ip") or norm_row.get("client_ip") or norm_row.get("source_address"),
            user=norm_row.get("user") or norm_row.get("username") or norm_row.get("account_name"),
            service=norm_row.get("service") or norm_row.get("app") or "csv_import",
            message=message,
            raw=json.dumps(row)
        ))
    return normalized


def parse_xml_logs(raw_data: str) -> List[NormalizedLog]:
    """Parse XML log entries."""
    normalized: List[NormalizedLog] = []
    try:
        root = ET.fromstring(f"<root>{raw_data}</root>")
        for log_entry in root:
            data = {child.tag.strip(): child.text for child in log_entry if child.tag}
            norm_data = {k.lower().replace("_", "").replace(" ", ""): v for k, v in data.items()}
            
            ts_val = norm_data.get("timestamp") or norm_data.get("time") or norm_data.get("date")
            ts = parse_timestamp(str(ts_val)) if ts_val else datetime.utcnow()
            message = norm_data.get("message") or norm_data.get("msg") or norm_data.get("log") or str(data)
            normalized.append(NormalizedLog(
                timestamp=ts,
                level=norm_data.get("level") or norm_data.get("severity") or norm_data.get("status") or detect_log_level(message),
                source_ip=norm_data.get("sourceip") or norm_data.get("ip") or norm_data.get("clientip") or norm_data.get("sourceaddress"),
                user=norm_data.get("user") or norm_data.get("username") or norm_data.get("accountname"),
                service=norm_data.get("service") or norm_data.get("app") or log_entry.tag,
                message=message,
                raw=ET.tostring(log_entry, encoding="utf-8").decode("utf-8")
            ))
    except Exception as e:
        logger.warning(f"XML parsing failed: {e}. Falling back to TXT line-by-line.")
        return parse_txt_logs(raw_data)
    return normalized


def parse_txt_logs(raw_data: str) -> List[NormalizedLog]:
    """Fallback plain-text parser. Extracts whatever it can from each line."""
    normalized: List[NormalizedLog] = []
    lines = raw_data.strip().splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        source_ip = None
        ip_match = IP_REGEX.search(line)
        if ip_match:
            source_ip = ip_match.group(0)

        user = None
        user_match = re.search(r'\bUser=([a-zA-Z0-9_\-\.]+)', line, re.IGNORECASE)
        if user_match:
            user = user_match.group(1)

        normalized.append(NormalizedLog(
            timestamp=datetime.utcnow(),
            level=detect_log_level(line),
            source_ip=source_ip,
            user=user,
            message=line,
            raw=line
        ))
    return normalized

# ---------------------------------------------------------------------------
# Filtering & metrics
# ---------------------------------------------------------------------------

def apply_filters(logs: List[NormalizedLog], intent: IntentObject) -> List[NormalizedLog]:
    filtered: List[NormalizedLog] = []
    entities = intent.entities or {}
    conditions = intent.conditions or {}

    def clean_val(v: Any) -> Optional[str]:
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
            ref_time = datetime.utcnow()
            if logs:
                log_times = [log.timestamp for log in logs if log.timestamp]
                if log_times:
                    ref_time = max(log_times)
            cutoff_time = ref_time - timedelta(**{delta_map[unit]: val})

    for log in logs:
        if cutoff_time and log.timestamp < cutoff_time:
            continue
        if target_ip and log.source_ip != target_ip:
            continue
        if target_user and log.user != target_user:
            continue
        if target_resource and target_resource.lower() not in log.message.lower() and target_resource.lower() not in (log.service or "").lower():
            continue
        filtered.append(log)
    return filtered


def compute_metrics(all_logs: List[NormalizedLog], filtered_logs: List[NormalizedLog]) -> Dict[str, Any]:
    error_count = sum(1 for l in filtered_logs if l.level.upper() in ["ERROR", "CRITICAL", "FAIL", "FATAL"])
    warn_count = sum(1 for l in filtered_logs if l.level.upper() in ["WARN", "WARNING"])

    ips: Dict[str, int] = {}
    for l in filtered_logs:
        if l.source_ip:
            ips[l.source_ip] = ips.get(l.source_ip, 0) + 1

    services: Dict[str, int] = {}
    for l in filtered_logs:
        if l.service:
            services[l.service] = services.get(l.service, 0) + 1

    # Level distribution — lets the Analysis Agent see exact severity breakdown
    level_dist: Dict[str, int] = {}
    for l in filtered_logs:
        lvl = l.level.upper()
        level_dist[lvl] = level_dist.get(lvl, 0) + 1

    # User distribution — surfaces brute-force user-targeting patterns
    user_dist: Dict[str, int] = {}
    for l in filtered_logs:
        if l.user:
            user_dist[l.user] = user_dist.get(l.user, 0) + 1

    # Calculate log recency: if latest log is within 1 hour of current UTC time, it is recent.
    max_log_time = None
    if filtered_logs:
        max_log_time = max(l.timestamp for l in filtered_logs if l.timestamp)
    elif all_logs:
        max_log_time = max(l.timestamp for l in all_logs if l.timestamp)

    recency = "unknown"
    if max_log_time:
        time_diff = datetime.utcnow() - max_log_time
        if abs(time_diff.total_seconds()) < 3600:
            recency = "recent (real-time stream)"
        else:
            recency = "historical (past logs archive)"

    return {
        "total_records": len(all_logs),
        "filtered_records": len(filtered_logs),
        "error_count": error_count,
        "warning_count": warn_count,
        "unique_ips_count": len(ips),
        "top_ips": sorted(ips.items(), key=lambda x: x[1], reverse=True)[:10],
        "services": services,
        "level_distribution": level_dist,
        "user_distribution": dict(sorted(user_dist.items(), key=lambda x: x[1], reverse=True)[:10]),
        "log_recency": recency
    }

# ---------------------------------------------------------------------------
# API endpoint
# ---------------------------------------------------------------------------

# Map all frontend format values to internal parser names
FORMAT_ALIASES: Dict[str, str] = {
    "SYSLOG": "SYSLOG",
    "SYSLOG RFC 3164": "SYSLOG",
    "WINDOWS EVENT": "SYSLOG",       # Same timestamp-host-message structure
    "WINDOWS EVENT LOGS": "SYSLOG",
    "LINUX AUTH": "SYSLOG",
    "LINUX AUTH LOGS": "SYSLOG",
    "FIREWALL": "SYSLOG",
    "FIREWALL LOGS": "SYSLOG",
    "NGINX": "NGINX",
    "NGINX LOGS": "NGINX",
    "APACHE": "NGINX",               # Same combined log format
    "APACHE LOGS": "NGINX",
    "JSON": "JSON",
    "JSON LOGLINES": "JSON",
    "CSV": "CSV",
    "CSV COMMA SEPARATED": "CSV",
    "XML": "XML",
    "XML STRUCTURED": "XML",
    "TXT": "TXT",
    "PLAIN TXT": "TXT",
}

PARSERS = {
    "SYSLOG": parse_syslog,
    "NGINX": parse_nginx,
    "JSON": parse_json_logs,
    "CSV": parse_csv_logs,
    "XML": parse_xml_logs,
    "TXT": parse_txt_logs,
}


@app.post("/process-data", response_model=DataProcessResponse)
async def process_data(request: DataProcessRequest):
    raw = request.logs_raw.strip()
    user_hint = request.log_format.strip().upper()

    # 1. Auto-detect the actual content format
    detected = auto_detect_format(raw)

    # 2. Resolve the user's dropdown selection through aliases
    resolved_hint = FORMAT_ALIASES.get(user_hint, user_hint)

    # 3. Decide which parser to use:
    #    - Trust auto-detection for structural formats (JSON, XML, CSV, NGINX)
    #    - For SYSLOG/TXT, prefer auto-detection but fall back to user hint
    if detected in ("JSON", "XML", "CSV", "NGINX"):
        fmt = detected
    elif resolved_hint in PARSERS:
        fmt = resolved_hint
    else:
        fmt = detected

    logger.info(f"Processing logs. User hint='{request.log_format}' -> resolved='{resolved_hint}', auto-detected='{detected}', using='{fmt}'")

    try:
        parser = PARSERS.get(fmt, parse_syslog)
        all_logs = parser(raw)

        # Safety net: if the chosen parser produced zero results but syslog
        # parser would have found some, retry with syslog as the universal fallback.
        if not all_logs and fmt != "SYSLOG" and fmt != "TXT":
            logger.info(f"Parser '{fmt}' produced 0 results. Retrying with syslog fallback.")
            all_logs = parse_syslog(raw)

        filtered_logs = apply_filters(all_logs, request.intent)
        metrics = compute_metrics(all_logs, filtered_logs)

        logger.info(f"Parsed {len(all_logs)} logs, {len(filtered_logs)} after filtering. "
                     f"Errors={metrics['error_count']}, Warnings={metrics['warning_count']}")

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
