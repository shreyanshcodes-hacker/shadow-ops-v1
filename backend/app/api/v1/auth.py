from fastapi import APIRouter, Depends
from app.models.profile import Profile
from app.schemas.profile import ProfileResponse
from app.security.dependencies import get_current_user

router = APIRouter(tags=["Authentication"])


@router.get("/me", response_model=ProfileResponse)
async def get_my_profile(current_user: Profile = Depends(get_current_user)):
    """
    Returns the authenticated user's ShadowOps profile.
    Identity is verified via the Firebase ID token and resolved in PostgreSQL.
    """
    return current_user
