from fastapi import APIRouter, Request, HTTPException, Response
from app.services.slack_service import SlackService
import json
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/slack")

slack_service = SlackService()
# ========== Routes ==========

@router.post("/events")
async def handle_slack_events(request: Request) -> Dict[str, Any]:
    try:
        body = await request.body()
        data = json.loads(body)

        # Slack URL Verification Challenge
        if data.get("type") == "url_verification":
            return Response(content=data.get("challenge", ""), media_type="text/plain")

        # Verify authenticity
        if not await slack_service.verify_request(request):
            raise HTTPException(status_code=401, detail="Invalid Slack request")

        await slack_service.handle_event(data)
        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Slack event error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Slack event handler error")


@router.get("/oauth/callback")
async def slack_oauth_callback(code: str):
    try:
        await slack_service.handle_oauth_callback(code)
        return {"status": "success", "message": "Slack integration successful"}
    except Exception as e:
        logger.error("OAuth callback error: %s", str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Slack OAuth error")
