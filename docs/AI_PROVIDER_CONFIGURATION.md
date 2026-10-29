# SHADOWOPS — AI PROVIDER CONFIGURATION SPECIFICATION
## Environment Variables, Provider Switching, Model Parameters & Cost Safeguards

```
+-----------------------------------------------------------------------------------+
|                     AI PROVIDER CONFIGURATION SPECIFICATION                       |
+-----------------------------------------------------------------------------------+
```

---

## 1. Environment Configuration

All AI provider credentials and configurations remain strictly backend-only. The frontend browser bundle never receives provider API keys or service credentials.

| Environment Variable | Default Value | Description |
|---|---|---|
| `AI_PROVIDER` | `gemini` | Configured active provider (`gemini` or `grok`). |
| `GEMINI_API_KEY` | *(None / Confidential)* | Google Generative Language API Key. |
| `GEMINI_MODEL` | `gemini-1.5-pro` | Gemini model name. |
| `GROK_API_KEY` | *(None / Confidential)* | xAI Grok API Key. |
| `GROK_MODEL` | `grok-beta` | Grok model name. |
| `AI_MAX_FINDINGS_PER_RUN` | `25` | Maximum findings processed per batch scan analysis. |
| `AI_MAX_INPUT_CHARS` | `12000` | Character ceiling for code snippet inputs. |
| `AI_REQUEST_TIMEOUT_SECONDS` | `45` | Bounded HTTP timeout per provider call. |
| `AI_MAX_RETRIES` | `3` | Maximum retry attempts with exponential backoff on 429/5xx. |
| `AI_COST_CAP_PER_RUN_USD` | `2.0` | Maximum estimated spend budget per analysis run. |
| `AI_PROMPT_VERSION` | `security-finding-analysis-v1` | Immutable version tag for security prompts. |

---

## 2. Dynamic Provider Selection

The platform dynamically resolves the requested provider via `app.ai.provider.get_ai_provider(provider_name)`:

- If `AI_PROVIDER=gemini`: invokes `GeminiProvider` using Google Generative Language API.
- If `AI_PROVIDER=grok`: invokes `GrokProvider` using xAI's OpenAI-compatible completions API.
- If in automated testing: `FakeAIProvider` is available exclusively for hermetic unit tests.

If an unconfigured or failing provider is requested, the service records an error in `finding_ai_analysis` with status `FAILED` and raises a clean HTTP 503 (`AI_ANALYSIS_PROVIDER_UNAVAILABLE`) without leaking secrets or configuration details.
