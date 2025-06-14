from fastapi import APIRouter, Request, HTTPException, Response
from app.services.slack_service import SlackService
from app.db.crud import get_slack_token_by_team
from app.config.slack_config import SlackConfig
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/slack")

slack_service = SlackService()
# ========== Routes ==========

@router.get("/status")
async def slack_status():
    """Check if Slack is connected for any team"""
    try:
        # For demo purposes, check if we have any Slack installations
        # In a real app, you'd check for a specific team
        token = await get_slack_token_by_team("T090NR297QD")  # Demo team ID
        return {
            "connected": bool(token),
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
async def slack_oauth_authorize():
    """Redirect to Slack OAuth authorization"""
    if not SlackConfig.CLIENT_ID:
        raise HTTPException(status_code=400, detail="Slack not configured")
    
    auth_url = (
        f"https://slack.com/oauth/v2/authorize"
        f"?client_id={SlackConfig.CLIENT_ID}"
        f"&scope=app_mentions:read,channels:history,chat:write,im:history,im:read,im:write"
        f"&redirect_uri={SlackConfig.REDIRECT_URI}"
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
async def slack_oauth_callback(code: str):
    try:
        result = await slack_service.handle_oauth_callback(code)
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message", "OAuth failed"))
        return {"status": "success", "message": "Slack integration successful"}
    except Exception as e:
        logger.error("OAuth callback error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Slack OAuth error")
