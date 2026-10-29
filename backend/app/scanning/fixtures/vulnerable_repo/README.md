# Controlled Demo Target Fixture
Intentionally vulnerable microservice codebase used exclusively for Stage 3 SAST/Semgrep validation.
Rules tested:
- SQL Injection in query formatting
- Hardcoded secrets
- Shell=True subprocess execution
- Weak MD5 cryptographic hashing
