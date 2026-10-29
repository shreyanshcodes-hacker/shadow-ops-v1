"""
CONTROLLED DEMO TARGET FIXTURE
WARNING: Contains intentionally insecure code patterns for SAST/Semgrep validation tests.
DO NOT RUN IN PRODUCTION.
"""

import sqlite3
import subprocess
import hashlib

# 1. Insecure SQL Injection pattern
def insecure_search_user(username: str):
    conn = sqlite3.connect(":memory:")
    cursor = conn.cursor()
    # Semgrep rule: bandit.B608 or generic sql injection
    query = f"SELECT * FROM users WHERE username = '{username}'"
    return cursor.execute(query).fetchall()

# 2. Hardcoded Secret / Key pattern
# Semgrep rule: generic.secrets.security.detected-jwt-token / hardcoded-key
AWS_ACCESS_KEY_EXAMPLE = "AKIAIOSFODNN7EXAMPLE"
API_SECRET_KEY_MOCK = "sh_sec_9948281048102830192840192830"

# 3. Unsafe Subprocess invocation
def insecure_ping(host: str):
    # Semgrep rule: subprocess-shell-true / command-injection
    return subprocess.run(f"ping {host}", shell=True, capture_output=True)

# 4. Weak Cryptographic Hash (MD5 for security)
def generate_insecure_token(password: str):
    # Semgrep rule: use-of-md5
    return hashlib.md5(password.encode()).hexdigest()
