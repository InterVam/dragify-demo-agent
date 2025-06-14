from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel
import logging

from app.services.gmail_service import GmailService
from app.config.gmail_config import GmailConfig

router = APIRouter(prefix="/gmail", tags=["Gmail"])
logger = logging.getLogger(__name__)

# Initialize GmailService with config
config = GmailConfig()
gmail_service = GmailService(
    client_id=config.client_id,
    client_secret=config.client_secret,
    redirect_uri=config.redirect_uri
)

@router.get("/oauth/authorize", summary="Get Gmail OAuth authorization URL")
async def gmail_oauth_authorize(team_id: str = Query(default="T090NR297QD", description="Slack team_id for this integration")):
    """
    Generate Gmail OAuth authorization URL.
    Redirect users to this URL to start the OAuth flow.
    """
    try:
        authorization_url = gmail_service.get_authorization_url(team_id)
        return {
            "auth_url": authorization_url,
            "message": "Redirect user to this URL to authorize Gmail access"
        }
    except Exception as e:
        logger.error(f"[Gmail OAuth] Error generating authorization URL: {e}")
        raise HTTPException(status_code=500, detail="Failed to generate authorization URL")

@router.get("/oauth/callback", summary="Gmail OAuth callback")
async def gmail_oauth_callback(
    code: str = Query(..., description="Authorization code from Gmail"),
    state: str = Query(..., description="Slack team_id stored in state parameter")
):
    """
    Callback endpoint for Gmail OAuth. 'state' contains the Slack team_id.
    Exchanges code for tokens and stores them.
    """
    try:
        team_id = state
        logger.info(f"[Gmail OAuth] Received callback for team_id={team_id}")
        await gmail_service.exchange_code_for_tokens(code=code, team_id=team_id)
        return {"status": "success", "message": "Gmail integration successful."}
    except Exception as e:
        logger.error(f"[Gmail OAuth] Error during token exchange: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Gmail OAuth callback failed.")

@router.post("/test-email/{team_id}", summary="Test email sending")
async def test_email(team_id: str):
    """
    Test endpoint to send a sample notification email.
    Useful for testing the Gmail integration.
    """
    try:
        test_lead_info = {
            "first_name": "Test",
            "last_name": "User",
            "phone": "+1234567890",
            "location": "Test City",
            "property_type": "apartment",
            "bedrooms": 2,
            "budget": 500000,
            "matched_projects": ["Test Project 1", "Test Project 2"],
            "team_id": team_id
        }
        
        subject = "Test: Lead Processing Notification"
        body_html = gmail_service.generate_lead_success_email(test_lead_info, {"status": "success"})
        
        await gmail_service.send_notification_email(
            team_id=team_id,
            subject=subject,
            body_html=body_html
        )
        
        return {"status": "success", "message": "Test email sent successfully"}
    except Exception as e:
        logger.error(f"[Gmail Test] Error sending test email: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to send test email")

@router.get("/status", summary="Check Gmail integration status")
async def gmail_status():
    """
    Check if Gmail integration is set up for the demo team.
    """
    try:
        from app.db.session import AsyncSessionLocal
        from app.db.models import GmailInstallation
        from sqlalchemy import select
        from datetime import datetime
        
        team_id = "T090NR297QD"  # Demo team ID
        
        async with AsyncSessionLocal() as session:
            stmt = select(GmailInstallation).where(GmailInstallation.team_id == team_id)
            result = await session.execute(stmt)
            installation = result.scalar_one_or_none()
            
        if installation:
            # Check if token is expired
            now_utc = datetime.utcnow()
            exp = installation.expires_at
            if exp.tzinfo is not None:
                exp = exp.replace(tzinfo=None)
            
            is_expired = exp <= now_utc
            
            return {
                "connected": bool(installation.access_token and not is_expired),
                "service": "gmail",
                "configured": bool(config.client_id),
                "user_email": installation.user_email,
                "expires_at": installation.expires_at.isoformat() if installation.expires_at else None,
                "is_expired": is_expired
            }
        else:
            return {
                "connected": False,
                "service": "gmail",
                "configured": bool(config.client_id),
                "user_email": None
            }
                
    except Exception as e:
        logger.error(f"Gmail status check error: {e}")
        return {
            "connected": False,
            "service": "gmail",
            "configured": bool(config.client_id),
            "error": str(e)
        }

@router.post("/revoke/{team_id}", summary="Revoke Gmail integration")
async def revoke_gmail_integration(team_id: str):
    """
    Revoke Gmail integration for a team. User will need to re-authorize.
    """
    try:
        await gmail_service.revoke_tokens(team_id)
        return {"status": "success", "message": "Gmail integration revoked successfully"}
    except Exception as e:
        logger.error(f"[Gmail Revoke] Error revoking integration: {e}")
        raise HTTPException(status_code=500, detail="Failed to revoke Gmail integration") 