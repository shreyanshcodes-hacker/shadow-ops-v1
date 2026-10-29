# Email Delivery & n8n Integration Setup Guide

## 1. Email Delivery Configuration

ShadowOps features a provider-agnostic `EmailAdapter` that supports standard SMTP relays (e.g. SendGrid, AWS SES, Resend, Mailgun, or self-hosted Postfix).

### 1.1 Environment Variables
To enable outbound email alerts, set the following environment variables in your deployment environment (e.g., Railway or `.env`):

```bash
# SMTP Configuration
SMTP_HOST=smtp.sendgrid.net
SMTP_PORT=587
SMTP_USER=apikey
SMTP_PASSWORD=SG.your_actual_sendgrid_api_key_here
ALERT_FROM_EMAIL=alerts@shadowops.security
```

### 1.2 Graceful Degraded State (`not_configured`)
If these environment variables are absent or incomplete:
- The system **will not fail** or throw exceptions.
- The `EmailAdapter` returns `{"status": "not_configured", "sent_at": null}`.
- Deliveries are logged in `notification_deliveries` with `status="not_configured"`.
- Core security scans, AI analysis, remediation, and report generations proceed without interruption.

---

## 2. Optional n8n Workflow Automation Integration

n8n integration enables external orchestration for security team notifications and ticketing. By design, **n8n integration is disabled by default** and requires explicit activation.

### 2.1 Security Controls & Defense-in-Depth
1. **Disabled by Default:** Requires `N8N_ENABLED=true` in environment.
2. **Anti-SSRF Protection:** Destinations pointing to loopback addresses (`127.0.0.1`, `localhost`), link-local metadata addresses (`169.254.169.254`), or private RFC 1918 subnets (`10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16`) are blocked at runtime.
3. **Cryptographic HMAC SHA256 Signature:** Every outbound webhook payload is signed with `N8N_WEBHOOK_SECRET` and delivered with the header `X-ShadowOps-Signature`.
4. **Strict Timeout:** Enforces a 5.0-second HTTP timeout so external n8n downtimes never stall platform workers.
5. **Read-Only Telemetry:** n8n webhooks receive notifications only. They cannot trigger patch applications, close findings, or bypass human sign-offs.

### 2.2 n8n Environment Configuration
```bash
N8N_ENABLED=true
N8N_WEBHOOK_URL=https://automation.yourdomain.com/webhook/shadowops-alerts
N8N_WEBHOOK_SECRET=your_32_character_cryptographic_secret_here
```

### 2.3 Verifying Signatures in n8n
Inside your n8n Webhook Node, use a Code Node or Crypto Node to verify incoming authenticity:

```javascript
const crypto = require('crypto');
const signature = $request.headers['x-shadowops-signature'];
const secret = 'your_32_character_cryptographic_secret_here';

const expectedSignature = crypto
  .createHmac('sha256', secret)
  .update(JSON.stringify($json.body))
  .digest('hex');

if (signature !== expectedSignature) {
  throw new Error('Unauthorized: Invalid HMAC signature from ShadowOps');
}
return $json;
```
