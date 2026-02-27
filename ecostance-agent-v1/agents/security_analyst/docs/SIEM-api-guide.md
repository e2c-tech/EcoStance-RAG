# 🤖 Cyber-AI SIEM API & Service Manual

This document is a comprehensive guide for an **AI Security Agent** to interact with the Corvatte SIEM platform. It details all available REST API endpoints and underlying OpenSearch service logic.

---

## 🔐 1. Authentication & Security
The AI Agent must first authenticate to receive a JWT token. Most endpoints require the `Authorization: Bearer <token>` header.

### Login
- **Endpoint:** `POST /api/v1/auth/login`
- **Body:** `OAuth2PasswordRequestForm` (Form-data: `username`, `password`)
- **Returns:** 
  ```json
  {
    "token": { "access_token": "...", "refresh_token": "...", "token_type": "bearer" },
    "user": { "username": "...", "role": "...", "permissions": [...] }
  }
  ```

### Validate Token
- **Endpoint:** `GET /api/v1/auth/validate-token`
- **Purpose:** Check if the current token is valid and get user permissions.

---

## 🔍 2. Log Discovery & Data Analysis
These are the most important tools for the AI Agent to investigate logs.

### Flexible Log Search
- **Endpoint:** `POST /api/v1/discover/`
- **Payload Schema:**
  ```json
  {
    "index_pattern": "string (e.g., 'syslog_logs-*')",
    "size": 100,
    "from": 0,
    "time_range": { 
        "from": "now-24h", 
        "to": "now" 
    },
    "query": { "match": { "message": "error" } },
    "filters": [
      { 
        "field": "hostname", 
        "value": "server-1", 
        "type": "term",
        "operator": "gte" (only for range type)
      }
    ],
    "sort": [{ "field": "@timestamp", "order": "desc" }],
    "aggs": { "my_agg": { "terms": { "field": "dest_ip" } } },
    "fields": ["@timestamp", "message", "source_ip"]
  }
  ```
- **Capabilities:** Supports full OpenSearch DSL in the `query` field, Date Math (e.g., `now/d`), and aggregations in the `aggs` field.
- **Python Mapping:** Note that `from` is aliased as `from_` in the backend code, but the API expects `from`.

### Log Volume Stats
- **Endpoint:** `GET /api/v1/discover/log-counts-over-time`
- **Query Params:** `index_pattern`, `time_period_minutes`, `interval` (e.g., 'h', 'm')
- **Purpose:** Detect spikes in log volume.

### Field Discovery
- **Endpoint:** `GET /api/v1/discover/unique-values`
- **Query Params:** `index_pattern`, `fields` (list)
- **Purpose:** Find which services or IPs are present in the logs.

---

## 🛡️ 3. Security Analytics (SIEM Plugin)
Interaction with the OpenSearch Security Analytics engine for threat detection.

### Detectors
- **`GET /api/v1/security-analytics/detectors`**: List all active detectors.
- **`POST /api/v1/security-analytics/detectors`**: Create a detector for specific log types (e.g., `windows`, `network`, `syslog`).
- **`POST /api/v1/security-analytics/detectors/_search`**: Search for specific detectors.

### Findings (Raw Matches)
- **`GET /api/v1/security-analytics/findings`**: List every rule match (even if no alert was triggered).
- **`POST /api/v1/security-analytics/findings/_search`**: Filter findings by severity or rule.

### Security Alerts (High Priority)
- **`GET /api/v1/security-analytics/alerts`**: List active security alerts.
- **`POST /api/v1/security-analytics/alerts/_acknowledge`**: Acknowledge alerts (Body: `{"alertIds": ["id1", "id2"]}`).

### Sigma & Detection Rules
- **`GET /api/v1/security-analytics/rules`**: List internal/custom detection rules.
- **`POST /api/v1/security-analytics/rules/_validate`**: Pre-check Sigma YAML syntax.

