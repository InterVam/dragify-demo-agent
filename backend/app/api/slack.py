from fastapi import APIRouter, Request, HTTPException, Response
from slack_sdk.signature import SignatureVerifier
from slack_sdk.errors import SlackApiError
from app.db.crud import get_slack_token_by_team
from slack_sdk import WebClient

from app.services.slack_service import SlackService
import os
import json
import logging
from typing import Dict, Any

# Setup logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

router = APIRouter(prefix="/slack")

# Load Slack app secrets from env
SLACK_SIGNING_SECRET = os.getenv("SLACK_SIGNING_SECRET")
SLACK_CLIENT_ID = os.getenv("SLACK_CLIENT_ID")
SLACK_CLIENT_SECRET = os.getenv("SLACK_CLIENT_SECRET")
SLACK_REDIRECT_URI = os.getenv("SLACK_REDIRECT_URI")

if not all([SLACK_SIGNING_SECRET, SLACK_CLIENT_ID, SLACK_CLIENT_SECRET, SLACK_REDIRECT_URI]):
    raise ValueError("Missing Slack environment variables")

# Signature verifier
signature_verifier = SignatureVerifier(SLACK_SIGNING_SECRET)

# In-memory deduplication store (replace with Redis in production)
processed_event_ids = set()

# ========== Helpers ==========

async def verify_slack_request(request: Request) -> bool:
    body = await request.body()
    timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
    signature = request.headers.get("X-Slack-Signature", "")
    return signature_verifier.is_valid(body=body, timestamp=timestamp, signature=signature)

def is_user_message(event: Dict[str, Any]) -> bool:
    return event.get("type") == "message" and not event.get("bot_id")

def is_duplicate(event_id: str) -> bool:
    if event_id in processed_event_ids:
        return True
    processed_event_ids.add(event_id)
    return False

# ========== Routes ==========

@router.post("/events")
async def handle_slack_events(request: Request) -> Dict[str, Any]:
    try:
        body = await request.body()
        data = json.loads(body)

        if data.get("type") == "url_verification":
            return Response(content=data.get("challenge", ""), media_type="text/plain")

        if not await verify_slack_request(request):
            raise HTTPException(status_code=401, detail="Invalid Slack request")

        event_id = data.get("event_id")
        event = data.get("event", {})
        team_id = data.get("team_id", "team_default")

        if not event_id:
            raise HTTPException(status_code=400, detail="Missing event_id")

        if is_duplicate(event_id):
            logger.info(f"Duplicate event {event_id}, skipping.")
            return {"status": "duplicate_skipped"}

        if is_user_message(event):
            message_text = event.get("text", "")
            channel = event.get("channel")
            thread_ts = event.get("thread_ts", event.get("ts"))

            logger.info(f"Received message from team {team_id}: {message_text}")

            token = await get_slack_token_by_team(team_id)
            if not token:
                logger.error(f"No token found for team {team_id}")
                raise HTTPException(status_code=404, detail="Slack bot not installed for this team.")

            slack_service = SlackService(token=token)
            await slack_service.process_message(
                message_text=message_text,
                channel=channel,
                thread_ts=thread_ts,
                team_id=team_id
            )

        return {"status": "ok"}

    except Exception as e:
        logger.error(f"Slack event error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Slack event handler error")

@router.get("/oauth/callback")
async def slack_oauth_callback(code: str):
    slack_client = WebClient()  # No token needed for OAuth flow

    try:
        response = slack_client.oauth_v2_access(
            client_id=SLACK_CLIENT_ID,
            client_secret=SLACK_CLIENT_SECRET,
            code=code,
            redirect_uri=SLACK_REDIRECT_URI
        )

        access_token = response.get("access_token")
        team = response.get("team", {})
        team_id = team.get("id")

        if not access_token or not team_id:
            raise HTTPException(status_code=400, detail="Invalid OAuth response")

        from app.db.crud import upsert_slack_installation
        await upsert_slack_installation(
            team_id=team_id,
            access_token=access_token,
            bot_user_id=response.get("bot_user_id", ""),
            team_name=team.get("name", "")
        )

        logger.info(f"Slack app installed by team: {team.get('name')} ({team_id})")

        return {"status": "success", "message": "Slack integration successful"}

    except SlackApiError as e:
        logger.error("OAuth error: %s", str(e))
        raise HTTPException(status_code=500, detail="Slack OAuth error")
