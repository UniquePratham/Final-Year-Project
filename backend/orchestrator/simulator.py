import random
import json
import csv
import io
from datetime import datetime, timedelta
from typing import List, Dict, Any

# Predefined variables for realistic details
IPS = [
    "192.168.1.105", "10.0.0.12", "192.168.1.44", "172.16.4.8", "203.0.113.15", 
    "198.51.100.4", "45.76.10.2", "185.190.140.22", "82.102.23.45", "91.200.12.33"
]
ATTACK_IPS = [
    "185.220.101.44", "91.200.12.33", "203.0.113.55", "82.102.23.45", "45.55.12.99"
]
USERNAMES = ["admin", "root", "ubuntu", "postgres", "db_backup", "pratham", "guest", "test_user"]
SERVICES = ["sshd", "nginx", "postgres", "systemd", "auth-server", "api-gateway", "firewalld", "cron"]
HOSTNAMES = ["gateway-prod", "db-cluster-01", "auth-svc-win", "auth-server", "host-monitor", "web-lb-02"]
COUNTRIES = ["US", "RU", "CN", "DE", "IN", "BR", "CA", "UA", "NL", "FR"]

def get_random_ip(is_attacker=False):
    return random.choice(ATTACK_IPS) if is_attacker else random.choice(IPS)

def format_timestamp(dt: datetime, format_type: str) -> str:
    if format_type == "Syslog" or format_type == "Linux Auth Logs":
        # e.g., Jun 13 00:20:15
        return dt.strftime("%b %d %H:%M:%S")
    elif format_type == "Nginx" or format_type == "Apache":
        # e.g., 13/Jun/2026:00:20:18 +0000
        return dt.strftime("%d/%b/%Y:%H:%M:%S +0000")
    elif format_type == "Windows Event Logs":
        # e.g., 2026-06-13 00:20:15
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    else:
        return dt.isoformat()

