import React, { useState, useEffect, useRef } from 'react';

// Mock SVG icons
const Icons = {
  Terminal: () => (
    <svg className="w-5 h-5 text-blue-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z" />
    </svg>
  ),
  Activity: () => (
    <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
    </svg>
  ),
  ShieldAlert: () => (
    <svg className="w-5 h-5 text-rose-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  Cpu: () => (
    <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 5h10a2 2 0 012 2v10a2 2 0 01-2 2H7a2 2 0 01-2-2V7a2 2 0 012-2z" />
    </svg>
  ),
  CheckCircle: () => (
    <svg className="w-5 h-5 text-emerald-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
    </svg>
  ),
  AlertTriangle: () => (
    <svg className="w-5 h-5 text-amber-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
    </svg>
  ),
  Server: () => (
    <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01" />
    </svg>
  ),
  Upload: ({ className = "w-6 h-6 text-blue-400" }) => (
    <svg className={className} fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" />
    </svg>
  ),
  Lock: () => (
    <svg className="w-4 h-4 mr-2 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z" />
    </svg>
  ),
  Refresh: () => (
    <svg className="w-4 h-4 mr-1 text-slate-400 animate-spin" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
      <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H17" />
    </svg>
  )
};

function generateLogsJS(scenario, format, rate, duration, customIp, customUser) {
  const IPS = [
    "192.168.1.105", "10.0.0.12", "192.168.1.44", "172.16.4.8", "203.0.113.15", 
    "198.51.100.4", "45.76.10.2", "185.190.140.22", "82.102.23.45", "91.200.12.33"
  ];
  const ATTACK_IPS = [
    "185.220.101.44", "91.200.12.33", "203.0.113.55", "82.102.23.45", "45.55.12.99"
  ];
  const USERNAMES = ["admin", "root", "ubuntu", "postgres", "db_backup", "pratham", "guest", "test_user"];
  const SERVICES = ["sshd", "nginx", "postgres", "systemd", "auth-server", "api-gateway", "firewalld", "cron"];
  const HOSTNAMES = ["gateway-prod", "db-cluster-01", "auth-svc-win", "auth-server", "host-monitor", "web-lb-02"];
  const COUNTRIES = ["US", "RU", "CN", "DE", "IN", "BR", "CA", "UA", "NL", "FR"];

  const getRandomIp = (isAttacker) => {
    const arr = isAttacker ? ATTACK_IPS : IPS;
    return arr[Math.floor(Math.random() * arr.length)];
  };

  const formatTimestamp = (dt, formatType) => {
    if (formatType === "Syslog" || formatType === "Linux Auth Logs") {
      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const m = months[dt.getMonth()];
      const d = String(dt.getDate()).padStart(2, ' ');
      const h = String(dt.getHours()).padStart(2, '0');
      const min = String(dt.getMinutes()).padStart(2, '0');
      const s = String(dt.getSeconds()).padStart(2, '0');
      return `${m} ${d} ${h}:${min}:${s}`;
    } else if (formatType === "Nginx" || formatType === "Apache") {
      const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
      const m = months[dt.getMonth()];
      const d = String(dt.getDate()).padStart(2, '0');
      const y = dt.getFullYear();
      const h = String(dt.getHours()).padStart(2, '0');
      const min = String(dt.getMinutes()).padStart(2, '0');
      const s = String(dt.getSeconds()).padStart(2, '0');
      return `${d}/${m}/${y}:${h}:${min}:${s} +0000`;
    } else if (formatType === "Windows Event Logs") {
      const y = dt.getFullYear();
      const m = String(dt.getMonth() + 1).padStart(2, '0');
      const d = String(dt.getDate()).padStart(2, '0');
      const h = String(dt.getHours()).padStart(2, '0');
      const min = String(dt.getMinutes()).padStart(2, '0');
      const s = String(dt.getSeconds()).padStart(2, '0');
      return `${y}-${m}-${d} ${h}:${min}:${s}`;
    } else {
      return dt.toISOString();
    }
  };

  const count = rate * duration;
  const limitedCount = count > 500 ? 500 : count;
  const logs = [];
  const now = new Date();

  for (let i = 0; i < limitedCount; i++) {
    const offsetSeconds = (duration / limitedCount) * i;
    const dt = new Date(now.getTime() - offsetSeconds * 1000);

    const isAttacker = ["Brute Force Attacks", "DDoS Traffic Patterns", "Unauthorized Access Attempts", "Malware Indicators", "Privilege Escalation Attempts"].includes(scenario);
    const ip = customIp || getRandomIp(isAttacker);
    const user = customUser || USERNAMES[Math.floor(Math.random() * USERNAMES.length)];
    const host = HOSTNAMES[Math.floor(Math.random() * HOSTNAMES.length)];
    let service = SERVICES[Math.floor(Math.random() * SERVICES.length)];
    const country = COUNTRIES[Math.floor(Math.random() * COUNTRIES.length)];

    let level = "INFO";
    let msg = "";
    let statusCode = 200;
    let method = "GET";
    let path = "/index.html";
    let bytesSent = Math.floor(Math.random() * 4500) + 500;
    let winEventId = 4624;

    if (scenario === "Normal System Activity") {
      level = "INFO";
      const templates = [
        ["nginx", `Connection established from ${ip} to port 80`],
        ["sshd", `Connection closed by authenticating user ${user} ${ip} port ${Math.floor(Math.random() * 20000) + 40000} [preauth]`],
        ["postgres", `database system is ready to accept connections`],
        ["systemd", `Service docker.service entered active state.`],
        ["nginx", `${ip} - - [${formatTimestamp(dt, 'Nginx')}] "GET /api/v1/health HTTP/1.1" 200 45`],
        ["cron", `pam_unix(cron:session): session opened for user root(uid=0) by (uid=0)`]
      ];
      const selected = templates[Math.floor(Math.random() * templates.length)];
      service = selected[0];
      msg = selected[1];
      if (service === "nginx") {
        statusCode = 200;
        path = "/api/v1/health";
      }
    } else if (scenario === "Failed Login Attempts") {
      level = "WARN";
      winEventId = 4625;
      const templates = [
        ["sshd", `Failed password for invalid user ${user} from ${ip} port ${Math.floor(Math.random() * 20000) + 40000} ssh2`],
        ["auth-server", `Authentication failure for user '${user}' from IP {ip}: invalid credentials`],
        ["postgres", `FATAL: password authentication failed for user "${user}" from ${ip}`]
      ];
      const selected = templates[Math.floor(Math.random() * templates.length)];
      service = selected[0];
      msg = selected[1];
    } else if (scenario === "Brute Force Attacks") {
      level = "WARN";
      winEventId = 4625;
      const templates = [
        ["sshd", `Failed password for root from ${ip} port ${Math.floor(Math.random() * 20000) + 40000} ssh2`],
        ["sshd", `Failed password for admin from ${ip} port ${Math.floor(Math.random() * 20000) + 40000} ssh2`],
        ["auth-server", `Authentication failure for user 'admin' from IP ${ip}: Account locked temporarily due to 5 failed attempts`]
      ];
      const selected = templates[Math.floor(Math.random() * templates.length)];
      service = selected[0];
      msg = selected[1];
    } else if (scenario === "DDoS Traffic Patterns") {
      level = "INFO";
      service = "nginx";
      path = "/login";
      method = "POST";
      statusCode = 200;
      msg = `${ip} - - [${formatTimestamp(dt, 'Nginx')}] "POST /login HTTP/1.1" 200 ${Math.floor(Math.random() * 400) + 100} "-" "Mozilla/5.0 (Bot)"`;
    } else if (scenario === "Unauthorized Access Attempts") {
      level = "WARN";
      service = "nginx";
      statusCode = [401, 403][Math.floor(Math.random() * 2)];
      const paths = ["/admin/settings", "/etc/passwd", "/api/v2/secrets", "/wp-admin/"];
      path = paths[Math.floor(Math.random() * paths.length)];
      method = "GET";
      msg = `${ip} - - [${formatTimestamp(dt, 'Nginx')}] "GET ${path} HTTP/1.1" ${statusCode} 102`;
    } else if (scenario === "Malware Indicators") {
      level = "CRITICAL";
      service = "firewalld";
      const sigs = ["Trojan.Gen.2", "WannaCry.KillSwitch", "ReverseShell.Python", "Adware.Clicker"];
      const sig = sigs[Math.floor(Math.random() * sigs.length)];
      const ports = [4444, 8080, 22];
      const targetPort = ports[Math.floor(Math.random() * ports.length)];
      msg = `MALWARE ALERT: Inbound connection matches signature ${sig} from host ${ip} targeted at local port ${targetPort}`;
    } else if (scenario === "Service Crashes") {
      level = "ERROR";
      service = "systemd";
      const svcs = ["nginx.service", "postgresql.service", "api-gateway.service", "logstash.service"];
      const crashedSvc = svcs[Math.floor(Math.random() * svcs.length)];
      msg = `Service ${crashedSvc} entered failed state. Main process exited, code=exited, status=${[1, 127, 2, 137][Math.floor(Math.random() * 4)]}`;
    } else if (scenario === "Database Failures") {
      level = "CRITICAL";
      service = "postgres";
      const msgs = [
        `FATAL: connection limit exceeded for non-superusers`,
        `ERROR: deadlock detected - Process ${Math.floor(Math.random() * 9000) + 1000} waits for ShareLock on transaction`,
        `PANIC: could not locate a valid checkpoint record`,
        `FATAL: database system is shutting down`
      ];
      msg = msgs[Math.floor(Math.random() * msgs.length)];
    } else if (scenario === "Memory Spikes") {
      level = "WARN";
      service = "systemd";
      const pct = Math.floor(Math.random() * 8) + 92;
      msg = `SYSTEM WARNING: High RAM usage detected. Current utilization at ${pct}%. kernel: [oom-killer] active process list analyzed.`;
    } else if (scenario === "CPU Overload") {
      level = "WARN";
      service = "systemd";
      const load = (Math.random() * 14 + 8.5).toFixed(2);
      msg = `SYSTEM WARNING: High CPU utilization load average: ${load}, ${(load - 2).toFixed(2)}, ${(load - 4).toFixed(2)}. Scheduler latency spiked to ${Math.floor(Math.random() * 700) + 100}ms.`;
    } else if (scenario === "Disk Exhaustion") {
      level = "CRITICAL";
      service = "systemd";
      msg = `SYSTEM ERROR: Disk space exhausted on partition /dev/sda1 (100% capacity). Write operations blocked.`;
    } else if (scenario === "Network Latency Issues") {
      level = "WARN";
      service = "api-gateway";
      msg = `TIMEOUT ERROR: Gateway timeout forwarding request to backend auth-service. Latency: ${Math.floor(Math.random() * 10000) + 5000}ms.`;
    } else if (scenario === "Compliance Violations") {
      level = "WARN";
      service = "firewalld";
      msg = `COMPLIANCE ALERT: Non-compliant connection handshaked from ${ip} using legacy TLSv1.0 protocol. Allowed minimum: TLSv1.2.`;
    } else if (scenario === "User Behavior Anomalies") {
      level = "WARN";
      service = "auth-server";
      const timeStr = formatTimestamp(dt, "Syslog").split(" ")[2] || "00:00:00";
      msg = `ANOMALY DETECTED: User '${user}' authenticated successfully from IP ${ip} (${country}) at unusual hour ${timeStr}. Previous geo-session: IN`;
    } else if (scenario === "Privilege Escalation Attempts") {
      level = "CRITICAL";
      service = "sshd";
      msg = `SECURITY ALERT: User '${user}' failed sudo command validation: user NOT in sudoers file. Attempted command: 'rm -rf /var/log/' from terminal tty1`;
    } else {
      level = ["INFO", "WARN", "ERROR", "CRITICAL"][Math.floor(Math.random() * 4)];
      msg = `Mixed logs activity: System operation normal at ${ip} executing job task ${Math.floor(Math.random() * 400) + 100}`;
    }

    let line = "";
    if (format === "JSON") {
      line = JSON.stringify({
        timestamp: formatTimestamp(dt, "JSON"),
        level,
        source_ip: ip,
        user,
        hostname: host,
        service,
        message: msg,
        country,
        status: statusCode
      });
    } else if (format === "Syslog") {
      line = `${formatTimestamp(dt, 'Syslog')} ${host} ${service}[${Math.floor(Math.random() * 4950) + 50}]: ${msg}`;
    } else if (format === "Nginx") {
      if (msg.startsWith(ip)) {
        line = msg;
      } else {
        line = `${ip} - - [${formatTimestamp(dt, 'Nginx')}] "${method} ${path} HTTP/1.1" ${statusCode} ${bytesSent} "-" "Mozilla/5.0"`;
      }
    } else if (format === "Apache") {
      line = `${ip} - - [${formatTimestamp(dt, 'Apache')}] "${method} ${path} HTTP/1.1" ${statusCode} ${bytesSent}`;
    } else if (format === "Windows Event Logs") {
      line = `${formatTimestamp(dt, 'Windows Event Logs')} ${host} Security EventID=${winEventId} Level=${level} Msg=${msg} User=${user} IP=${ip}`;
    } else if (format === "Linux Auth Logs") {
      line = `${formatTimestamp(dt, 'Linux Auth Logs')} ${host} auth-server: ${msg}`;
    } else if (format === "Firewall Logs") {
      const action = ["WARN", "ERROR", "CRITICAL"].includes(level) ? "BLOCKED" : "ALLOWED";
      line = `${formatTimestamp(dt, 'Windows Event Logs')} ${host} firewall: ${action} SRC=${ip} DST=${getRandomIp(false)} PROTO=TCP SPORT=${Math.floor(Math.random() * 64511) + 1024} DPORT=${[80, 443, 22, 5432][Math.floor(Math.random() * 4)]} Country=${country}`;
    } else if (format === "CSV") {
      line = `"${formatTimestamp(dt, "JSON")}","${level}","${host}","${service}","${ip}","${user}","${msg}"`;
    } else {
      line = `[${formatTimestamp(dt, 'JSON')}] [${level}] [${service}] ${msg}`;
    }

    logs.push(line);
  }

  logs.reverse();
  return logs.join("\n");
}

