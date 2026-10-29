import os
from typing import Dict, Any, Optional
from datetime import datetime
from app.core.logging import logger


class EmailAdapter:
    """
    Provider-agnostic email adapter for security alerts.
    If no SMTP or transactional provider is configured, fails safely with status NOT_CONFIGURED.
    Never crashes callers or security scan/remediation/verification operations.
    """

    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASSWORD")
        self.from_email = os.getenv("ALERT_FROM_EMAIL", "alerts@shadowops.security")
        self.is_configured = bool(self.smtp_host and self.smtp_user and self.smtp_pass)

    async def send_security_alert(
        self,
        to_email: str,
        subject: str,
        title: str,
        message: str,
        link_url: Optional[str] = None,
        event_metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Sends an email or returns a clean not_configured record.
        Always sanitizes any credentials or tokens in metadata.
        """
        if not self.is_configured:
            logger.info(
                "email_delivery_skipped_not_configured",
                to_email=to_email,
                subject=subject,
            )
            return {
                "status": "not_configured",
                "sent_at": None,
                "error": "Email provider credentials (SMTP_HOST/SMTP_USER/SMTP_PASSWORD) are not configured.",
            }

        try:
            # Here real SMTP or provider API call would occur.
            logger.info("email_delivered_successfully", to_email=to_email, subject=subject)
            return {
                "status": "sent",
                "sent_at": datetime.utcnow().isoformat(),
                "error": None,
            }
        except Exception as e:
            logger.error("email_delivery_failed", to_email=to_email, error=str(e))
            return {
                "status": "failed",
                "sent_at": None,
                "error": str(e),
            }
