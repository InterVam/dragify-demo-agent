from fastapi import APIRouter, Request, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
import httpx
import logging
import asyncio
from sqlalchemy import select

from app.services.zoho_service import ZohoService
from app.config.zoho_config import ZohoConfig
from app.db.session import AsyncSessionLocal
from app.db.models import ZohoInstallation
from app.utils.session import SessionManager

router = APIRouter(prefix="/zoho", tags=["Zoho"])
logger = logging.getLogger(__name__)

# Initialize ZohoService with config
config = ZohoConfig()
zoho_service = ZohoService(
    client_id=config.client_id,
    client_secret=config.client_secret,
    redirect_uri=config.redirect_uri
)

class LeadPayload(BaseModel):
    first_name: str
    last_name: str
    phone: str
    location: str
    property_type: str
    bedrooms: int
    budget: int
    matched_projects: list[str]
    team_id: str

@router.get("/status")
async def zoho_status(team_id: str = None):
    """Check if Zoho is connected for a specific team"""
    try:
        if not team_id:
            return {
                "connected": False,
                "service": "zoho",
                "configured": bool(config.client_id)
            }
            
        async with AsyncSessionLocal() as session:
            stmt = select(ZohoInstallation).where(ZohoInstallation.team_id == team_id)
            result = await session.execute(stmt)
            installation = result.scalar_one_or_none()
            
        return {
            "connected": bool(installation and installation.access_token),
            "service": "zoho",
            "configured": bool(config.client_id),
            "team_id": team_id
        }
    except Exception as e:
        logger.error(f"Zoho status check error: {e}")
        return {
            "connected": False,
            "service": "zoho",
            "configured": bool(config.client_id),
            "error": str(e)
        }

@router.get("/oauth/authorize")
async def zoho_oauth_authorize(team_id: str, request: Request):
    """Get Zoho OAuth authorization URL"""
    if not config.client_id:
        raise HTTPException(status_code=400, detail="Zoho not configured")
    
    if not team_id:
        raise HTTPException(status_code=400, detail="team_id is required")
    
    # Try to get session ID, but don't require it for now (backward compatibility)
    session_id = SessionManager.get_session_id_from_request(request)
    
    # If we have a session ID, validate team access
    if session_id:
        from app.db.crud import get_team_by_id_and_session
        async with AsyncSessionLocal() as session:
            team = await get_team_by_id_and_session(team_id, session_id)
            if not team:
                raise HTTPException(status_code=403, detail="Team not found or access denied")
    
    auth_url = zoho_service.get_authorization_url(team_id)
    
    return {"auth_url": auth_url}

@router.get("/oauth/callback", summary="Zoho OAuth callback")
async def zoho_oauth_callback(
    code: str = Query(..., description="Authorization code from Zoho"),
    state: str = Query(..., alias="state", description="Slack team_id stored in state parameter")
):
    """
    Callback endpoint for Zoho OAuth. 'state' must be the Slack team_id.
    Exchanges code for tokens and stores them.
    """
    try:
        team_id = state
        logger.info(f"[Zoho OAuth] Received callback for team_id={team_id}")
        await zoho_service.exchange_code_for_tokens(code=code, team_id=team_id)
        return {"status": "success", "message": "Zoho integration successful."}
    except httpx.HTTPError as e:
        logger.error(f"[Zoho OAuth] HTTP error during token exchange: {e}", exc_info=True)
        raise HTTPException(status_code=502, detail="Error exchanging Zoho OAuth tokens.")
    except Exception as e:
        logger.error(f"[Zoho OAuth] Unexpected error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Zoho OAuth callback failed.")

@router.post("/leads/{team_id}", summary="Insert lead into Zoho")
async def insert_zoho_lead(
    team_id: str,
    payload: LeadPayload,
    bg: BackgroundTasks
):
    """
    Insert a lead into Zoho CRM using stored tokens for the given Slack team_id.
    Processes asynchronously to acknowledge Slack quickly.
    """
    async def _background_task():
        try:
            await zoho_service.insert_lead(team_id=team_id, lead_info=payload.dict())
            logger.info(f"[Zoho] Successfully inserted lead for team {team_id}")
        except Exception as e:
            logger.error(f"[Zoho] Failed to insert lead for team {team_id}: {e}", exc_info=True)

    bg.add_task(_background_task)
    return {"status": "accepted", "message": "Lead processing started."}