function getSandboxReportAndPlaybook(scenario, customIp, customUser, logsCount) {
  const ip = customIp || "185.220.101.44";
  const user = customUser || "root";
  const count = logsCount || 100;

  let status = "Healthy";
  let summary = "";
  let recommendations = "";
  let affected_resources = [];
  let mitigation_actions = [];

  if (scenario === "Normal System Activity") {
    status = "Healthy";
    summary = `### System Analysis Report\n\nAll ingested system logs (${count} lines analyzed) exhibit normal behavior. System authentication events, cron jobs, and database initializations are occurring within normal thresholds. Web service traffic consists solely of authorized requests and routine health checks. No security threats or performance anomalies detected.`;
    recommendations = `1. **Routine Auditing**: Continue regular monitoring at the current polling rate.\n2. **Log Maintenance**: Ensure log rotation is configured correctly to prevent partition bloating.\n3. **Baseline Update**: Keep this trace as a template for baseline comparison.`;
    affected_resources = ["Nginx Web Server", "PostgreSQL Daemon", "SSHD Service"];
    mitigation_actions = [
      {
        action_type: "SYSTEM_MONITOR",
        status: "SUCCESS",
        description: "System baseline verified. No immediate response actions required.",
        command: "service --status-all"
      }
    ];
  } else if (scenario === "Failed Login Attempts" || scenario === "Brute Force Attacks") {
    status = "Bad";
    summary = `### Brute Force Authentication Detected\n\nAn ongoing authentication attack has been identified on the system. The analysis detected a series of rapid SSH and authentication failures (EventID 4625 / Pam auth failure) targeting accounts such as '${user}' and 'root' from the source IP address \`${ip}\`. A total of ${Math.ceil(count * 0.4)} authentication failure events were logged in the batch, indicating a coordinated credential stuffing or brute-force attempt.`;
    recommendations = `1. **Isolate Source IP**: Immediately block incoming connections from the attacker IP address.\n2. **Enforce Strong Password Policies**: Ensure SSH and administrative users use public-key auth instead of passwords.\n3. **Limit Login Retries**: Configure fail2ban to lock out IPs after 3 failed password attempts.`;
    affected_resources = ["SSHD Service", "Authentication Gateway", "Linux PAM Module"];
    mitigation_actions = [
      {
        action_type: "FIREWALL_RULE",
        status: "COMPLETED",
        description: `Block all incoming TCP/UDP traffic from source IP address ${ip} via iptables firewall.`,
        command: `sudo iptables -A INPUT -s ${ip} -j DROP`
      },
      {
        action_type: "SSH_HARDENING",
        status: "COMPLETED",
        description: `Disable password authentication in sshd_config for root.`,
        command: "sudo sed -i 's/#PermitRootLogin.*/PermitRootLogin prohibit-password/' /etc/ssh/sshd_config && sudo systemctl restart sshd"
      }
    ];
  } else if (scenario === "DDoS Traffic Patterns") {
    status = "Bad";
    summary = `### Distributed Denial of Service (DDoS) Flood Detected\n\nThe web frontend (Nginx) is receiving a sudden surge of POST requests to \`/login\` from IP address \`${ip}\` (user agent: Mozilla/5.0 (Bot)), simulating a layer 7 HTTP flood. Over ${Math.ceil(count * 0.8)} POST requests were processed in the last evaluation window, causing response latency warnings in our gateway components.`;
    recommendations = `1. **Deploy Rate Limiting**: Enable Nginx rate-limiting on endpoint \`/login\`.\n2. **Block Attacker IP**: Apply temporary edge firewall drop rules for IP ${ip}.\n3. **Integrate Cloudflare WAF**: Place the service behind a CDN or WAF to filter automated botnets.`;
    affected_resources = ["Nginx Web Server", "Application Gateway", "Login Endpoint /login"];
    mitigation_actions = [
      {
        action_type: "FIREWALL_BLOCK",
        status: "COMPLETED",
        description: `Null-route or block the traffic from attacker IP ${ip} immediately.`,
        command: `sudo ufw deny from ${ip} to any port 80,443`
      },
      {
        action_type: "RATE_LIMITING",
        status: "COMPLETED",
        description: "Configure Nginx rate-limiting zones to limit logins to 5 requests per minute.",
        command: "echo 'limit_req_zone $binary_remote_addr zone=login_limit:10m rate=5r/m;' | sudo tee -a /etc/nginx/conf.d/rate_limits.conf"
      }
    ];
  } else if (scenario === "Unauthorized Access Attempts") {
    status = "Warning";
    summary = `### Directory Traversal & Unauthorized Access Detected\n\nSecurity analysis identified unauthorized access attempts targetting restricted paths (e.g., \`/admin/settings\`, \`/etc/passwd\`) from source IP \`${ip}\`, returning HTTP Status Codes 401 and 403. This indicates active scanner reconnaissance probing for configuration vulnerabilities.`;
    recommendations = `1. **Block Reconnaissance Host**: Ban scanner IP ${ip}.\n2. **Hide Administrative Paths**: Implement IP restrict lists for internal panels.\n3. **Directory Protection**: Ensure file permissions prevent reading sensitive system assets.`;
    affected_resources = ["Nginx Web Server", "Admin Portal Modules", "Sensitive Filesystem Paths"];
    mitigation_actions = [
      {
        action_type: "FIREWALL_DROP",
        status: "COMPLETED",
        description: `Block scanner host ${ip} from accessing all port ranges.`,
        command: `sudo ufw insert 1 deny from ${ip}`
      },
      {
        action_type: "NGINX_ACL",
        status: "COMPLETED",
        description: "Restrict access to directory paths using HTTP 404/403 controls.",
        command: "sudo bash -c 'cat <<EOF >> /etc/nginx/sites-available/default\\nlocation ~* /(wp-admin|etc/passwd) {\\n  deny all;\\n}\\nEOF' && sudo systemctl reload nginx"
      }
    ];
  } else if (scenario === "Malware Indicators") {
    status = "Bad";
    summary = `### Host Intrusion / Malware Connection Signature Alert\n\nCRITICAL: System firewall detected a connection match for known malware signatures from/to host \`${ip}\`. Active reverse shell script activity is suspected on local port ranges. Indicator signature matches: Trojan/ReverseShell.Python.`;
    recommendations = `1. **Terminate Malicious Processes**: Inspect active process trees on the system for unauthorized socket streams.\n2. **Perform Forensic Audit**: Check file hashes in cron directories and log scripts.\n3. **Isolate Compromised Node**: Place the instance under security group containment.`;
    affected_resources = ["Kernel Network Stack", "Local Ports 4444/8080", "System Binary Binaries"];
    mitigation_actions = [
      {
        action_type: "PROCESS_KILL",
        status: "COMPLETED",
        description: "Identify and terminate any processes communicating on suspicious local port 4444.",
        command: "sudo kill -9 $(sudo lsof -t -i:4444)"
      },
      {
        action_type: "CONTAINMENT_RULE",
        status: "COMPLETED",
        description: "Isolate compromised interfaces by dropping traffic to the malicious control IP.",
        command: `sudo iptables -A OUTPUT -d ${ip} -j DROP`
      }
    ];
  } else if (scenario === "Service Crashes") {
    status = "Bad";
    summary = `### System Service Process Crashed\n\nAn unexpected termination has been detected for critical applications (e.g., database postgresql or web nginx). systemd reports that the main process exited with failure code (status 1/137), leading to service unavailability.`;
    recommendations = `1. **Restart Crashing Service**: Attempt to restart the system process container.\n2. **Examine Process Logs**: Read stdout/stderr journalctls to trace memory segmentation faults or crash exceptions.\n3. **Verify Health Probes**: Configure auto-restart rules inside systemd configs.`;
    affected_resources = ["Systemd Daemon Service Manager", "PostgreSQL Database Engine", "Nginx Application"];
    mitigation_actions = [
      {
        action_type: "SERVICE_RESTART",
        status: "COMPLETED",
        description: "Attempt service status recovery and daemon-reload.",
        command: "sudo systemctl daemon-reload && sudo systemctl restart postgresql nginx"
      },
      {
        action_type: "LOG_DIAGNOSTIC",
        status: "COMPLETED",
        description: "Dump the last 100 systemd logs for the failed process units.",
        command: "sudo journalctl -xe -u postgresql -n 100"
      }
    ];
  } else if (scenario === "Database Failures") {
    status = "Bad";
    summary = `### PostgreSQL Database Exception / Connection Failure\n\nDatabase services are reporting severe operational exceptions. Common indicators detected: PostgreSQL connection limits exceeded, lock deadlocks, or database systems running shut down states. Transactions are blocked.`;
    recommendations = `1. **Scale Connection Limits**: Increase the max_connections setting in postgresql.conf.\n2. **Terminate Blocked Backends**: Find and kill blocking pg process PID connections.\n3. **Verify Storage Availability**: Inspect if disk space limits are causing write-ahead log (WAL) panics.`;
    affected_resources = ["PostgreSQL Database System", "Shared Memory Buffers", "Transaction Locks Table"];
    mitigation_actions = [
      {
        action_type: "SQL_TERMINATION",
        status: "COMPLETED",
        description: "Terminate queries holding transaction locks for more than 5 minutes.",
        command: "sudo -u postgres psql -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'active' AND now() - query_start > interval '5 minutes';\""
      },
      {
        action_type: "CONFIG_OPTIMIZATION",
        status: "COMPLETED",
        description: "Increase max connection parameters in configuration.",
        command: "sudo sed -i 's/max_connections =.*/max_connections = 250/' /etc/postgresql/*/main/postgresql.conf && sudo systemctl restart postgresql"
      }
    ];
  } else if (scenario === "Memory Spikes" || scenario === "CPU Overload" || scenario === "Disk Exhaustion") {
    status = "Warning";
    summary = `### System Resource Saturation Alert (${scenario})\n\nResource monitoring agent detected warning spikes on the node. CPU Scheduler latency has reached critical limits, RAM utilization is exceeding 95% triggering OOM killer logs, or root filesystem is at 100% capacity blocking writes.`;
    recommendations = `1. **Purge Temp Assets**: Clean up package manager caches and docker build volumes.\n2. **Identify Resource Hogs**: Inspect top processes by memory or CPU usage.\n3. **Provision Resources**: Scale node compute metrics or add additional volume space.`;
    affected_resources = ["Node Hypervisor Host", "Root Partition /dev/sda1", "CPU Core Schedulers"];
    mitigation_actions = [
      {
        action_type: "VOLUME_CLEANUP",
        status: "COMPLETED",
        description: "Clean up unused docker volumes, packages, and systemd journal logs to free space.",
        command: "sudo docker system prune -af --volumes && sudo journalctl --vacuum-size=100M && sudo apt-get clean"
      },
      {
        action_type: "RESOURCE_DIAGNOSTIC",
        status: "COMPLETED",
        description: "Find top 10 memory consuming active processes.",
        command: "ps aux --sort=-%mem | head -n 11"
      }
    ];
  } else {
    status = "Warning";
    summary = `### Security Incident & Anomalous Activity Detected\n\nWe analyzed the simulated log batch and identified security warnings and access exceptions during evaluation. Active IP connections from \`${ip}\` are displaying non-compliant traffic signatures.`;
    recommendations = `1. **Block Anomalous Traffic**: Filter source address IP ${ip}.\n2. **Audit Host Log Files**: Search files for privilege adjustments.\n3. **Restart Failed Daemons**: Validate system processes.`;
    affected_resources = ["API Gateway Service", "System Firewall Rules"];
    mitigation_actions = [
      {
        action_type: "FIREWALL_FILTER",
        status: "COMPLETED",
        description: `Apply drop filters for target IP ${ip}.`,
        command: `sudo iptables -A INPUT -s ${ip} -j DROP`
      }
    ];
  }

  return { status, summary, recommendations, affected_resources, mitigation_actions };
}
const PROVIDER_MODELS = {
  gemini: [
    { value: "gemini-1.5-flash", label: "Gemini 1.5 Flash" },
    { value: "gemini-1.5-pro", label: "Gemini 1.5 Pro" },
    { value: "custom", label: "Custom Model..." }
  ],
  openai: [
    { value: "gpt-4o", label: "GPT-4o" },
    { value: "gpt-4o-mini", label: "GPT-4o Mini" },
    { value: "gpt-3.5-turbo", label: "GPT-3.5 Turbo" },
    { value: "custom", label: "Custom Model..." }
  ],
  groq: [
    { value: "llama3-8b-8192", label: "Llama 3 8B (Groq)" },
    { value: "llama3-70b-8192", label: "Llama 3 70B (Groq)" },
    { value: "mixtral-8x7b-32768", label: "Mixtral 8x7b (Groq)" },
    { value: "custom", label: "Custom Model..." }
  ],
  ollama: [
    { value: "llama3", label: "Llama 3 (Ollama)" },
    { value: "mistral", label: "Mistral (Ollama)" },
    { value: "gemma", label: "Gemma (Ollama)" },
    { value: "custom", label: "Custom Model..." }
  ],
  anthropic: [
    { value: "claude-3-5-sonnet-20240620", label: "Claude 3.5 Sonnet" },
    { value: "claude-3-opus-20240229", label: "Claude 3 Opus" },
    { value: "custom", label: "Custom Model..." }
  ],
  custom: [
    { value: "custom", label: "Custom Model..." }
  ]
};