### Attack Path Correlation
- **`GET /api/v1/security-analytics/correlations`**: Find related events across different log sources using the `start_time` and `end_time` parameters.
- **`GET /api/v1/security-analytics/correlations/findings`**: Finding-to-finding correlation to track lateral movement.

---

## 🔔 4. Traditional Alerting & Monitoring
Standard monitors that check logs for specific thresholds (different from Security Analytics).

### Monitors
- **`POST /api/v1/alerts/monitors`**: Create a monitor.
- **Payload Example:**
  ```json
  {
    "name": "High Error Rate",
    "type": "monitor",
    "schedule": { "period": { "interval": 1, "unit": "MINUTES" } },
    "inputs": [{
      "search": {
        "indices": ["syslog_logs-*"],
        "query": { "query": { "bool": { "filter": [{ "term": { "Severity": "ERROR" } }] } } }
      }
    }],
    "triggers": [{
      "name": "Error Trigger",
      "condition": { "script": { "source": "ctx.results[0].hits.total.value > 10" } },
      "actions": [{ "name": "Notify Admin", "destination_id": "dest_id_here" }]
    }]
  }
  ```
- **`GET /api/v1/alerts/monitors/{id}`**: Get monitor status.

### Notification Channels (Destinations)
- **`GET /api/v1/alerts/channels`**: List where alerts are sent.
- **`POST /api/v1/alerts/channels`**: Create a destination.
  ```json
  {
    "name": "Admin Webhook",
    "type": "custom_webhook",
    "webhook": { "url": "https://api.example.com/notify" }
  }
  ```

---

## 📊 5. Index & Lifecycle Management
Tools for managing the underlying data storage.

### Indices
- **`GET /api/v1/indices/`**: List all OpenSearch indices and their stats (size, document count).
- **`POST /api/v1/indices/`**: Create a new index with custom mappings.

### ISM (Index State Management) Policies
- **`GET /api/v1/ism/policies`**: List data retention policies.
- **`POST /api/v1/ism/policies/attach`**: Apply a policy (e.g., "Delete after 30 days") to an index pattern.

---

## 🛠️ 6. System Administration & IPS
Access control and firewall integration.

### User & Role Management
- **`GET /api/v1/users/`**: List registered analysts/admins.
- **`GET /api/v1/roles/`**: List roles and their associated permissions.
- **`GET /api/v1/roles/permissions`**: Get a list of all 20+ permissions available in the SIEM.

### IPS Whitelisting (Firewall Rules)
- **`POST /api/v1/ips/whitelist`**: Add an IP to the whitelist. On Linux, this automatically updates `iptables` rules for ports 24224 and 6514.
- **`DELETE /api/v1/ips/whitelist/{ip}`**: Revoke access for an IP.

---

## 📋 7. Diagnostics
- **`GET /api/v1/diagnostics/logs`**: Read the last N lines of the backend server logs (`nohup.out`) to debug the SIEM itself.

---

## ⚙️ 8. OpenSearch Service Internal Logic
The `opensearch_service.py` provides high-level abstractions that the AI can invoke when performing advanced analysis:

1.  **`fetch_logs(request: DiscoverRequest)`**: The master function for querying logs. It handles security filtering by `client_id` automatically.
2.  **`get_unique_field_values(...)`**: Uses `terms` aggregations to find all unique entities (IPs, users, servers) in a time window.
3.  **Security Analytics Wrappers**: Provides direct calls to the OpenSearch SIEM plugin API for complex operations like `validate_security_rule` and `get_correlated_findings`.

---

### 💡 AI Best Practices for API Usage:
1.  **Iterative Discovery:** Start by listing indices (`GET /indices`) to see what data is available.
2.  **Context Building:** Use `GET /unique-values` to see which hostnames or IPs are most active before running a detailed `POST /discover` search.
3.  **Incident Reconstruction:** When an alert is found, use `GET /correlations/findings` to find other logs related to that specific event.
4.  **Error Prevention:** Always validate custom rules with `POST /rules/_validate` before attempting to save them.
