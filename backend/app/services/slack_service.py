import logging
from fastapi import Request
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier
from collections import deque

from app.agent.orchestrator import AgentOrchestrator
from app.config.flow_config import get_user_flow
from app.config.slack_config import SlackConfig
from app.db.crud import upsert_slack_installation, get_slack_token_by_team
from app.services.event_logger import event_logger

logger = logging.getLogger(__name__)
# Use bounded deque to prevent memory leaks - keeps only last 1000 event IDs
_processed_event_ids = deque(maxlen=1000)

class SlackService:
    def __init__(self, token: str = None):
        self.token = token
        self.client = WebClient(token=token) if token else None
        self.verifier = SignatureVerifier(SlackConfig.SIGNING_SECRET)

    @staticmethod
    def is_user_message(event: dict) -> bool:
        return event.get("type") == "message" and not event.get("bot_id")

    @staticmethod
    def is_duplicate(event_id: str) -> bool:
        if event_id in _processed_event_ids:
            return True
        _processed_event_ids.append(event_id)
        return False

    async def verify_request(self, request: Request) -> bool:
        try:
            body = await request.body()
            timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
            signature = request.headers.get("X-Slack-Signature", "")
            return self.verifier.is_valid(body=body, timestamp=timestamp, signature=signature)
        except Exception as e:
            logger.error(f"Error verifying Slack request: {e}")
            return False

    def post_message(self, channel: str, thread_ts: str, text: str):
        try:
            if not self.client:
                logger.error("Slack client not initialized")
                return
                
            # Ensure text is a string and not empty
            if not text or not isinstance(text, str):
                text = "✅ Request processed successfully"
                
            # Clean up the text - remove any extra formatting
            text = str(text).strip()
            if not text:
                text = "✅ Request processed successfully"
                
            self.client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=text)
            logger.info(f"Sent message to {channel}")
        except SlackApiError as e:
            logger.error(f"Failed to send message: {e.response['error']}")
        except Exception as e:
            logger.error(f"Unexpected error sending message: {e}")

    async def process_message(self, message_text: str, channel: str, thread_ts: str, team_id: str):
        """
        Orchestrate the agent workflow for a single Slack message.
        """
        logger.info(f"Processing message for team {team_id}: {message_text}")
        
        # Log the incoming message event
        event_id = await event_logger.log_event(
            event_type="message_received",
            event_data={
                "message": message_text,
                "channel": channel,
                "team_id": team_id
            },
            status="processing",
            team_id=team_id
        )
        
        try:
            flow_config = get_user_flow(team_id)
            orchestrator = AgentOrchestrator(team_id, flow_config)
            reply = await orchestrator.handle_message(message_text)
            
            # Ensure reply is a proper string
            if not reply or not isinstance(reply, str):
                reply = "✅ Request processed successfully"
            
            # Log the actual reply for debugging
            logger.info(f"Agent reply for team {team_id}: {reply}")
            
            # Update event status to success
            await event_logger.update_event_status(
                event_id=event_id,
                status="success",
                event_data={
                    "message": message_text,
                    "channel": channel,
                    "team_id": team_id,
                    "reply": reply
                }
            )
            
        except Exception as e:
            logger.error(f"Orchestrator error for team {team_id}: {e}", exc_info=True)
            reply = "❌ Error processing your request. Please try again later."
            
            # Update event status to error
            await event_logger.update_event_status(
                event_id=event_id,
                status="error",
                error_message=str(e)
            )

        self.post_message(channel=channel, thread_ts=thread_ts, text=reply)

    async def handle_event(self, data: dict):
        try:
            event_id = data.get("event_id")
            if not event_id or SlackService.is_duplicate(event_id):
                logger.info(f"Skipping event {event_id}")
                return

            event = data.get("event", {})
            if not self.is_user_message(event):
                return

            team_id = data.get("team_id", "")
            if not team_id:
                logger.error("No team_id in event data")
                return
                
            token = await get_slack_token_by_team(team_id)
            if not token:
                logger.error(f"No token for team {team_id}")
                return

            self.client = WebClient(token=token)

            message_text = event.get("text", "")
            channel = event.get("channel")
            thread_ts = event.get("thread_ts") or event.get("ts")

            if not channel or not thread_ts:
                logger.error(f"Missing channel or thread_ts in event for team {team_id}")
                return

            await self.process_message(message_text, channel, thread_ts, team_id)
        except Exception as e:
            logger.error(f"Error handling Slack event: {e}", exc_info=True)

    async def handle_oauth_callback(self, code: str) -> dict:
        slack = WebClient()
        try:
            resp = slack.oauth_v2_access(
                client_id=SlackConfig.CLIENT_ID,
                client_secret=SlackConfig.CLIENT_SECRET,
                code=code,
                redirect_uri=SlackConfig.REDIRECT_URI
            )
            token = resp.get("access_token")
            team = resp.get("team", {})
            team_id = team.get("id")
            if not token or not team_id:
                raise ValueError("Invalid OAuth response")

            await upsert_slack_installation(
                team_id=team_id,
                access_token=token,
                bot_user_id=resp.get("bot_user_id", ""),
                team_name=team.get("name", "")
            )
            logger.info(f"Installed Slack for {team_id}")
            return {"status": "success", "message": "Slack integration complete"}
        except SlackApiError as e:
            logger.error(f"OAuth error: {e.response['error']}")
            return {"status": "error", "message": "OAuth failed"}
        except Exception as e:
            logger.error(f"Unexpected OAuth error: {e}", exc_info=True)
            return {"status": "error", "message": "OAuth failed"}