const PROMPT_PRESETS = [
  "Detect brute force login attacks and isolate the offender IP.",
  "Identify if any database connections or service outages happened yesterday.",
  "Audit user activities to find access to sensitive resources.",
  "Analyze high latency or performance warning spikes in API gateway."
];

export default function App() {
  // Authentication states
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [authMode, setAuthMode] = useState('login'); 
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [authError, setAuthError] = useState('');

  // Config parameters
  const [prompt, setPrompt] = useState(() => localStorage.getItem('sentinel_forge_prompt') || PROMPT_PRESETS[0]);
  const [logs, setLogs] = useState(''); // Empty by default - no fake logs!
  const [logFormat, setLogFormat] = useState(() => localStorage.getItem('sentinel_forge_log_format') || "Syslog");
  const [provider, setProvider] = useState(() => localStorage.getItem('sentinel_forge_provider') || "ollama");
  const [model, setModel] = useState(() => localStorage.getItem('sentinel_forge_model') || "llama3");
  const [customModel, setCustomModel] = useState(() => localStorage.getItem('sentinel_forge_custom_model') || "");
  const [apiUrl, setApiUrl] = useState(() => localStorage.getItem('sentinel_forge_api_url') || import.meta.env.VITE_API_URL || "http://localhost:8000");
  const [systemMode, setSystemMode] = useState("OFFLINE"); 
  const [liveLogUrl, setLiveLogUrl] = useState(() => localStorage.getItem('sentinel_forge_live_log_url') || "");
  const [isPolling, setIsPolling] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  // Custom models fetching states
  const [fetchedModels, setFetchedModels] = useState(() => {
    try {
      const saved = localStorage.getItem('sentinel_forge_fetched_models_map');
      return saved ? JSON.parse(saved) : {};
    } catch (e) {
      return {};
    }
  });
  const [fetchingModels, setFetchingModels] = useState(false);
  const [fetchError, setFetchError] = useState("");

  useEffect(() => {
    localStorage.setItem('sentinel_forge_prompt', prompt);
  }, [prompt]);

  useEffect(() => {
    localStorage.setItem('sentinel_forge_log_format', logFormat);
  }, [logFormat]);

  useEffect(() => {
    localStorage.setItem('sentinel_forge_provider', provider);
  }, [provider]);

  useEffect(() => {
    localStorage.setItem('sentinel_forge_model', model);
  }, [model]);

  useEffect(() => {
    localStorage.setItem('sentinel_forge_custom_model', customModel);
  }, [customModel]);

  useEffect(() => {
    localStorage.setItem('sentinel_forge_api_url', apiUrl);
  }, [apiUrl]);

  useEffect(() => {
    localStorage.setItem('sentinel_forge_live_log_url', liveLogUrl);
  }, [liveLogUrl]);

  useEffect(() => {
    localStorage.setItem('sentinel_forge_fetched_models_map', JSON.stringify(fetchedModels));
  }, [fetchedModels]);

  const [apiKeys, setApiKeys] = useState(() => {
    try {
      const saved = localStorage.getItem('sentinel_forge_api_keys');
      return saved ? JSON.parse(saved) : { gemini: '', openai: '', groq: '', anthropic: '', custom: '' };
    } catch (e) {
      return { gemini: '', openai: '', groq: '', anthropic: '', custom: '' };
    }
  });

  useEffect(() => {
    localStorage.setItem('sentinel_forge_api_keys', JSON.stringify(apiKeys));
  }, [apiKeys]);

  const [apiBaseUrls, setApiBaseUrls] = useState(() => {
    const defaults = {
      gemini: 'https://generativelanguage.googleapis.com',
      openai: 'https://api.openai.com/v1',
      groq: 'https://api.groq.com/openai/v1',
      ollama: 'http://localhost:11434/v1',
      anthropic: 'https://api.anthropic.com/v1',
      custom: 'http://localhost:1234/v1'
    };
    try {
      const saved = localStorage.getItem('sentinel_forge_api_base_urls');
      if (saved) {
        const parsed = JSON.parse(saved);
        const merged = { ...defaults };
        Object.keys(defaults).forEach(key => {
          if (parsed[key] !== undefined && parsed[key] !== '') {
            let val = parsed[key];
            if (val.includes("locathost")) {
              val = val.replace("locathost", "localhost");
            }
            merged[key] = val;
          }
        });
        return merged;
      }
      return defaults;
    } catch (e) {
      return defaults;
    }
  });

  useEffect(() => {
    localStorage.setItem('sentinel_forge_api_base_urls', JSON.stringify(apiBaseUrls));
  }, [apiBaseUrls]);

  const providerFetchedModels = fetchedModels[provider] || [];

  const modelOptions = React.useMemo(() => {
    const defaults = PROVIDER_MODELS[provider] || [];
    if (providerFetchedModels.length > 0) {
      const fetchedOpts = providerFetchedModels.map(m => ({ value: m, label: m }));
      const standard = defaults.filter(d => d.value !== 'custom');
      const combined = [...standard];
      fetchedOpts.forEach(opt => {
        if (!combined.some(c => c.value === opt.value)) {
          combined.push(opt);
        }
      });
      if (defaults.some(d => d.value === 'custom')) {
        combined.push({ value: "custom", label: "Custom Model..." });
      }
      return combined;
    }
    return defaults;
  }, [provider, providerFetchedModels]);

  useEffect(() => {
    if (modelOptions && modelOptions.length > 0) {
      const exists = modelOptions.some(m => m.value === model);
      if (!exists) {
        setModel(modelOptions[0].value);
      }
    }
  }, [provider, modelOptions]);

  const fetchCustomModels = async () => {
    let baseUrl = apiBaseUrls[provider];
    if (!baseUrl) {
      if (provider === "openai") baseUrl = "https://api.openai.com/v1";
      else if (provider === "groq") baseUrl = "https://api.groq.com/openai/v1";
      else if (provider === "ollama") baseUrl = "http://localhost:11434/v1";
      else if (provider === "anthropic") baseUrl = "https://api.anthropic.com/v1";
      else if (provider === "gemini") baseUrl = "https://generativelanguage.googleapis.com";
      else if (provider === "custom") baseUrl = "http://localhost:1234/v1";
      else {
        setFetchError("Please configure the Endpoint base URL first.");
        return;
      }
    }
    
    setFetchingModels(true);
    setFetchError("");
    
    const isBaseUrlLocal = baseUrl.includes("localhost") || baseUrl.includes("127.0.0.1") || baseUrl.includes("::1");
    const isOrchestratorLocal = apiUrl && (apiUrl.includes("localhost") || apiUrl.includes("127.0.0.1") || apiUrl.includes("::1"));
    const canProxy = apiUrl && (!isBaseUrlLocal || isOrchestratorLocal);
    
    // 1. Try fetching via Orchestrator (avoids browser CORS issues for cloud providers)
    if (canProxy) {
      addConsoleLog(`Requesting model list for ${provider} via Orchestrator: ${apiUrl}...`, 'info');
      try {
        const cleanApiUrl = apiUrl.replace(/\/+$/, "");
        const response = await fetch(`${cleanApiUrl}/list-models`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            provider,
            api_key: apiKeys[provider] || null,
            api_base_url: baseUrl || null
          })
        });
        
        if (response.ok) {
          const data = await response.json();
          if (data && Array.isArray(data.models) && data.models.length > 0) {
            setFetchedModels(prev => ({ ...prev, [provider]: data.models }));
            setModel(data.models[0]);
            addConsoleLog(`Successfully loaded ${data.models.length} models for ${provider} via Orchestrator.`, 'success');
            setFetchingModels(false);
            return;
          }
        }
      } catch (err) {
        console.warn("Orchestrator list-models failed, falling back to direct fetch:", err);
      }
    }
    
    // 2. Direct Browser Fetch Fallback (for localhost or if orchestrator request fails)
    addConsoleLog(`Attempting direct browser fetch from ${provider} endpoint: ${baseUrl}...`, 'info');
    let modelsFound = [];
    
    if (provider === "gemini") {
      try {
        const apiKey = apiKeys.gemini;
        if (!apiKey) {
          setFetchError("Gemini API key is required to load models.");
          setFetchingModels(false);
          return;
        }
        const url = `${baseUrl.replace(/\/$/, "")}/v1beta/models?key=${apiKey}`;
        const res = await fetch(url);
        if (res.ok) {
          const data = await res.json();
          if (data && Array.isArray(data.models)) {
            modelsFound = data.models.map(m => m.name.replace("models/", "")).filter(Boolean);
          }
        } else {
          console.warn("Gemini fetch failed with status:", res.status);
        }
      } catch (e) {
        console.warn("Gemini fetch error:", e);
      }
    } else if (provider === "anthropic") {
      modelsFound = [
        "claude-3-5-sonnet-20241022",
        "claude-3-5-sonnet-20240620",
        "claude-3-5-haiku-20241022",
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307"
      ];
    } else {
      const headers = {
        "Content-Type": "application/json"
      };
      if (apiKeys[provider]) {
        headers["Authorization"] = `Bearer ${apiKeys[provider]}`;
      }
      
      const tryFetch = async (url) => {
        try {
          const res = await fetch(url, { headers });
          if (res.ok) {
            const data = await res.json();
            if (data && Array.isArray(data.data)) {
              return data.data.map(m => m.id).filter(Boolean);
            }
            if (data && Array.isArray(data.models)) {
              return data.models.map(m => m.name || m.model).filter(Boolean);
            }
            if (Array.isArray(data)) {
              return data.map(m => typeof m === 'object' ? (m.id || m.name) : m).filter(Boolean);
            }
            if (data && typeof data === 'object') {
              if (data.id) return [data.id];
              if (data.model) return [data.model];
            }
          }
        } catch (e) {
          console.warn(`Failed fetch on ${url}:`, e);
        }
        return null;
      };
      
      const cleanBaseUrl = baseUrl.replace(/\/$/, "");
      modelsFound = await tryFetch(`${cleanBaseUrl}/models`);
      
      if (!modelsFound || modelsFound.length === 0) {
        modelsFound = await tryFetch(`${cleanBaseUrl}/model`);
      }
      
      if (!modelsFound || modelsFound.length === 0) {
        const rootUrl = cleanBaseUrl.replace(/\/v1$/, "");
        modelsFound = await tryFetch(`${rootUrl}/api/tags`);
      }
    }
    
    if (modelsFound && modelsFound.length > 0) {
      setFetchedModels(prev => ({ ...prev, [provider]: modelsFound }));
      setModel(modelsFound[0]);
      addConsoleLog(`Successfully loaded ${modelsFound.length} models for ${provider}.`, 'success');
    } else {
      const isBaseUrlLocal = baseUrl.includes("localhost") || baseUrl.includes("127.0.0.1") || baseUrl.includes("::1");
      const isWindowRemote = window.location.hostname !== "localhost" && window.location.hostname !== "127.0.0.1";
      
      if (isBaseUrlLocal && isWindowRemote) {
        setFetchError(`Could not retrieve models from local Ollama (${baseUrl}). Since you are running the app from a remote domain (${window.location.hostname}), browser security requires Ollama to be started with OLLAMA_ORIGINS="*" env variable. Alternatively, run the desktop setup app to bypass CORS.`);
        addConsoleLog(`⚠️ CORS Block: To connect to local Ollama from a remote web app, restart Ollama with environment variable: set OLLAMA_ORIGINS=*`, 'warning');
      } else {
        setFetchError(`Could not retrieve models from ${baseUrl}. Ensure the endpoint is active, running, and spelling is correct.`);
        addConsoleLog(`⚠️ Failed to load models for ${provider} from ${baseUrl}. Check network logs or spelling.`, 'warning');
      }
    }
    setFetchingModels(false);
  };


  // Active Tab
  const [activeTab, setActiveTab] = useState("DASHBOARD"); // DASHBOARD | SIMULATOR

  // Pipeline execution state
  const [pipelineRunning, setPipelineRunning] = useState(false);
  const [consoleLogs, setConsoleLogs] = useState([]);
  const [activeStep, setActiveStep] = useState(null); 
  const [stepStatuses, setStepStatuses] = useState({
    intent: 'IDLE',
    data: 'IDLE',
    analysis: 'IDLE',
    report: 'IDLE',
    response: 'IDLE'
  });
  
  // Reports & Mitigation
  const [finalReport, setFinalReport] = useState(null);
  const [mitigationActions, setMitigationActions] = useState([]);
  const [metrics, setMetrics] = useState(null);

  // System states for Offline/Online switching retention
  const [offlineState, setOfflineState] = useState({
    logs: '',
    consoleLogs: [],
    finalReport: null,
    metrics: null,
    stepStatuses: { intent: 'IDLE', data: 'IDLE', analysis: 'IDLE', report: 'IDLE', response: 'IDLE' },
    activeStep: null
  });
  
  const [onlineState, setOnlineState] = useState({
    logs: '',
    consoleLogs: [],
    finalReport: null,
    metrics: null,
    stepStatuses: { intent: 'IDLE', data: 'IDLE', analysis: 'IDLE', report: 'IDLE', response: 'IDLE' },
    activeStep: null,
    liveLogUrl: '',
    isPolling: false
  });

  // Simulator parameters
  const [simScenario, setSimScenario] = useState("Normal System Activity");
  const [simFormat, setSimFormat] = useState("Syslog");
  const [simRate, setSimRate] = useState(5);
  const [simLogs, setSimLogs] = useState("");
  const [isSimulating, setIsSimulating] = useState(false);
  const [simCustomIp, setSimCustomIp] = useState("");
  const [simCustomUser, setSimCustomUser] = useState("");
  const [simulatedCount, setSimulatedCount] = useState(0);
  const [simulatedAnomalies, setSimulatedAnomalies] = useState(0);
  const consoleEndRef = useRef(null);

  // Scroll console
  useEffect(() => {
    if (consoleEndRef.current) {
      consoleEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [consoleLogs]);

  // Handle Online Monitoring Mode Log Polling
  useEffect(() => {
    let timer = null;
    if (systemMode === "ONLINE" && isPolling && isLoggedIn && liveLogUrl.trim()) {
      addConsoleLog(`🟢 Online Monitoring activated. Polling incoming stream: ${liveLogUrl}`, 'system');
      
      const pollLogs = async () => {
        try {
          addConsoleLog(`Polling live feed from ${liveLogUrl}...`, 'info');
          const response = await fetch(liveLogUrl);
          if (response.ok) {
            const rawText = await response.text();
            if (rawText.trim()) {
              setLogs(rawText);
              addConsoleLog(`[Ingested Live logs]:\n${rawText.slice(0, 150)}...`, 'success');
              
              // Trigger analysis on live data
              await executePipeline(rawText);
            }
          } else {
            throw new Error(`Ingestion failed (status: ${response.status})`);
          }
        } catch (e) {
          if (isSimulating || liveLogUrl.includes("/simulator/logs")) {
            addConsoleLog(`⚠️ Connection to backend simulator failed. Activating client-side sandbox simulation...`, 'warning');
            
            // Generate mock client-side logs for the ingestion loop (eval window 10s)
            const duration = 10;
            const rawText = generateLogsJS(simScenario, simFormat, simRate, duration, simCustomIp, simCustomUser);
            
            setLogs(rawText);
            addConsoleLog(`[Ingested Live logs (Sandbox)]: \n${rawText.slice(0, 150)}...`, 'success');
            
            // Execute the pipeline on the generated log
            await executePipeline(rawText);
          } else {
            addConsoleLog(`⚠️ Ingestion error: Failed to connect to stream at ${liveLogUrl} (${e.message})`, 'warning');
            setIsPolling(false);
          }
        }
      };

      pollLogs(); // Initial run
      timer = setInterval(pollLogs, 10000); // Poll every 10 seconds
    }

    return () => {
      if (timer) clearInterval(timer);
    };
  }, [systemMode, isPolling, isLoggedIn, liveLogUrl, prompt, provider, model, customModel, apiBaseUrls, apiUrl, isSimulating, simScenario, simFormat, simRate, simCustomIp, simCustomUser]);

  // Restore session on mount
  useEffect(() => {
    const token = localStorage.getItem('session_token');
    const storedUser = localStorage.getItem('username');
    if (token && storedUser) {
      setIsLoggedIn(true);
      setUsername(storedUser);
    }
  }, []);

  // Simulator loop
  useEffect(() => {
    let timer = null;
    if (isSimulating) {
      const fetchSimLogs = async () => {
        try {
          const cleanApiUrl = apiUrl.replace(/\/+$/, "");
          const url = `${cleanApiUrl}/simulator/logs?scenario=${encodeURIComponent(simScenario)}&format=${simFormat}&rate=${simRate}&duration=5` + 
                      (simCustomIp ? `&ip=${simCustomIp}` : "") + 
                      (simCustomUser ? `&user=${simCustomUser}` : "");
                      
          const response = await fetch(url);
          if (response.ok) {
            const rawText = await response.text();
            setSimLogs(prev => {
              const lines = prev.split("\n").filter(Boolean);
              const newLines = rawText.split("\n").filter(Boolean);
              const combined = [...lines, ...newLines].slice(-100); // Keep last 100 logs
              return combined.join("\n");
            });
            
            const count = rawText.split("\n").filter(Boolean).length;
            setSimulatedCount(prev => prev + count);
            
            // Increment anomalies based on scenario
            if (simScenario !== "Normal System Activity") {
              setSimulatedAnomalies(prev => prev + Math.ceil(count * 0.15));
            }
            
            // If in ONLINE mode and polling the simulator url, update the main logs area
            if (systemMode === "ONLINE" && isPolling && liveLogUrl.includes("/simulator/logs")) {
              setLogs(rawText);
            }
          } else {
            throw new Error(`Server status ${response.status}`);
          }
        } catch (e) {
          console.error("Simulation connection failed, running client-side fallback:", e);
          const duration = 5;
          const rawText = generateLogsJS(simScenario, simFormat, simRate, duration, simCustomIp, simCustomUser);
          
          setSimLogs(prev => {
            const lines = prev.split("\n").filter(Boolean);
            const newLines = rawText.split("\n").filter(Boolean);
            const combined = [...lines, ...newLines].slice(-100);
            return combined.join("\n");
          });
          
          const count = rawText.split("\n").filter(Boolean).length;
          setSimulatedCount(prev => prev + count);
          
          if (simScenario !== "Normal System Activity") {
            setSimulatedAnomalies(prev => prev + Math.ceil(count * 0.15));
          }
          
          if (systemMode === "ONLINE" && isPolling && liveLogUrl.includes("/simulator/logs")) {
            setLogs(rawText);
          }
        }
      };
      
      fetchSimLogs();
      timer = setInterval(fetchSimLogs, 5000); // Generate every 5 seconds
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isSimulating, simScenario, simFormat, simRate, simCustomIp, simCustomUser, systemMode, isPolling, liveLogUrl]);

  const addConsoleLog = (message, type = 'info') => {
    setConsoleLogs(prev => [...prev, {
      timestamp: new Date().toLocaleTimeString(),
      message,
      type
    }]);
  };

  // Auth Submit connected to PostgreSQL backend
  const handleAuthSubmit = async (e) => {
    e.preventDefault();
    setAuthError('');
    if (!username || !password) {
      setAuthError('Please fill in all credentials.');
      return;
    }
    
    try {
      const cleanApiUrl = apiUrl.replace(/\/+$/, "");
      const endpoint = authMode === 'login' ? '/auth/login' : '/auth/signup';
      const response = await fetch(`${cleanApiUrl}${endpoint}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username,
          password,
          email: authMode === 'signup' ? email : "guest@sentinelforge.ai"
        })
      });
      
      const result = await response.json();
      if (!response.ok) {
        setAuthError(result.detail || 'Authentication failed.');
        return;
      }
      
      setIsLoggedIn(true);
      localStorage.setItem('session_token', result.token || 'authenticated');
      localStorage.setItem('username', username);
      addConsoleLog(`🔒 User ${username} authenticated successfully via backend.`, 'success');
    } catch (err) {
      // Offline fallback for development when orchestrator is not running
      if (username === 'admin' && password === 'admin') {
        setIsLoggedIn(true);
        localStorage.setItem('session_token', 'token_admin');
        localStorage.setItem('username', 'admin');
        addConsoleLog(`🔒 User admin authenticated via offline fallback.`, 'success');
      } else {
        setAuthError(`Connection to authentication service failed: ${err.message}`);
      }
    }
  };

  // File Upload Handlers
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      readFile(file);
    }
  };

  const readFile = (file) => {
    setFinalReport(null);
    setMitigationActions([]);
    setMetrics(null);
    setConsoleLogs([]);
    setStepStatuses({
      intent: 'IDLE',
      data: 'IDLE',
      analysis: 'IDLE',
      report: 'IDLE',
      response: 'IDLE'
    });

    const reader = new FileReader();
    reader.onload = (event) => {
      setLogs(event.target.result);
      addConsoleLog(`📂 Uploaded log file: ${file.name} (${file.size} bytes) successfully.`, 'success');
    };
    reader.readAsText(file);
  };

  // Drag and drop handlers
  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      readFile(e.dataTransfer.files[0]);
    }
  };

  const handleTogglePolling = () => {
    if (!isPolling) {
      if (!liveLogUrl.trim()) {
        const inputUrl = prompt("Please configure the URL of the incoming logs stream:", "http://localhost:8000/live-logs");
        if (inputUrl && inputUrl.trim()) {
          setLiveLogUrl(inputUrl.trim());
          setLogs("");
          setFinalReport(null);
          setMetrics(null);
          setConsoleLogs([]);
          setIsPolling(true);
        } else {
          alert("A valid URL is required to start the live ingestion feed.");
        }
      } else {
        setLogs("");
        setFinalReport(null);
        setMetrics(null);
        setConsoleLogs([]);
        setIsPolling(true);
      }
    } else {
      setIsPolling(false);
    }
  };

  // Export helper functions
  const exportAsJSON = (data, filename) => {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
  };

  const exportAsTXT = (text, filename) => {
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
  };

  const exportAsCSV = (headers, rows, filename) => {
    let csvContent = headers.join(",") + "\n";
    rows.forEach(row => {
      csvContent += row.map(val => `"${val.toString().replace(/"/g, '""')}"`).join(",") + "\n";
    });
    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    link.click();
  };

  // Retention toggler between Online & Offline state systems
  const toggleSystemMode = (mode) => {
    if (systemMode === mode) return;
    
    // Save current active parameters into the previous system context
    if (systemMode === "OFFLINE") {
      setOfflineState({
        logs,
        consoleLogs,
        finalReport,
        metrics,
        stepStatuses,
        activeStep
      });
    } else {
      setOnlineState({
        logs,
        consoleLogs,
        finalReport,
        metrics,
        stepStatuses,
        activeStep,
        liveLogUrl,
        isPolling
      });
    }
    
    // Load active settings from the new target context
    if (mode === "OFFLINE") {
      const s = offlineState;
      setSystemMode("OFFLINE");
      setIsPolling(false);
      setLogs(s.logs);
      setConsoleLogs(s.consoleLogs);
      setFinalReport(s.finalReport);
      setMitigationActions([]);
      setMetrics(s.metrics);
      setStepStatuses(s.stepStatuses);
      setActiveStep(s.activeStep);
      
      addConsoleLog("📂 Offline System mode loaded from local cache.", "system");
      alert("Offline Mode activated. Workspace state restored.");
    } else {
      const s = onlineState;
      setSystemMode("ONLINE");
      setLogs(s.logs);
      setConsoleLogs(s.consoleLogs);
      setFinalReport(s.finalReport);
      setMitigationActions([]);
      setMetrics(s.metrics);
      setStepStatuses(s.stepStatuses);
      setActiveStep(s.activeStep);
      setLiveLogUrl(s.liveLogUrl);
      setIsPolling(s.isPolling);
      
      addConsoleLog("🟢 Online System mode loaded from local cache.", "system");
      
      // Auto-ask configuration if empty
      const targetUrl = s.liveLogUrl || liveLogUrl;
      if (!targetUrl.trim()) {
        const inputUrl = prompt("Please configure the URL of the incoming logs stream:", "http://localhost:8000/live-logs");
        if (inputUrl && inputUrl.trim()) {
          setLiveLogUrl(inputUrl.trim());
        }
      }
    }
  };

  const handlePushToIngestion = () => {
    // 1. Switch to online system mode
    setSystemMode("ONLINE");
    
    // 2. Build the simulator URL
    const cleanApiUrl = apiUrl.replace(/\/+$/, "");
    const simUrl = `${cleanApiUrl}/simulator/logs?scenario=${encodeURIComponent(simScenario)}&format=${simFormat}&rate=${simRate}` + 
                   (simCustomIp ? `&ip=${simCustomIp}` : "") + 
                   (simCustomUser ? `&user=${simCustomUser}` : "");
    setLiveLogUrl(simUrl);
    
    // Sync ingestion format to match simulator format
    setLogFormat(simFormat);
    
    // 3. Clear previous outputs
    setLogs("");
    setFinalReport(null);
    setMitigationActions([]);
    setMetrics(null);
    setConsoleLogs([]);
    setStepStatuses({
      intent: 'IDLE',
      data: 'IDLE',
      analysis: 'IDLE',
      report: 'IDLE',
      response: 'IDLE'
    });
    
    // 4. Start polling & simulator execution loops
    setIsPolling(true);
    setIsSimulating(true);
    
    // 5. Switch active tab back to main dashboard
    setActiveTab("DASHBOARD");
    addConsoleLog(`⚡ Simulator active: Ingesting logs for '${simScenario}' scenario.`, 'system');
  };

  // Pipeline Execution trigger
  const handleStartAnalysis = async () => {
    if (systemMode === "OFFLINE" && !logs.trim()) {
      alert("Please upload a log file first before running the analysis pipeline.");
      addConsoleLog("❌ Error: Missing log inputs. Load a file first.", "warning");
      return;
    }
    // Clear previous logs
    setConsoleLogs([]);
    setFinalReport(null);
    setMetrics(null);
    await executePipeline(logs);
  };

  const executePipeline = async (logsContent) => {
    if (pipelineRunning) return;
    setPipelineRunning(true);
    setStepStatuses({
      intent: 'IDLE',
      data: 'IDLE',
      analysis: 'IDLE',
      report: 'IDLE',
      response: 'IDLE'
    });
    setActiveStep('intent');

    const activeModel = model === 'custom' ? customModel : model;

    addConsoleLog("🚀 Launching Sentinel Forge Log Intelligence pipeline...", 'system');
    addConsoleLog(`Settings -> Provider: ${provider} | Model: ${activeModel}`, 'info');

    try {
      const cleanApiUrl = apiUrl.replace(/\/+$/, "");
      const orchestratorUrl = `${cleanApiUrl}/analyze/stream`;
      addConsoleLog("Connecting to Central Orchestrator stream...", 'info');
      
      const response = await fetch(orchestratorUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          logs_raw: logsContent,
          log_format: logFormat,
          provider,
          model: activeModel,
          api_key: provider !== "ollama" ? apiKeys[provider] : null,
          api_base_url: apiBaseUrls[provider] || null
        })
      });

      if (!response.ok) {
        throw new Error(`Pipeline initialization failed. Server status: ${response.status}`);
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n\n");
        buffer = lines.pop(); 

        for (const rawLine of lines) {
          if (!rawLine.trim()) continue;
          
          const eventMatch = rawLine.match(/^event:\s*(.*)$/m);
          const dataMatch = rawLine.match(/^data:\s*(.*)$/m);

          if (eventMatch && dataMatch) {
            const eventType = eventMatch[1].trim();
            const eventData = JSON.parse(dataMatch[1].trim());

            switch (eventType) {
              case "pipeline_started":
                addConsoleLog(`🟢 Pipeline run ${eventData.run_id} started.`, 'system');
                break;

              case "intent_started":
                setStepStatuses(prev => ({ ...prev, intent: 'RUNNING' }));
                setActiveStep('intent');
                addConsoleLog("Invoking Intent Agent: Parsing query prompt...", 'info');
                break;

              case "intent_completed":
                setStepStatuses(prev => ({ ...prev, intent: 'COMPLETED' }));
                addConsoleLog("Intent Agent completed successfully.", 'success');
                break;

              case "data_started":
                setStepStatuses(prev => ({ ...prev, intent: 'COMPLETED', data: 'RUNNING' }));
                setActiveStep('data');
                addConsoleLog("Invoking Data Agent: Filtering and normalizing logs...", 'info');
                break;

              case "data_completed":
                setStepStatuses(prev => ({ ...prev, data: 'COMPLETED' }));
                addConsoleLog("Data Agent completed successfully.", 'success');
                break;

              case "analysis_started":
                setStepStatuses(prev => ({ ...prev, data: 'COMPLETED', analysis: 'RUNNING' }));
                setActiveStep('analysis');
                addConsoleLog("Invoking Analysis Agent: Evaluating log metrics...", 'info');
                break;

              case "analysis_completed":
                setStepStatuses(prev => ({ ...prev, analysis: 'COMPLETED' }));
                addConsoleLog("Analysis Agent completed successfully.", 'success');
                break;

              case "report_started":
                setStepStatuses(prev => ({ ...prev, analysis: 'COMPLETED', report: 'RUNNING' }));
                setActiveStep('report');
                addConsoleLog("Invoking Report Agent: Compiling security audit report...", 'info');
                break;

              case "report_completed":
                setStepStatuses(prev => ({ ...prev, report: 'COMPLETED' }));
                addConsoleLog("Report Agent completed. Executive summary compiled.", 'success');
                break;

              case "response_started":
                setStepStatuses(prev => ({ ...prev, report: 'COMPLETED', response: 'RUNNING' }));
                setActiveStep('response');
                addConsoleLog("Invoking Response Agent: Generating playbook playbooks...", 'info');
                break;

              case "response_completed":
                setStepStatuses(prev => ({ ...prev, response: 'COMPLETED' }));
                addConsoleLog("Response Agent completed. Mitigation actions compiled.", 'success');
                break;

              case "pipeline_completed":
                setActiveStep(null);
                setFinalReport(eventData.final_report);
                setMitigationActions(eventData.response_actions?.mitigation_actions || []);
                setMetrics({
                  total: logsContent.split('\n').filter(Boolean).length,
                  filtered: eventData.final_report?.affected_resources?.length + 1 || 4,
                  status: eventData.final_report?.status || "Bad"
                });
                addConsoleLog("🏁 Log intelligence processing complete.", 'system');
                break;

              case "pipeline_failed":
                const failedAgent = eventData.agent.toLowerCase();
                setStepStatuses(prev => ({
                  ...prev,
                  [failedAgent]: 'FAILED'
                }));
                setActiveStep(null);
                addConsoleLog(`❌ Pipeline execution failed at ${eventData.agent} Agent: ${eventData.error}`, 'warning');
                setFinalReport({
                  status: "Bad",
                  summary: `❌ Pipeline Execution Failed at ${eventData.agent} Agent\n\nUnable to execute subagent. Error:\n${eventData.error}`,
                  recommendations: `1. **Verify Agent Status**: Make sure the subagent on its designated port (e.g. Intent: 8001, Data: 8002, etc.) is running.\n2. **Check Model Configurations**: Ensure model '${activeModel}' is loaded in Ollama or API keys are valid.\n3. **Docker Logs**: Run \`docker compose logs\` to check for container exceptions.`,
                  affected_resources: []
                });
                setMitigationActions([]);
                setMetrics(null);
                return; 
            }
          }
        }
      }
    } catch (err) {
      addConsoleLog(`❌ Central Orchestrator error: ${err.message}. Please verify the Orchestrator service is running at ${apiUrl}.`, 'warning');
      setStepStatuses(prev => {
        const next = { ...prev };
        if (next.intent === 'RUNNING' || next.intent === 'IDLE') next.intent = 'FAILED';
        else if (next.data === 'RUNNING') next.data = 'FAILED';
        else if (next.analysis === 'RUNNING') next.analysis = 'FAILED';
        else if (next.report === 'RUNNING') next.report = 'FAILED';
        else if (next.response === 'RUNNING') next.response = 'FAILED';
        return next;
      });
      setActiveStep(null);
      setFinalReport({
        status: "Bad",
        summary: "❌ Pipeline Execution Failed\n\nUnable to establish connection with the central Orchestrator service at the configured host.\n\nPlease ensure the backend containers/services are active and check the API Host setting.",
        recommendations: "1. **Verify Backend Status**: Start the Docker containers or FastAPI services.\n2. **Check Host URL**: Adjust the API Host input in the top header if the server runs on a different port.\n3. **Network Configurations**: Ensure there are no firewall or CORS issues blocking the connection.",
        affected_resources: []
      });
      setMitigationActions([]);
      setMetrics(null);
    } finally {
      setPipelineRunning(false);
    }
  };

  // Auth panel view
  if (!isLoggedIn) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-slate-950 font-sans text-slate-100 p-4">
        <div className="w-full max-w-md p-8 sm:p-10 rounded-3xl glassmorphism flex flex-col items-center shadow-2xl relative overflow-hidden backdrop-blur-2xl">
          <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-blue-500 via-indigo-500 to-emerald-500"></div>
          
          <img src="logo.png" className="w-16 h-16 object-contain rounded-2xl mb-4 border border-slate-800" alt="Logo" />
          
          <h1 className="font-display font-bold text-2xl tracking-wide text-white mb-1">SENTINEL FORGE</h1>
          <p className="text-[10px] text-slate-500 mb-8 uppercase tracking-widest font-bold">AI Log Intelligence Portal</p>
 
          <form onSubmit={handleAuthSubmit} className="w-full space-y-4">
            {authError && (
              <div className="text-xs bg-rose-500/10 border border-rose-500/20 text-rose-400 p-3.5 rounded-xl">
                {authError}
              </div>
            )}
 
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Username</label>
              <input 
                type="text" 
                value={username}
                onChange={e => setUsername(e.target.value)}
                className="w-full bg-slate-950/60 border border-slate-800/80 rounded-xl px-4 py-3 text-sm text-slate-200 outline-none focus:border-blue-500/80 focus:ring-2 focus:ring-blue-500/10 transition-all font-sans shadow-inner"
                placeholder="Enter username"
              />
            </div>
 
            {authMode === 'signup' && (
              <div>
                <label className="block text-[10px] font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Email Address</label>
                <input 
                  type="email" 
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full bg-slate-950/60 border border-slate-800/80 rounded-xl px-4 py-3 text-sm text-slate-200 outline-none focus:border-blue-500/80 focus:ring-2 focus:ring-blue-500/10 transition-all font-sans shadow-inner"
                  placeholder="Enter email"
                />
              </div>
            )}
 
            <div>
              <label className="block text-[10px] font-semibold text-slate-400 mb-1.5 uppercase tracking-wider">Password</label>
              <input 
                type="password" 
                value={password}
                onChange={e => setPassword(e.target.value)}
                className="w-full bg-slate-950/60 border border-slate-800/80 rounded-xl px-4 py-3 text-sm text-slate-200 outline-none focus:border-blue-500/80 focus:ring-2 focus:ring-blue-500/10 transition-all font-sans shadow-inner"
                placeholder="Enter password"
              />
            </div>
 
            <button 
              type="submit"
              className="w-full flex items-center justify-center py-3.5 px-4 rounded-xl font-display font-bold text-sm text-white bg-blue-600 hover:bg-blue-500 transition-all shadow-md mt-3"
            >
              <Icons.Lock />
              <span>{authMode === 'login' ? 'Authenticate' : 'Create Account'}</span>
            </button>
          </form>
 
          <div className="mt-8 text-xs text-slate-500 font-medium">
            {authMode === 'login' ? (
              <span>New to Sentinel Forge? <button onClick={() => setAuthMode('signup')} className="text-blue-400 hover:underline">Sign up</button></span>
            ) : (
              <span>Already have an account? <button onClick={() => setAuthMode('login')} className="text-blue-400 hover:underline">Log in</button></span>
            )}
          </div>
        </div>
      </div>
    );
  }
 
  // Dashboard View
  return (
    <div className="flex flex-col h-full font-sans bg-slate-950 text-slate-100">
      
      {/* Header bar */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/40 backdrop-blur-xl relative z-30">
        <div className="flex items-center space-x-3">
          <img src="logo.png" className="w-10 h-10 object-contain rounded-xl border border-slate-800" alt="Logo" />
          <div>
            <h1 className="font-display font-bold text-lg leading-tight tracking-wide bg-gradient-to-r from-blue-400 via-indigo-400 to-emerald-400 bg-clip-text text-transparent">SENTINEL FORGE</h1>
            <span className="text-[10px] uppercase tracking-widest text-slate-500 font-semibold block">AI Log Intelligence Portal</span>
          </div>
        </div>
 
        {/* Configurations & Toggles */}
        <div className="flex items-center space-x-4">
          {/* Active Model Status Badge */}
          <div className="hidden lg:flex items-center space-x-1.5 bg-slate-950/80 px-3 py-1.5 rounded-xl border border-slate-800/80 text-[10px]">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-slate-400">Agent Brain:</span>
            <span className="text-slate-200 font-mono font-semibold capitalize">{provider} ({model})</span>
          </div>
 
          {/* System Mode (Online / Offline) Toggle */}
          <div className="flex items-center p-1 bg-slate-950/80 rounded-xl border border-slate-800/80">
            <button 
              onClick={() => toggleSystemMode("ONLINE")}
              className={`text-[10px] px-3 py-1.5 rounded-lg transition-all font-semibold uppercase tracking-wider ${
                systemMode === "ONLINE" 
                  ? 'bg-gradient-to-r from-blue-600 to-blue-500 text-white shadow-md' 
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              Online
            </button>
            <button 
              onClick={() => toggleSystemMode("OFFLINE")}
              className={`text-[10px] px-3 py-1.5 rounded-lg transition-all font-semibold uppercase tracking-wider ${
                systemMode === "OFFLINE" 
                  ? 'bg-gradient-to-r from-indigo-600 to-indigo-500 text-white shadow-md' 
                  : 'text-slate-500 hover:text-slate-300'
              }`}
            >
              Offline
            </button>
          </div>
 
          <div className="h-4 w-px bg-slate-800"></div>
 
          {/* Settings Toggle */}
          <button 
            onClick={() => setShowSettings(!showSettings)}
            className={`p-2 rounded-xl border transition-all flex items-center space-x-1.5 ${
              showSettings 
                ? 'bg-blue-600/20 border-blue-500/80 text-blue-400 shadow-md' 
                : 'bg-slate-900/60 border-slate-800 text-slate-400 hover:text-slate-200 hover:border-slate-700'
            }`}
            title="Configure LLM & Server Settings"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2">
              <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
            <span className="text-xs font-semibold hidden sm:inline">Settings</span>
          </button>
 
          <button 
            onClick={() => {
              setIsLoggedIn(false);
              localStorage.removeItem('session_token');
              localStorage.removeItem('username');
            }}
            className="text-xs bg-slate-900 border border-slate-800 hover:border-rose-500/40 hover:text-rose-400 px-3 py-1.5 rounded-xl transition-all"
          >
            Log out
          </button>
        </div>
      </header>

      {/* Settings Drawer */}
      {showSettings && (
        <div className="bg-slate-950/90 backdrop-blur-xl border-b border-slate-800/80 px-6 py-5 z-20 relative transition-all duration-300 ease-in-out shadow-2xl">
          <div className="max-w-7xl mx-auto grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-6">
            
            {/* Provider Selection */}
            <div>
              <label className="block text-[10px] font-bold text-slate-400 mb-1.5 uppercase tracking-wider">LLM Provider</label>
              <select 
                value={provider} 
                onChange={e => setProvider(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all cursor-pointer font-sans"
              >
                <option value="gemini">Google Gemini</option>
                <option value="openai">OpenAI GPT</option>
                <option value="groq">Groq Cloud</option>
                <option value="ollama">Ollama (Local)</option>
                <option value="anthropic">Anthropic Claude</option>
                <option value="custom">Custom Provider (OpenAI Compatible)</option>
              </select>
            </div>

             {/* Model Selection */}
             <div className="space-y-3">
               <div>
                 <label className="block text-[10px] font-bold text-slate-400 mb-1.5 uppercase tracking-wider">Model Variant</label>
                 <select 
                   value={model} 
                   onChange={e => setModel(e.target.value)}
                   className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all cursor-pointer font-sans"
                 >
                   {(modelOptions || []).map(m => (
                     <option key={m.value} value={m.value}>{m.label}</option>
                   ))}
                 </select>
               </div>
               {(model === 'custom' || provider === 'custom') && (
                 <div>
                   <label className="block text-[10px] font-bold text-slate-400 mb-1.5 uppercase tracking-wider">Custom Model Identifier</label>
                   <input 
                     type="text"
                     value={customModel}
                     onChange={e => setCustomModel(e.target.value)}
                     placeholder="e.g. llama3.1:latest, gpt-4-32k, my-custom-model"
                     className="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-200 outline-none focus:border-blue-500/80 focus:ring-2 focus:ring-blue-500/10 transition-all font-mono"
                   />
                 </div>
               )}
             </div>

            {/* API Host */}
            <div>
              <label className="block text-[10px] font-bold text-slate-400 mb-1.5 uppercase tracking-wider">Central API Host</label>
              <input 
                type="text"
                value={apiUrl}
                onChange={e => setApiUrl(e.target.value)}
                placeholder="http://localhost:8000"
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 font-mono outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
              />
            </div>

            {/* API Key Input */}
            <div>
              {provider !== "ollama" ? (
                <>
                  <label className="block text-[10px] font-bold text-slate-400 mb-1.5 uppercase tracking-wider">{provider.toUpperCase()} API Key</label>
                  <input 
                    type="password"
                    value={apiKeys[provider] || ""}
                    onChange={e => {
                      const val = e.target.value;
                      setApiKeys(prev => ({ ...prev, [provider]: val }));
                    }}
                    placeholder={`sk-...`}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 font-mono outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
                  />
                </>
              ) : (
                <div className="flex flex-col justify-center h-full pt-4">
                  <span className="text-[10px] text-slate-500 italic">No key required for local Ollama service.</span>
                </div>
              )}
            </div>

            {/* Custom LLM API Endpoint */}
            <div>
              <label className="block text-[10px] font-bold text-slate-400 mb-1.5 uppercase tracking-wider">Custom Endpoint (API Base)</label>
              <input 
                type="text"
                value={apiBaseUrls[provider] || ""}
                onChange={e => {
                  const val = e.target.value;
                  setApiBaseUrls(prev => ({ ...prev, [provider]: val }));
                }}
                placeholder={
                  provider === "gemini" ? "https://generativelanguage.googleapis.com" :
                  provider === "openai" ? "https://api.openai.com/v1" :
                  provider === "groq" ? "https://api.groq.com/openai/v1" :
                  provider === "ollama" ? "http://localhost:11434/v1" :
                  provider === "anthropic" ? "https://api.anthropic.com/v1" :
                  provider === "custom" ? "https://api.your-inference-host.com/v1" : ""
                }
                className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 font-mono outline-none focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20 transition-all"
              />
              {true && (
                <>
                  <button
                    type="button"
                    onClick={fetchCustomModels}
                    disabled={fetchingModels}
                    className="mt-2 w-full flex items-center justify-center space-x-1.5 px-3 py-1.5 bg-blue-600/20 hover:bg-blue-600/30 text-blue-400 border border-blue-500/30 hover:border-blue-500/50 rounded-lg text-[10px] font-semibold transition-all active:scale-[0.98] disabled:opacity-50"
                  >
                    {fetchingModels ? (
                      <>
                        <Icons.Refresh />
                        <span>Loading Models...</span>
                      </>
                    ) : (
                      <span>🔌 Load Models from Endpoint</span>
                    )}
                  </button>
                  {fetchError && (
                    <p className="text-[9px] text-rose-400 mt-1 font-medium">{fetchError}</p>
                  )}
                </>
              )}
            </div>

          </div>
        </div>
      )}

      {/* Tab switcher */}
      <div className="flex px-6 border-b border-slate-800 bg-slate-900/20 backdrop-blur-sm">
        <button 
          onClick={() => setActiveTab("DASHBOARD")}
          className={`px-5 py-3.5 text-xs font-semibold uppercase tracking-wider border-b-2 transition-all ${
            activeTab === "DASHBOARD" ? 'border-blue-500 text-blue-400 bg-blue-500/5' : 'border-transparent text-slate-400 hover:text-slate-300'
          }`}
        >
          🔍 Ingestion & Analysis
        </button>
        <button 
          onClick={() => setActiveTab("SIMULATOR")}
          className={`px-5 py-3.5 text-xs font-semibold uppercase tracking-wider border-b-2 transition-all ${
            activeTab === "SIMULATOR" ? 'border-indigo-500 text-indigo-400 bg-indigo-500/5' : 'border-transparent text-slate-400 hover:text-slate-300'
          }`}
        >
          ⚡ Live Log Simulator
        </button>
      </div>

      {activeTab === "DASHBOARD" ? (
        /* Workspace Panel */
        <main className="flex-1 grid grid-cols-12 gap-6 p-6 overflow-hidden">
        
        {/* Left Side: Log Ingestion & Prompt */}
        <section className="col-span-4 flex flex-col space-y-6 overflow-hidden">
          
          {/* Natural Language Prompt Intent */}
          <div className="p-5 rounded-2xl glassmorphism flex flex-col space-y-4">
            <div className="flex items-center space-x-2">
              <div className="p-1.5 bg-blue-500/10 text-blue-400 rounded-lg">
                <Icons.Terminal />
              </div>
              <h2 className="font-display font-semibold text-sm">Define Intent Analysis Prompt</h2>
            </div>
            
            <textarea 
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              rows={3}
              placeholder="What do you want to find in the logs?"
              className="w-full bg-slate-950/60 border border-slate-800/80 rounded-xl p-3.5 text-xs outline-none focus:border-blue-500/80 focus:ring-2 focus:ring-blue-500/10 text-slate-200 placeholder:text-slate-500 font-sans resize-none transition-all shadow-inner leading-relaxed"
            />
            
            <div className="flex flex-wrap gap-1.5">
              {PROMPT_PRESETS.map((p, idx) => (
                <button 
                  key={idx}
                  onClick={() => setPrompt(p)}
                  className={`text-[10px] px-2.5 py-1 rounded-full border transition-all ${prompt === p ? 'bg-blue-600/15 border-blue-500/30 text-blue-400 font-semibold' : 'bg-slate-900/50 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'}`}
                >
                  Preset {idx + 1}
                </button>
              ))}
            </div>
          </div>

          {/* Log Upload Workspace */}
          <div className="flex-1 p-5 rounded-2xl glassmorphism flex flex-col space-y-4 overflow-hidden">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="p-1.5 bg-indigo-500/10 text-indigo-400 rounded-lg">
                  <Icons.Activity />
                </div>
                <h2 className="font-display font-semibold text-sm">Log Dataset Workspace</h2>
              </div>
              
              <select 
                value={logFormat}
                onChange={e => setLogFormat(e.target.value)}
                className="bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1 text-[10px] text-slate-400 outline-none cursor-pointer hover:border-slate-700"
              >
                <option value="Syslog">Syslog RFC 3164</option>
                <option value="Windows Event Logs">Windows Event</option>
                <option value="Nginx">Nginx Logs</option>
                <option value="Apache">Apache Logs</option>
                <option value="Linux Auth Logs">Linux Auth</option>
                <option value="Firewall Logs">Firewall Logs</option>
                <option value="JSON">JSON Loglines</option>
                <option value="CSV">CSV Comma Separated</option>
                <option value="XML">XML Structured</option>
                <option value="TXT">Plain TXT</option>
              </select>
            </div>

            {/* Offline Ingestion Layout */}
            {systemMode === "OFFLINE" ? (
              <>
                {!logs ? (
                  <div 
                    onDragEnter={handleDrag}
                    onDragOver={handleDrag}
                    onDragLeave={handleDrag}
                    onDrop={handleDrop}
                    className={`flex-1 border border-dashed rounded-xl flex flex-col items-center justify-center p-4 sm:p-5 text-center transition-all duration-300 ${
                      dragActive 
                        ? 'border-blue-500 bg-blue-500/10 shadow-[0_0_25px_rgba(59,130,246,0.15)] animate-pulse' 
                        : 'border-slate-800/80 bg-slate-950/40 hover:border-slate-700/60 hover:bg-slate-950/60'
                    }`}
                  >
                    <div className="p-2 bg-blue-500/10 text-blue-400 rounded-xl mb-2 shadow-inner">
                      <Icons.Upload className="w-5 h-5 text-blue-400" />
                    </div>
                    <span className="text-xs font-semibold text-slate-300">Forensic Log Ingestion Target</span>
                    <span className="text-[10px] text-slate-500 mt-1 max-w-[200px] leading-relaxed">
                      Drag & drop server log files here, or browse local volumes.
                    </span>
                    
                    <input 
                      type="file" 
                      accept=".log,.txt,.json,.csv,.xml" 
                      onChange={handleFileUpload} 
                      id="log-file" 
                      className="hidden" 
                    />
                    <label 
                      htmlFor="log-file" 
                      className="mt-3.5 px-5 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-xl text-xs font-semibold cursor-pointer transition-all duration-200 shadow-md hover:shadow-lg hover:shadow-blue-500/10 active:scale-[0.98] inline-flex items-center space-x-1.5 border border-blue-500/20"
                    >
                      <svg className="w-3.5 h-3.5 text-blue-100" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth="2.5">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4-4m0 0l-4 4m4-4v12" />
                      </svg>
                      <span>Choose File</span>
                    </label>
                  </div>
                ) : (
                  <div className="flex-1 flex flex-col space-y-2 overflow-hidden">
                    <div className="flex items-center justify-between text-[10px] text-slate-400">
                      <span>Forensic Log Data loaded:</span>
                      <button 
                        onClick={() => setLogs("")}
                        className="text-rose-400 hover:text-rose-300 font-semibold hover:underline"
                      >
                        Clear File
                      </button>
                    </div>
                    <textarea 
                      value={logs}
                      onChange={e => setLogs(e.target.value)}
                      className="flex-1 w-full bg-slate-950/80 border border-slate-800/80 rounded-xl p-3.5 text-[10px] font-mono outline-none focus:border-blue-500/80 focus:ring-2 focus:ring-blue-500/10 text-slate-300 placeholder:text-slate-500 overflow-y-auto resize-none transition-all shadow-inner leading-normal"
                    />
                  </div>
                )}
              </>
            ) : (
              /* Online Ingestion Layout */
              <div className="flex-grow flex flex-col space-y-4">
                <div className="p-4 rounded-xl bg-slate-950/40 border border-slate-800/80 space-y-3.5 shadow-inner backdrop-blur-md">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-300">Stream Channel Address</span>
                    <span className="text-[9px] bg-slate-900 px-1.5 py-0.5 rounded text-slate-500 font-mono">10s Rate</span>
                  </div>
                  <input 
                    type="text" 
                    value={liveLogUrl}
                    onChange={e => setLiveLogUrl(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800/80 rounded-xl px-3 py-2.5 text-xs text-slate-300 outline-none focus:border-blue-500/80 focus:ring-2 focus:ring-blue-500/10 font-mono"
                    placeholder="http://localhost:8000/live-logs"
                  />
                  <div className="flex items-center justify-between pt-1">
                    <span className="text-[10px] text-slate-500">Auto Ingest Sequence active</span>
                    <button 
                      onClick={handleTogglePolling}
                      className={`px-5 py-2.5 rounded-xl text-xs font-semibold transition-all duration-300 ${
                        isPolling 
                          ? 'bg-rose-500/15 border border-rose-500/30 text-rose-400' 
                          : 'bg-blue-600 hover:bg-blue-500 text-white shadow-md'
                      }`}
                    >
                      {isPolling ? 'Terminate Feed' : 'Establish Ingest'}
                    </button>
                  </div>
                </div>

                <div className="flex-1 flex flex-col space-y-2 overflow-hidden">
                  <span className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Live Log Ingestion Feed</span>
                  <textarea 
                    value={logs}
                    readOnly
                    placeholder="Waiting to ingest dynamic live records..."
                    className="flex-1 w-full bg-slate-950/80 border border-slate-800/80 rounded-xl p-3.5 text-[10px] font-mono outline-none text-slate-400 overflow-y-auto resize-none transition-all shadow-inner leading-normal"
                  />
                </div>
              </div>
            )}

            {systemMode === "OFFLINE" && logs && (
              <div className="flex items-center justify-between pt-2">
                <div></div>
                <button 
                  onClick={handleStartAnalysis}
                  disabled={pipelineRunning}
                  className="flex items-center space-x-2 px-5 py-2.5 rounded-xl font-display font-semibold text-xs text-white bg-blue-600 hover:bg-blue-500 disabled:opacity-50 transition-all shadow-md"
                >
                  {pipelineRunning ? 'Analyzing...' : 'Run Agentic Pipeline'}
                </button>
              </div>
            )}
          </div>

        </section>

        {/* Right Side: Agent visual tracing & Results */}
        <section className="col-span-8 flex flex-col space-y-6 overflow-hidden">
          
          {/* Agent Visual Trace Graph */}
          <div className="p-5 rounded-2xl glassmorphism flex flex-col space-y-4">
            <h2 className="font-display font-semibold text-sm">Agent Communication & Workflow Visualizer</h2>
            
            <div className="grid grid-cols-5 gap-4 relative py-3 items-center">
              
              {/* Animated SVG Connector Flow Path */}
              <svg className="absolute inset-x-0 top-1/2 -translate-y-1/2 w-full pointer-events-none z-0 overflow-visible hidden md:block" style={{ height: '6px' }}>
                <defs>
                  <linearGradient id="agent-flow-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#3b82f6" />
                    <stop offset="25%" stopColor="#6366f1" />
                    <stop offset="50%" stopColor="#a855f7" />
                    <stop offset="75%" stopColor="#ec4899" />
                    <stop offset="100%" stopColor="#10b981" />
                  </linearGradient>
                </defs>
                {/* Background trace line */}
                <line 
                  x1="10%" 
                  y1="3" 
                  x2="90%" 
                  y2="3" 
                  stroke="rgba(30, 41, 59, 0.6)" 
                  strokeWidth="2.5" 
                  strokeLinecap="round"
                />
                {/* Foreground animated line */}
                <line 
                  x1="10%" 
                  y1="3" 
                  x2="90%" 
                  y2="3" 
                  stroke="url(#agent-flow-gradient)" 
                  strokeWidth="3" 
                  strokeLinecap="round"
                  strokeDasharray="12 10" 
                  className={pipelineRunning ? "animate-flow opacity-100" : "opacity-30 transition-opacity duration-500"}
                />
              </svg>
              
              {/* Intent Agent Node */}
              <div className={`flex flex-col items-center p-4 rounded-xl border transition-all duration-300 z-10 relative ${
                activeStep === 'intent' ? 'bg-slate-900/95 border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.15)] node-pulse' :
                stepStatuses.intent === 'COMPLETED' ? 'bg-slate-900/95 border-emerald-500/60 shadow-[0_0_15px_rgba(16,185,129,0.1)]' :
                stepStatuses.intent === 'FAILED' ? 'bg-slate-900/95 border-rose-500/60 shadow-[0_0_15px_rgba(244,63,94,0.1)]' : 
                'bg-slate-950/90 border-slate-800/80 opacity-70 hover:opacity-100 hover:border-slate-700'
              }`}>
                <div className={`p-2.5 rounded-lg mb-2 transition-colors duration-300 ${
                  activeStep === 'intent' ? 'bg-blue-500/20 text-blue-400' :
                  stepStatuses.intent === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400' :
                  stepStatuses.intent === 'FAILED' ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-800/60 text-slate-500'
                }`}>
                  <Icons.Terminal />
                </div>
                <span className="font-display font-semibold text-xs text-slate-200">Intent Agent</span>
                <span className={`text-[9px] mt-1.5 font-mono font-semibold px-2 py-0.5 rounded-full ${
                  activeStep === 'intent' ? 'bg-blue-500/10 text-blue-400' :
                  stepStatuses.intent === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400' :
                  stepStatuses.intent === 'FAILED' ? 'bg-rose-500/10 text-rose-400 font-bold' : 'bg-slate-900 text-slate-500'
                }`}>{stepStatuses.intent}</span>
              </div>

              {/* Data Agent Node */}
              <div className={`flex flex-col items-center p-4 rounded-xl border transition-all duration-300 z-10 relative ${
                activeStep === 'data' ? 'bg-slate-900/95 border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.15)] node-pulse' :
                stepStatuses.data === 'COMPLETED' ? 'bg-slate-900/95 border-emerald-500/60 shadow-[0_0_15px_rgba(16,185,129,0.1)]' :
                stepStatuses.data === 'FAILED' ? 'bg-slate-900/95 border-rose-500/60 shadow-[0_0_15px_rgba(244,63,94,0.1)]' : 
                'bg-slate-950/90 border-slate-800/80 opacity-70 hover:opacity-100 hover:border-slate-700'
              }`}>
                <div className={`p-2.5 rounded-lg mb-2 transition-colors duration-300 ${
                  activeStep === 'data' ? 'bg-blue-500/20 text-blue-400' :
                  stepStatuses.data === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400' :
                  stepStatuses.data === 'FAILED' ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-800/60 text-slate-500'
                }`}>
                  <Icons.Server />
                </div>
                <span className="font-display font-semibold text-xs text-slate-200">Data Agent</span>
                <span className={`text-[9px] mt-1.5 font-mono font-semibold px-2 py-0.5 rounded-full ${
                  activeStep === 'data' ? 'bg-blue-500/10 text-blue-400' :
                  stepStatuses.data === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400' :
                  stepStatuses.data === 'FAILED' ? 'bg-rose-500/10 text-rose-400 font-bold' : 'bg-slate-900 text-slate-500'
                }`}>{stepStatuses.data}</span>
              </div>

              {/* Analysis Agent Node */}
              <div className={`flex flex-col items-center p-4 rounded-xl border transition-all duration-300 z-10 relative ${
                activeStep === 'analysis' ? 'bg-slate-900/95 border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.15)] node-pulse' :
                stepStatuses.analysis === 'COMPLETED' ? 'bg-slate-900/95 border-emerald-500/60 shadow-[0_0_15px_rgba(16,185,129,0.1)]' :
                stepStatuses.analysis === 'FAILED' ? 'bg-slate-900/95 border-rose-500/60 shadow-[0_0_15px_rgba(244,63,94,0.1)]' : 
                'bg-slate-950/90 border-slate-800/80 opacity-70 hover:opacity-100 hover:border-slate-700'
              }`}>
                <div className={`p-2.5 rounded-lg mb-2 transition-colors duration-300 ${
                  activeStep === 'analysis' ? 'bg-blue-500/20 text-blue-400' :
                  stepStatuses.analysis === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400' :
                  stepStatuses.analysis === 'FAILED' ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-800/60 text-slate-500'
                }`}>
                  <Icons.Cpu />
                </div>
                <span className="font-display font-semibold text-xs text-slate-200">Analysis Agent</span>
                <span className={`text-[9px] mt-1.5 font-mono font-semibold px-2 py-0.5 rounded-full ${
                  activeStep === 'analysis' ? 'bg-blue-500/10 text-blue-400' :
                  stepStatuses.analysis === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400' :
                  stepStatuses.analysis === 'FAILED' ? 'bg-rose-500/10 text-rose-400 font-bold' : 'bg-slate-900 text-slate-500'
                }`}>{stepStatuses.analysis}</span>
              </div>

              {/* Report Agent Node */}
              <div className={`flex flex-col items-center p-4 rounded-xl border transition-all duration-300 z-10 relative ${
                activeStep === 'report' ? 'bg-slate-900/95 border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.15)] node-pulse' :
                stepStatuses.report === 'COMPLETED' ? 'bg-slate-900/95 border-emerald-500/60 shadow-[0_0_15px_rgba(16,185,129,0.1)]' :
                stepStatuses.report === 'FAILED' ? 'bg-slate-900/95 border-rose-500/60 shadow-[0_0_15px_rgba(244,63,94,0.1)]' : 
                'bg-slate-950/90 border-slate-800/80 opacity-70 hover:opacity-100 hover:border-slate-700'
              }`}>
                <div className={`p-2.5 rounded-lg mb-2 transition-colors duration-300 ${
                  activeStep === 'report' ? 'bg-blue-500/20 text-blue-400' :
                  stepStatuses.report === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400' :
                  stepStatuses.report === 'FAILED' ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-800/60 text-slate-500'
                }`}>
                  <Icons.CheckCircle />
                </div>
                <span className="font-display font-semibold text-xs text-slate-200">Report Agent</span>
                <span className={`text-[9px] mt-1.5 font-mono font-semibold px-2 py-0.5 rounded-full ${
                  activeStep === 'report' ? 'bg-blue-500/10 text-blue-400' :
                  stepStatuses.report === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400' :
                  stepStatuses.report === 'FAILED' ? 'bg-rose-500/10 text-rose-400 font-bold' : 'bg-slate-900 text-slate-500'
                }`}>{stepStatuses.report}</span>
              </div>

              {/* Response Agent Node */}
              <div className={`flex flex-col items-center p-4 rounded-xl border transition-all duration-300 z-10 relative ${
                activeStep === 'response' ? 'bg-slate-900/95 border-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.15)] node-pulse' :
                stepStatuses.response === 'COMPLETED' ? 'bg-slate-900/95 border-emerald-500/60 shadow-[0_0_15px_rgba(16,185,129,0.1)]' :
                stepStatuses.response === 'FAILED' ? 'bg-slate-900/95 border-rose-500/60 shadow-[0_0_15px_rgba(244,63,94,0.1)]' : 
                'bg-slate-950/90 border-slate-800/80 opacity-70 hover:opacity-100 hover:border-slate-700'
              }`}>
                <div className={`p-2.5 rounded-lg mb-2 transition-colors duration-300 ${
                  activeStep === 'response' ? 'bg-blue-500/20 text-blue-400' :
                  stepStatuses.response === 'COMPLETED' ? 'bg-emerald-500/20 text-emerald-400' :
                  stepStatuses.response === 'FAILED' ? 'bg-rose-500/20 text-rose-400' : 'bg-slate-800/60 text-slate-500'
                }`}>
                  <Icons.ShieldAlert />
                </div>
                <span className="font-display font-semibold text-xs text-slate-200">Response Agent</span>
                <span className={`text-[9px] mt-1.5 font-mono font-semibold px-2 py-0.5 rounded-full ${
                  activeStep === 'response' ? 'bg-blue-500/10 text-blue-400' :
                  stepStatuses.response === 'COMPLETED' ? 'bg-emerald-500/10 text-emerald-400' :
                  stepStatuses.response === 'FAILED' ? 'bg-rose-500/10 text-rose-400 font-bold' : 'bg-slate-900 text-slate-500'
                }`}>{stepStatuses.response}</span>
              </div>

            </div>
          </div>

          {/* Metrics, Console & Final Report Area */}
          <div className="flex-1 grid grid-cols-2 gap-6 overflow-hidden">
            
            {/* Real-time agent streaming output console */}
            <div className="p-5 rounded-2xl glassmorphism flex flex-col space-y-4 overflow-hidden shadow-2xl relative">
              <div className="flex items-center justify-between">
                <h2 className="font-display font-semibold text-sm">Real-time Agent Workflow Tracing</h2>
                {isPolling && (
                  <span className="flex items-center text-[9px] text-blue-400 font-semibold bg-blue-500/10 px-2 py-0.5 rounded-full border border-blue-500/20 animate-pulse">
                    <Icons.Refresh />
                    <span>Ingesting Logs</span>
                  </span>
                )}
              </div>
              <div className="flex-1 bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 font-mono text-[10px] overflow-y-auto space-y-2 text-slate-300 shadow-inner leading-relaxed">
                {consoleLogs.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-full text-slate-600 space-y-2">
                    <Icons.Terminal />
                    <span className="text-[10px]">Ready to process log payloads</span>
                  </div>
                ) : (
                  consoleLogs.map((log, index) => (
                    <div key={index} className="flex flex-col border-b border-slate-905/30 pb-1.5 last:border-0">
                      <span className="text-[9px] text-slate-500">[{log.timestamp}]</span>
                      <span className={`pl-2 mt-0.5 leading-relaxed ${
                        log.type === 'system' ? 'text-blue-400 font-semibold' :
                        log.type === 'success' ? 'text-emerald-400' :
                        log.type === 'warning' ? 'text-rose-400' : 'text-slate-300'
                      }`}>
                        {log.message}
                      </span>
                    </div>
                  ))
                )}
                <div ref={consoleEndRef}></div>
              </div>
            </div>

            {/* Final Report & Findings Card */}
            <div className="p-5 rounded-2xl glassmorphism flex flex-col space-y-4 overflow-hidden">
              <div className="flex items-center justify-between">
                <h2 className="font-display font-semibold text-sm">Executive Intelligence Report</h2>
                {finalReport && (
                  <div className="flex space-x-1.5">
                    <button 
                      onClick={() => {
                        const reportText = `SENTINEL FORGE INTEL REPORT\n\nStatus: ${finalReport?.status}\nSummary: ${finalReport?.summary}\nRecommendations: ${finalReport?.recommendations}`;
                        exportAsTXT(reportText, "sentinel_forge_report.txt");
                      }}
                      className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-[9px]"
                    >
                      Export TXT
                    </button>
                    <button 
                      onClick={() => exportAsJSON({ final_report: finalReport, mitigation_actions: mitigationActions }, "sentinel_forge_report.json")}
                      className="px-2 py-0.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-[9px]"
                    >
                      Export JSON
                    </button>
                  </div>
                )}
              </div>
              
              {!finalReport ? (
                <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-slate-800 rounded-xl p-6 text-center">
                  <Icons.Terminal />
                  <span className="text-xs text-slate-500 mt-2">No active report generated. Start the analysis to see results here.</span>
                </div>
              ) : (
                <div className="flex-1 flex flex-col space-y-4 overflow-y-auto pr-1">
                  
                  {/* Status Indicator */}
                  <div className={`flex items-center space-x-3.5 p-4 rounded-xl border transition-all ${
                    finalReport.status === 'Bad' ? 'bg-gradient-to-r from-rose-950/40 to-rose-900/10 border-rose-500/30 text-rose-400 shadow-[0_0_20px_rgba(244,63,94,0.08)]' :
                    finalReport.status === 'Warning' ? 'bg-gradient-to-r from-amber-950/40 to-amber-900/10 border-amber-500/30 text-amber-400 shadow-[0_0_20px_rgba(245,158,11,0.08)]' :
                    'bg-gradient-to-r from-emerald-950/40 to-emerald-900/10 border-emerald-500/30 text-emerald-400 shadow-[0_0_20px_rgba(16,185,129,0.08)]'
                  }`}>
                    {finalReport.status === 'Bad' ? <Icons.ShieldAlert /> : 
                     finalReport.status === 'Warning' ? <Icons.AlertTriangle /> : <Icons.CheckCircle />}
                    <div>
                      <h3 className="font-display font-bold text-xs uppercase tracking-widest">System Threat Status: {finalReport.status}</h3>
                      <span className="text-[9px] text-slate-400 block mt-0.5">Evaluated in real-time by Orchestrator core</span>
                    </div>
                  </div>

                  {/* Summary */}
                  <div className="text-xs bg-slate-950/40 border border-slate-800/80 p-4 rounded-xl shadow-inner backdrop-blur-sm">
                    <h4 className="font-semibold text-slate-200 mb-2 font-display uppercase tracking-wider text-[10px] text-blue-400">Executive Threat Analysis</h4>
                    <div className="text-slate-300 space-y-1 font-sans leading-relaxed">
                      <p>{finalReport.summary.replace(/###/g, '')}</p>
                    </div>
                  </div>

                  {/* Actionable Remediation */}
                  <div className="text-xs bg-slate-950/40 border border-slate-800/80 p-4 rounded-xl shadow-inner backdrop-blur-sm">
                    <h4 className="font-semibold text-slate-200 mb-2 font-display uppercase tracking-wider text-[10px] text-indigo-400">Actionable Remediation Checklist</h4>
                    <div className="text-slate-300 space-y-1 font-sans leading-relaxed whitespace-pre-line">
                      {finalReport.recommendations}
                    </div>
                  </div>

                  {/* Mitigation Playbook (6th Agent) */}
                  {mitigationActions && mitigationActions.length > 0 && (
                    <div className="text-xs bg-slate-950/40 border border-slate-800/80 p-4 rounded-xl shadow-inner backdrop-blur-sm space-y-3">
                      <h4 className="font-semibold text-slate-200 flex items-center justify-between font-display">
                        <span className="uppercase tracking-wider text-[10px] text-emerald-400">🛡️ Automated Mitigation Playbook</span>
                        <span className="text-[8px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded border border-emerald-500/20 uppercase tracking-widest font-bold font-mono">
                          Response Agent
                        </span>
                      </h4>
                      <div className="space-y-3">
                        {mitigationActions.map((action, i) => (
                          <div key={i} className="p-3 rounded-xl bg-slate-950/80 border border-slate-900 space-y-2 hover:border-slate-800 transition-all duration-300">
                            <div className="flex items-center justify-between">
                              <span className="font-semibold text-blue-400 text-[11px] font-mono">{action.action_type}</span>
                              <span className="text-[9px] bg-slate-900 border border-slate-800 text-slate-400 px-2 py-0.5 rounded font-mono uppercase">
                                {action.status}
                              </span>
                            </div>
                            <p className="text-[10px] text-slate-400 font-sans leading-relaxed">{action.description}</p>
                            {action.command && (
                              <div className="flex items-center justify-between bg-slate-900/60 p-2 rounded-lg font-mono text-[9px] text-emerald-400 border border-slate-800/80">
                                <span className="break-all select-all">{action.command}</span>
                                <button 
                                  onClick={() => {
                                    navigator.clipboard.writeText(action.command);
                                    alert("Mitigation command copied to clipboard!");
                                  }}
                                  className="text-slate-400 hover:text-slate-200 font-sans pl-3 text-[9px] hover:underline uppercase tracking-wider font-semibold"
                                >
                                  Copy
                                </button>
                              </div>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* Affected resources */}
                  {finalReport.affected_resources && finalReport.affected_resources.length > 0 && (
                    <div className="text-xs bg-slate-950/20 p-3 rounded-xl border border-slate-900">
                      <h4 className="font-semibold text-slate-400 mb-2 font-display uppercase tracking-wider text-[10px]">Impacted Infrastructures</h4>
                      <div className="flex flex-wrap gap-1.5">
                        {finalReport.affected_resources.map((res, i) => (
                          <span key={i} className="text-[9px] bg-slate-900 px-2.5 py-1 rounded-lg border border-slate-800/80 font-mono text-slate-300">
                            {res}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                </div>
              )}
            </div>

          </div>

        </section>

      </main>
      ) : (
        /* Simulator Panel Layout */
        <main className="flex-1 grid grid-cols-12 gap-6 p-6 overflow-hidden">
          {/* Left Column: Simulator Controls */}
          <div className="col-span-4 flex flex-col space-y-6 overflow-y-auto pr-1">
            <div className="p-5 rounded-2xl glassmorphism space-y-4">
              <h2 className="font-display font-semibold text-sm flex items-center space-x-2">
                <span className="text-indigo-400 text-lg">⚡</span>
                <span>Live Log Simulator Control</span>
              </h2>
              
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase">Attack Scenario</label>
                  <select 
                    value={simScenario}
                    onChange={e => setSimScenario(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2.5 text-xs text-slate-200 outline-none focus:border-indigo-500"
                  >
                    <option value="Normal System Activity">Normal System Activity</option>
                    <option value="Failed Login Attempts">Failed Login Attempts</option>
                    <option value="Brute Force Attacks">Brute Force Attacks</option>
                    <option value="DDoS Traffic Patterns">DDoS Traffic Patterns</option>
                    <option value="Unauthorized Access Attempts">Unauthorized Access Attempts</option>
                    <option value="Malware Indicators">Malware Indicators</option>
                    <option value="Service Crashes">Service Crashes</option>
                    <option value="Database Failures">Database Failures</option>
                    <option value="Memory Spikes">Memory Spikes</option>
                    <option value="CPU Overload">CPU Overload</option>
                    <option value="Disk Exhaustion">Disk Exhaustion</option>
                    <option value="Network Latency Issues">Network Latency Issues</option>
                    <option value="Compliance Violations">Compliance Violations</option>
                    <option value="User Behavior Anomalies">User Behavior Anomalies</option>
                    <option value="Privilege Escalation Attempts">Privilege Escalation Attempts</option>
                    <option value="Mixed Incident Scenarios">Mixed Incident Scenarios</option>
                  </select>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase">Log Format</label>
                    <select 
                      value={simFormat}
                      onChange={e => setSimFormat(e.target.value)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-indigo-500"
                    >
                      <option value="Syslog">Syslog RFC 3164</option>
                      <option value="JSON">JSON Loglines</option>
                      <option value="CSV">CSV format</option>
                      <option value="Nginx">Nginx logs</option>
                      <option value="Apache">Apache logs</option>
                      <option value="Windows Event Logs">Windows Event</option>
                      <option value="Linux Auth Logs">Linux Auth</option>
                      <option value="Firewall Logs">Firewall Logs</option>
                      <option value="TXT">Plain TXT</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-400 mb-1.5 uppercase">Rate (logs/s)</label>
                    <input 
                      type="number"
                      min={1}
                      max={10000}
                      value={simRate}
                      onChange={e => setSimRate(parseInt(e.target.value) || 1)}
                      className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-indigo-500"
                    />
                  </div>
                </div>
              </div>

              {/* Action buttons */}
              <div className="grid grid-cols-2 gap-2 pt-2">
                <button 
                  onClick={() => setIsSimulating(!isSimulating)}
                  className={`w-full py-2.5 rounded-xl text-xs font-semibold transition-all shadow-md active:scale-[0.98] ${
                    isSimulating ? 'bg-amber-600 text-white hover:bg-amber-500' : 'bg-indigo-600 text-white hover:bg-indigo-500'
                  }`}
                >
                  {isSimulating ? '⏸️ Pause Sim' : '▶️ Start Sim'}
                </button>
                <button 
                  onClick={() => {
                    setIsSimulating(false);
                    setSimLogs("");
                    setSimulatedCount(0);
                    setSimulatedAnomalies(0);
                  }}
                  className="w-full py-2.5 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700"
                >
                  ⏹️ Reset
                </button>
              </div>

              <button 
                onClick={handlePushToIngestion}
                className="w-full py-3 rounded-xl text-xs font-bold bg-blue-600 hover:bg-blue-500 text-white shadow-md border border-blue-700/30 transition-all active:scale-[0.98]"
              >
                🚀 Push Logs to Ingestion & Run
              </button>
            </div>

            {/* Custom Scenario Builder */}
            <div className="p-5 rounded-2xl glassmorphism space-y-4">
              <h3 className="font-display font-semibold text-xs text-slate-300 uppercase tracking-wider">Custom Parameter Injector</h3>
              <div className="space-y-3">
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">Target Account User</label>
                  <input 
                    type="text" 
                    value={simCustomUser} 
                    onChange={e => setSimCustomUser(e.target.value)}
                    placeholder="e.g. pratham, root, guest"
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-500 mb-1">Source IP Address</label>
                  <input 
                    type="text" 
                    value={simCustomIp} 
                    onChange={e => setSimCustomIp(e.target.value)}
                    placeholder="e.g. 192.168.1.105, 91.200.12.33"
                    className="w-full bg-slate-900 border border-slate-800 rounded-xl px-3 py-2 text-xs text-slate-200 outline-none focus:border-indigo-500"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Right Column: Console Terminal, Stats & Exports */}
          <div className="col-span-8 flex flex-col space-y-6 overflow-hidden">
            {/* Stats Dashboard */}
            <div className="grid grid-cols-4 gap-4">
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col">
                <span className="text-[10px] text-slate-500 uppercase font-semibold">Logs Generated</span>
                <span className="text-xl font-bold text-indigo-400 mt-1">{simulatedCount.toLocaleString()}</span>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col">
                <span className="text-[10px] text-slate-500 uppercase font-semibold">Rate Status</span>
                <span className="text-xl font-bold text-emerald-400 mt-1">{simRate} / sec</span>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col">
                <span className="text-[10px] text-slate-500 uppercase font-semibold">Simulated Anomalies</span>
                <span className="text-xl font-bold text-rose-400 mt-1">{simulatedAnomalies}</span>
              </div>
              <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-col">
                <span className="text-[10px] text-slate-500 uppercase font-semibold">Simulation Health</span>
                <span className="text-xl font-bold text-blue-400 mt-1">{isSimulating ? 'Active' : 'Idle'}</span>
              </div>
            </div>

            {/* Stream Console */}
            <div className="flex-1 p-5 rounded-2xl glassmorphism flex flex-col space-y-4 overflow-hidden">
              <div className="flex items-center justify-between">
                <h3 className="font-display font-semibold text-sm">Real-time Simulated Stream Console</h3>
                
                {/* Export Dropdown */}
                <div className="flex space-x-2">
                  <button 
                    onClick={() => exportAsTXT(simLogs, "simulated_logs.txt")}
                    className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-[10px] font-semibold"
                  >
                    Export TXT
                  </button>
                  <button 
                    onClick={() => {
                      const records = simLogs.split("\n").filter(Boolean).map(log => [log]);
                      exportAsCSV(["Generated_Log_Line"], records, "simulated_logs.csv");
                    }}
                    className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-[10px] font-semibold"
                  >
                    Export CSV
                  </button>
                  <button 
                    onClick={() => {
                      const logsObj = simLogs.split("\n").filter(Boolean).map((log, idx) => ({ id: idx, raw: log }));
                      exportAsJSON(logsObj, "simulated_logs.json");
                    }}
                    className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded border border-slate-700 text-[10px] font-semibold"
                  >
                    Export JSON
                  </button>
                </div>
              </div>

              <textarea 
                value={simLogs}
                readOnly
                placeholder="Real-time simulated log lines will print here... Click 'Start Sim' to begin."
                className="flex-1 w-full bg-slate-950/80 border border-slate-800/80 rounded-xl p-4 font-mono text-[10px] outline-none text-slate-400 overflow-y-auto resize-none transition-all shadow-inner leading-normal"
              />
            </div>
          </div>
        </main>
      )}

    </div>
  );
}
