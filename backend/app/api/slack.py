from fastapi import APIRouter, Request, HTTPException, Response
from app.services.slack_service import SlackService
from app.db.crud import get_slack_token_by_team
from app.config.slack_config import SlackConfig
from app.utils.session import SessionManager
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/slack")

slack_service = SlackService()
# ========== Routes ==========

@router.get("/status")
async def slack_status(team_id: str = None):
    """Check if Slack is connected for a specific team or any team"""
    try:
        if team_id:
            # Check for specific team
            token = await get_slack_token_by_team(team_id)
            return {
                "connected": bool(token),
                "service": "slack",
                "configured": bool(SlackConfig.CLIENT_ID),
                "team_id": team_id
            }
        else:
            # When no team is specified, return basic configuration status
            return {
                "connected": False,
                "service": "slack",
                "configured": bool(SlackConfig.CLIENT_ID)
            }
    except Exception as e:
        logger.error(f"Slack status check error: {e}")
        return {
            "connected": False,
            "service": "slack",
            "configured": bool(SlackConfig.CLIENT_ID),
            "error": str(e)
        }

@router.get("/oauth/authorize")
async def slack_oauth_authorize(request: Request):
    """Redirect to Slack OAuth authorization"""
    if not SlackConfig.CLIENT_ID:
        raise HTTPException(status_code=400, detail="Slack not configured")
    
    # Try to get session ID from request, but don't require it for now
    session_id = SessionManager.get_session_id_from_request(request)
    if not session_id:
        # Generate a temporary session ID for this OAuth flow
        session_id = SessionManager.generate_session_id()
    
    auth_url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={SlackConfig.CLIENT_ID}"
        f"&scope=app_mentions:read,channels:history,chat:write,im:history,im:read,im:write"
        f"&redirect_uri={SlackConfig.REDIRECT_URI}"
        f"&state={session_id}"
    )
    
    return {"auth_url": auth_url}

@router.post("/events")
async def handle_slack_events(request: Request) -> Dict[str, Any]:
    try:
        body = await request.body()
        data = json.loads(body)

        # Slack URL Verification Challenge
        if data.get("type") == "url_verification":
            challenge = data.get("challenge", "")
            return Response(content=challenge, media_type="text/plain")

        # Verify authenticity
        if not await slack_service.verify_request(request):
            raise HTTPException(status_code=401, detail="Invalid Slack request")

        await slack_service.handle_event(data)
        return {"status": "ok"}

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in Slack event: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    except Exception as e:
        logger.error(f"Slack event error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Slack event handler error")


@router.get("/oauth/callback")
async def slack_oauth_callback(code: str, state: str = None):
    try:
        # Get session ID from OAuth state parameter
        session_id = state
        if not session_id:
            raise HTTPException(status_code=400, detail="Missing session state")
        
        result = await slack_service.handle_oauth_callback(code, session_id)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message", "OAuth failed"))
        return {"status": "success", "message": "Slack integration successful"}
    except Exception as e:
        logger.error("OAuth callback error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Slack OAuth error")