def generate_log_line(dt: datetime, scenario: str, log_format: str, custom_params: Dict[str, Any] = None) -> str:
    # 1. Determine parameters based on scenario
    is_attacker = scenario in ["Brute Force Attacks", "DDoS Traffic Patterns", "Unauthorized Access Attempts", "Malware Indicators", "Privilege Escalation Attempts"]
    ip = custom_params.get("ip") if custom_params and custom_params.get("ip") else get_random_ip(is_attacker)
    user = custom_params.get("user") if custom_params and custom_params.get("user") else random.choice(USERNAMES)
    host = random.choice(HOSTNAMES)
    service = random.choice(SERVICES)
    country = random.choice(COUNTRIES)
    
    # Override based on specific scenario details
    level = "INFO"
    msg = ""
    status_code = 200
    method = "GET"
    path = "/index.html"
    bytes_sent = random.randint(500, 5000)
    win_event_id = 4624 # Successful login
    
    if scenario == "Normal System Activity":
        level = "INFO"
        templates = [
            (f"nginx", f"Connection established from {ip} to port 80"),
            (f"sshd", f"Connection closed by authenticating user {user} {ip} port {random.randint(40000, 60000)} [preauth]"),
            (f"postgres", f"database system is ready to accept connections"),
            (f"systemd", f"Service docker.service entered active state."),
            (f"nginx", f"{ip} - - [{format_timestamp(dt, 'Nginx')}] \"GET /api/v1/health HTTP/1.1\" 200 45"),
            (f"cron", f"pam_unix(cron:session): session opened for user root(uid=0) by (uid=0)")
        ]
        service, msg = random.choice(templates)
        if service == "nginx":
            status_code = 200
            path = "/api/v1/health"
    
    elif scenario == "Failed Login Attempts":
        level = "WARN"
        win_event_id = 4625 # Failed login
        templates = [
            (f"sshd", f"Failed password for invalid user {user} from {ip} port {random.randint(40000, 60000)} ssh2"),
            (f"auth-server", f"Authentication failure for user '{user}' from IP {ip}: invalid credentials"),
            (f"postgres", f"FATAL: password authentication failed for user \"{user}\" from {ip}")
        ]
        service, msg = random.choice(templates)
        
    elif scenario == "Brute Force Attacks":
        level = "WARN"
        win_event_id = 4625
        templates = [
            (f"sshd", f"Failed password for root from {ip} port {random.randint(40000, 60000)} ssh2"),
            (f"sshd", f"Failed password for admin from {ip} port {random.randint(40000, 60000)} ssh2"),
            (f"auth-server", f"Authentication failure for user 'admin' from IP {ip}: Account locked temporarily due to 5 failed attempts")
        ]
        service, msg = random.choice(templates)
        
    elif scenario == "DDoS Traffic Patterns":
        level = "INFO"
        service = "nginx"
        path = "/login"
        method = "POST"
        status_code = 200
        msg = f"{ip} - - [{format_timestamp(dt, 'Nginx')}] \"POST /login HTTP/1.1\" 200 {random.randint(100, 500)} \"-\" \"Mozilla/5.0 (Bot)\""
        
    elif scenario == "Unauthorized Access Attempts":
        level = "WARN"
        service = "nginx"
        status_code = random.choice([401, 403])
        path = random.choice(["/admin/settings", "/etc/passwd", "/api/v2/secrets", "/wp-admin/"])
        method = "GET"
        msg = f"{ip} - - [{format_timestamp(dt, 'Nginx')}] \"GET {path} HTTP/1.1\" {status_code} 102"
        
    elif scenario == "Malware Indicators":
        level = "CRITICAL"
        service = "firewalld"
        malware_sig = random.choice(["Trojan.Gen.2", "WannaCry.KillSwitch", "ReverseShell.Python", "Adware.Clicker"])
        msg = f"MALWARE ALERT: Inbound connection matches signature {malware_sig} from host {ip} targeted at local port {random.choice([4444, 8080, 22])}"
        
    elif scenario == "Service Crashes":
        level = "ERROR"
        service = "systemd"
        crashed_svc = random.choice(["nginx.service", "postgresql.service", "api-gateway.service", "logstash.service"])
        msg = f"Service {crashed_svc} entered failed state. Main process exited, code=exited, status={random.choice([1, 127, 2, 137])}"
        
    elif scenario == "Database Failures":
        level = "CRITICAL"
        service = "postgres"
        msg = random.choice([
            f"FATAL: connection limit exceeded for non-superusers",
            f"ERROR: deadlock detected - Process {random.randint(1000, 9999)} waits for ShareLock on transaction",
            f"PANIC: could not locate a valid checkpoint record",
            f"FATAL: database system is shutting down"
        ])
        
    elif scenario == "Memory Spikes":
        level = "WARN"
        service = "systemd"
        pct = random.randint(92, 99)
        msg = f"SYSTEM WARNING: High RAM usage detected. Current utilization at {pct}%. kernel: [oom-killer] active process list analyzed."
        
    elif scenario == "CPU Overload":
        level = "WARN"
        service = "systemd"
        load = round(random.uniform(8.5, 22.4), 2)
        msg = f"SYSTEM WARNING: High CPU utilization load average: {load}, {load-2.0}, {load-4.0}. Scheduler latency spiked to {random.randint(100, 800)}ms."
        
    elif scenario == "Disk Exhaustion":
        level = "CRITICAL"
        service = "systemd"
        msg = f"SYSTEM ERROR: Disk space exhausted on partition /dev/sda1 (100% capacity). Write operations blocked."
        
    elif scenario == "Network Latency Issues":
        level = "WARN"
        service = "api-gateway"
        msg = f"TIMEOUT ERROR: Gateway timeout forwarding request to backend auth-service. Latency: {random.randint(5000, 15000)}ms."
        
    elif scenario == "Compliance Violations":
        level = "WARN"
        service = "firewalld"
        msg = f"COMPLIANCE ALERT: Non-compliant connection handshaked from {ip} using legacy TLSv1.0 protocol. Allowed minimum: TLSv1.2."
        
    elif scenario == "User Behavior Anomalies":
        level = "WARN"
        service = "auth-server"
        msg = f"ANOMALY DETECTED: User '{user}' authenticated successfully from IP {ip} ({country}) at unusual hour {dt.strftime('%H:%M:%S')}. Previous geo-session: IN"
        
    elif scenario == "Privilege Escalation Attempts":
        level = "CRITICAL"
        service = "sshd"
        msg = f"SECURITY ALERT: User '{user}' failed sudo command validation: user NOT in sudoers file. Attempted command: 'rm -rf /var/log/' from terminal tty1"
        
    else: # Mixed Incident Scenarios
        level = random.choice(["INFO", "WARN", "ERROR", "CRITICAL"])
        service = random.choice(SERVICES)
        msg = f"Mixed logs activity: System operation normal at {ip} executing job task {random.randint(100, 500)}"

    # 2. Convert to log format
    if log_format == "JSON":
        return json.dumps({
            "timestamp": format_timestamp(dt, "JSON"),
            "level": level,
            "source_ip": ip,
            "user": user,
            "hostname": host,
            "service": service,
            "message": msg,
            "country": country,
            "status": status_code
        })
        
    elif log_format == "Syslog":
        # Jun 13 00:20:15 host-monitor sshd[123]: Message
        return f"{format_timestamp(dt, 'Syslog')} {host} {service}[{random.randint(50, 5000)}]: {msg}"
        
    elif log_format == "Nginx":
        if msg.startswith(ip): # Nginx formatted already
            return msg
        return f"{ip} - - [{format_timestamp(dt, 'Nginx')}] \"{method} {path} HTTP/1.1\" {status_code} {bytes_sent} \"-\" \"Mozilla/5.0\""
        
    elif log_format == "Apache":
        return f"{ip} - - [{format_timestamp(dt, 'Apache')}] \"{method} {path} HTTP/1.1\" {status_code} {bytes_sent}"
        
    elif log_format == "Windows Event Logs":
        # 2026-06-13 00:20:15 Win-Server-01 Security EventID=4625 Level=Warning Msg=Failed Login
        return f"{format_timestamp(dt, 'Windows Event Logs')} {host} Security EventID={win_event_id} Level={level} Msg={msg} User={user} IP={ip}"
        
    elif log_format == "Linux Auth Logs":
        return f"{format_timestamp(dt, 'Linux Auth Logs')} {host} auth-server: {msg}"
        
    elif log_format == "Firewall Logs":
        # firewall-ip-blocked INBOUND PROTO=TCP SRC=1.1.1.1 DST=2.2.2.2 SPORT=4322 DPORT=80
        action = "BLOCKED" if level in ["WARN", "ERROR", "CRITICAL"] else "ALLOWED"
        return f"{format_timestamp(dt, 'Windows Event Logs')} {host} firewall: {action} SRC={ip} DST={get_random_ip(False)} PROTO=TCP SPORT={random.randint(1024, 65535)} DPORT={random.choice([80, 443, 22, 5432])} Country={country}"
        
    elif log_format == "CSV":
        # Return comma separated fields
        return f'"{format_timestamp(dt, "JSON")}","{level}","{host}","{service}","{ip}","{user}","{msg}"'
        
    else: # TXT / Plain Text
        return f"[{format_timestamp(dt, 'JSON')}] [{level}] [{service}] {msg}"

def generate_log_batch(scenario: str, log_format: str, rate: int, duration_seconds: int = 10, custom_params: Dict[str, Any] = None) -> List[str]:
    logs = []
    # Calculate count
    count = rate * duration_seconds
    if count > 500:
        # Cap count to avoid memory bloat in test environment
        count = 500
        
    now = datetime.utcnow()
    # Generate logs backwards in time so latest is "now"
    for i in range(count):
        offset = (duration_seconds / count) * i
        dt = now - timedelta(seconds=offset)
        logs.append(generate_log_line(dt, scenario, log_format, custom_params))
        
    # Reverse so they are chronological
    logs.reverse()
    return logs
