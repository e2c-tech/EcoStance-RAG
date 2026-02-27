from langchain_core.tools import tool
import httpx
import logging
import json
from typing import Dict, Any, List, Optional
from ..config import SIEM_API_URL, SIEM_USERNAME, SIEM_PASSWORD

logger = logging.getLogger(__name__)

class SIEMClient:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(SIEMClient, cls).__new__(cls)
            cls._instance.token = None
            # Ensure base_url has a trailing slash for proper joining
            base_url = SIEM_API_URL if SIEM_API_URL.endswith("/") else SIEM_API_URL + "/"
            cls._instance.client = httpx.Client(base_url=base_url, timeout=30.0)
        return cls._instance

    def login(self):
        """Authenticate and get JWT token from SIEM API."""
        try:
            logger.info(f"Attempting SIEM login for user: {SIEM_USERNAME} at {SIEM_API_URL}")
            # Align with OAuth2PasswordRequestForm (form-data)
            payload = {
                "username": SIEM_USERNAME,
                "password": SIEM_PASSWORD,
                "grant_type": "password"
            }
            response = self.client.post("auth/login", data=payload)
            
            if response.status_code != 200:
                # Fallback to JSON if form-data fails (some dev environments use JSON)
                logger.warning(f"SIEM Login form-data failed ({response.status_code}), trying JSON...")
                response = self.client.post("auth/login", json=payload)

            if response.status_code != 200:
                logger.error(f"SIEM Login Failed! Status: {response.status_code} | Response: {response.text}")
                return False
                
            data = response.json()
            # Handle different token structures
            token_obj = data.get("token") or data.get("access_token")
            if isinstance(token_obj, dict):
                self.token = token_obj.get("access_token")
            else:
                self.token = token_obj
            
            if not self.token:
                logger.error(f"SIEM Login succeeded but no token found in response: {data}")
                return False

            logger.info("SIEM Authentication successfully logged in")
            return True
        except Exception as e:
            logger.error(f"SIEM Login exception: {e}")
            return False

    def _get_headers(self):
        if not self.token:
            success = self.login()
            if not success:
                logger.warning("Proceeding with empty/stale token as login failed")
        return {"Authorization": f"Bearer {self.token}"}

    def request(self, method: str, endpoint: str, **kwargs):
        """Make an authenticated request. endpoint should be relative."""
        endpoint = endpoint.lstrip("/")
        headers = self._get_headers()
        try:
            response = self.client.request(method, endpoint, headers=headers, **kwargs)
            
            # If unauthorized, try to re-login once
            if response.status_code == 401:
                logger.info("SIEM request returned 401, attempting re-login...")
                if self.login():
                    headers = self._get_headers()
                    response = self.client.request(method, endpoint, headers=headers, **kwargs)
                else:
                    return {"error": "SIEM Authentication failed. Please check SIEM_USERNAME and SIEM_PASSWORD in .env"}
            
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"SIEM API HTTP Error ({method} {endpoint}): {e.response.status_code} - {e.response.text}")
            return {"error": f"SIEM API Error {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            logger.error(f"SIEM API Unexpected Error: {e}")
            return {"error": f"SIEM API Unexpected Error: {str(e)}"}

siem_client = SIEMClient()

@tool
def search_siem_logs(
    query_text: str, 
    index_pattern: str = "syslog_logs-*", 
    time_range_from: str = "now-24h", 
    time_range_to: str = "now",
    size: int = 50
) -> str:
    """
    Search SIEM logs for specific keywords, errors, or activity. 
    Args:
        query_text: The search term or DSL query.
        index_pattern: The index pattern (e.g., 'syslog_logs-*').
    """
    payload = {
        "index_pattern": index_pattern,
        "size": size,
        "time_range": {"from": time_range_from, "to": time_range_to},
        "query": {"multi_match": {"query": query_text, "fields": ["message", "hostname", "source_ip", "dest_ip"]}}
    }
    result = siem_client.request("POST", "discover/", json=payload)
    return json.dumps(result, indent=2)

@tool
def get_log_volume_stats(
    index_pattern: str = "syslog_logs-*",
    time_period_minutes: int = 60,
    interval: str = "m"
) -> str:
    """Get stats on log volume over time to detect spikes or anomalies."""
    params = {
        "index_pattern": index_pattern,
        "time_period_minutes": time_period_minutes,
        "interval": interval
    }
    result = siem_client.request("GET", "discover/log-counts-over-time", params=params)
    return json.dumps(result, indent=2)

@tool
def get_unique_field_values(
    index_pattern: str,
    fields: List[str]
) -> str:
    """Find unique values for specific fields (e.g., 'hostname', 'dest_ip') to discover active entities."""
    params = {
        "index_pattern": index_pattern,
        "fields": fields
    }
    result = siem_client.request("GET", "discover/unique-values", params=params)
    return json.dumps(result, indent=2)

@tool
def list_siem_indices() -> str:
    """List all available SIEM indices and their sizes to understand data sources."""
    result = siem_client.request("GET", "indices/")
    return json.dumps(result, indent=2)

@tool
def list_security_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None
) -> str:
    """List active security alerts from the SIEM threat detection engine."""
    params = {}
    if status: params["status"] = status
    if severity: params["severity"] = severity
    result = siem_client.request("GET", "security-analytics/alerts", params=params)
    return json.dumps(result, indent=2)

@tool
def list_security_findings(
    detector_id: Optional[str] = None,
    severity: Optional[str] = None
) -> str:
    """List raw security findings (rule matches) that haven't necessarily triggered alerts yet."""
    params = {}
    if detector_id: params["detector_id"] = detector_id
    if severity: params["severity"] = severity
    result = siem_client.request("GET", "security-analytics/findings", params=params)
    return json.dumps(result, indent=2)

@tool
def get_security_correlations(
    finding_id: str
) -> str:
    """Find correlated security events across different log sources for a specific finding."""
    result = siem_client.request("GET", f"security-analytics/correlations/findings", params={"finding_id": finding_id})
    return json.dumps(result, indent=2)

@tool
def acknowledge_siem_alerts(
    alert_ids: List[str]
) -> str:
    """Acknowledge security alerts to mark them as addressed or investigated."""
    payload = {"alertIds": alert_ids}
    result = siem_client.request("POST", "security-analytics/alerts/_acknowledge", json=payload)
    return json.dumps(result, indent=2)

@tool
def update_ip_whitelist(
    ip: str,
    action: str = "add"
) -> str:
    """Add or remove an IP from the SIEM whitelist (Firewall/IPS rules). action: 'add' or 'remove'."""
    if action.lower() == "add":
        payload = {"ip": ip, "description": "Added by Security AI Analyst"}
        result = siem_client.request("POST", "ips/whitelist", json=payload)
    else:
        result = siem_client.request("DELETE", f"ips/whitelist/{ip}")
    return json.dumps(result, indent=2)
