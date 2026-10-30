import json
from typing import Dict, Any, Optional
import jwt
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.logging import logger

# Optional firebase_admin initialization
_firebase_initialized = False


def init_firebase() -> None:
    global _firebase_initialized
    if _firebase_initialized:
        return

    try:
        import firebase_admin
        from firebase_admin import credentials

        if settings.FIREBASE_CLIENT_EMAIL and settings.FIREBASE_PRIVATE_KEY:
            cleaned_key = (
                settings.FIREBASE_PRIVATE_KEY.strip()
                .strip('"')
                .strip("'")
                .replace("\\n", "\n")
            )
            cred_dict = {
                "type": "service_account",
                "project_id": settings.FIREBASE_PROJECT_ID,
                "private_key": cleaned_key,
                "client_email": settings.FIREBASE_CLIENT_EMAIL.strip().strip('"').strip("'"),
                "token_uri": "https://oauth2.googleapis.com/token",
            }
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("firebase_admin_initialized", project_id=settings.FIREBASE_PROJECT_ID)
        else:
            logger.warning("firebase_admin_credentials_not_provided_skipping_sdk_init")
    except Exception as e:
        logger.warning("firebase_admin_init_skipped", reason=str(e))


def verify_firebase_id_token(token: str) -> Dict[str, Any]:
    """
    Verify Firebase Authentication ID Token (JWT).
    In testing environment, permits signed test tokens for hermetic unit testing.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Testing / Development hermetic bypass for test tokens
    if (settings.is_testing or settings.DEBUG) and token.startswith("test-token-"):
        uid = token.replace("test-token-", "")
        email = "operator@shadowops.io" if uid == "local-dev-user" else f"{uid}@test.shadowops.io"
        name = "Security Lead (Local)" if uid == "local-dev-user" else f"Test User {uid}"
        return {
            "uid": uid,
            "sub": uid,
            "email": email,
            "name": name,
            "email_verified": True,
        }

    # Verify with Firebase Admin SDK if initialized with service account
    if _firebase_initialized:
        try:
            from firebase_admin import auth
            decoded = auth.verify_id_token(token, check_revoked=True)
            return decoded
        except Exception as e:
            logger.warning("firebase_token_verification_failed", error=str(e))
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired token: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Verify cryptographically against Google's public Firebase X.509 certificates
    # even when service account private key is not provided on the server
    if not settings.is_testing and settings.FIREBASE_PROJECT_ID:
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests as google_requests

            decoded = id_token.verify_firebase_token(
                token,
                google_requests.Request(),
                audience=settings.FIREBASE_PROJECT_ID,
            )
            if decoded:
                uid = decoded.get("uid") or decoded.get("user_id") or decoded.get("sub")
                if uid:
                    decoded["uid"] = uid
                    return decoded
        except Exception as e:
            logger.warning("google_public_cert_firebase_verify_failed", error=str(e))
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Invalid or expired Firebase ID token: {str(e)}",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    # Fallback JWT decode for local development ONLY when NOT in production
    if settings.is_production:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Firebase Admin authentication is required in production environment.",
        )

    try:
        decoded = jwt.decode(
            token,
            options={"verify_signature": False},
        )
        if "sub" not in decoded and "uid" not in decoded:
            raise ValueError("Missing subject claim in token")
        return decoded
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token format",
            headers={"WWW-Authenticate": "Bearer"},
        )
