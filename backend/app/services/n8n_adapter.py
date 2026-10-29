import os
import hmac
import hashlib
import json
import ipaddress
import urllib.parse
from typing import Dict, Any, Optional
import httpx
from app.core.logging import logger


class N8nAdapter:
    """
    Controlled external webhook adapter for n8n workflow automation.
    Enforces:
    1. Disabled by default (N8N_ENABLED must be 'true')
    2. Strict SSRF protection on destination URLs (rejects private IPs, loopback, metadata services)
    3. HMAC SHA256 signature on payloads for authenticity
    4. Strict timeout (5s) so external outages never block core services
    5. Read-only event telemetry (cannot mutate state or execute arbitrary commands)
    """

    def __init__(self):
        self.enabled = os.getenv("N8N_ENABLED", "false").lower() in ("true", "1", "yes")
        self.webhook_url = os.getenv("N8N_WEBHOOK_URL")
        self.secret = os.getenv("N8N_WEBHOOK_SECRET", "shadowops_n8n_default_secret")

    def _validate_destination_url(self, url: str) -> bool:
        """Validates that destination is an acceptable, non-internal HTTPS/HTTP address."""
        try:
            parsed = urllib.parse.urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            hostname = parsed.hostname
            if not hostname:
                return False
            if hostname in ("localhost", "127.0.0.1", "0.0.0.0", "::1", "metadata.google.internal"):
                return False
            
            # Check if IP address is private/reserved
            try:
                ip = ipaddress.ip_address(hostname)
                if ip.is_private or ip.is_loopback or ip.is_reserved or ip.is_link_local:
                    return False
            except ValueError:
                # Hostname is a domain name, not raw IP
                pass

            return True
        except Exception:
            return False

    def _sign_payload(self, body_bytes: bytes) -> str:
        """Generates HMAC-SHA256 signature of the payload body."""
        return hmac.new(self.secret.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()

    async def dispatch_event(
        self,
        event_type: str,
        workspace_id: str,
        payload: Dict[str, Any],
        correlation_id: str,
    ) -> Dict[str, Any]:
        """Dispatches an event envelope to configured n8n endpoint."""
        if not self.enabled:
            return {
                "status": "disabled",
                "message": "n8n integration is disabled by default. Set N8N_ENABLED=true to activate.",
            }

        if not self.webhook_url:
            return {
                "status": "not_configured",
                "message": "n8n integration is enabled but N8N_WEBHOOK_URL is not set.",
            }

        if not self._validate_destination_url(self.webhook_url):
            logger.warning("n8n_webhook_ssrf_blocked", url=self.webhook_url)
            return {
                "status": "blocked_ssrf",
                "message": f"Webhook destination URL {self.webhook_url} violates SSRF security boundary.",
            }

        data = {
            "event_type": event_type,
            "workspace_id": workspace_id,
            "correlation_id": correlation_id,
            "payload": payload,
        }
        body_bytes = json.dumps(data, sort_keys=True).encode("utf-8")
        signature = self._sign_payload(body_bytes)

        headers = {
            "Content-Type": "application/json",
            "X-ShadowOps-Signature": signature,
            "X-ShadowOps-Event": event_type,
            "User-Agent": "ShadowOps-EventDispatcher/1.0",
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(self.webhook_url, content=body_bytes, headers=headers)
                return {
                    "status": "sent" if res.is_success else "failed",
                    "http_status": res.status_code,
                    "response": res.text[:200],
                }
        except Exception as e:
            logger.error("n8n_webhook_delivery_exception", error=str(e), url=self.webhook_url)
            return {
                "status": "failed",
                "error": str(e),
            }
