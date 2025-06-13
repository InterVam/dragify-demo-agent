import logging
from fastapi import Request
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_sdk.signature import SignatureVerifier

from app.agent.orchestrator import AgentOrchestrator
from app.config.flow_config import get_user_flow
from app.config.slack_config import SlackConfig
from app.db.crud import upsert_slack_installation, get_slack_token_by_team

logger = logging.getLogger(__name__)
processed_event_ids = set()

class SlackService:
    def __init__(self, token: str = None):
        self.token = token
        self.client = WebClient(token=token) if token else None
        self.signature_verifier = SignatureVerifier(SlackConfig.SIGNING_SECRET)

    @staticmethod
    def is_user_message(event: dict) -> bool:
        return event.get("type") == "message" and not event.get("bot_id")

    @staticmethod
    def is_duplicate(event_id: str) -> bool:
        if event_id in processed_event_ids:
            return True
        processed_event_ids.add(event_id)
        return False

    async def verify_request(self, request: Request) -> bool:
        body = await request.body()
        timestamp = request.headers.get("X-Slack-Request-Timestamp", "")
        signature = request.headers.get("X-Slack-Signature", "")
        return self.signature_verifier.is_valid(body=body, timestamp=timestamp, signature=signature)

    def post_message(self, channel: str, thread_ts: str, text: str):
        try:
            self.client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=text)
            logger.info(f"[SlackService] Message sent to channel {channel}")
        except SlackApiError as e:
            logger.error(f"[SlackService] Failed to send message: {e.response['error']}")

    async def process_message(self, message_text: str, channel: str, thread_ts: str, team_id: str, flow_config: dict):
        logger.info(f"[SlackService] Processing message for team {team_id}: {message_text}")
        try:
            agent = AgentOrchestrator(team_id).build()
            if not agent:
                raise RuntimeError(f"Failed to create agent for team: {team_id}")

            result = await agent.ainvoke({
                "input": message_text,
                "team_id": team_id,
                "flow_config": flow_config
            })

            logger.info(f"[SlackService] Agent result: {result}")
            output_text = result.get("output") if isinstance(result, dict) else str(result)
            if output_text:
                self.post_message(channel=channel, thread_ts=thread_ts, text=output_text)

        except Exception as e:
            logger.error(f"[SlackService] Agent error: {str(e)}", exc_info=True)
            self.post_message(
                channel=channel,
                thread_ts=thread_ts,
                text="❌ Sorry, I encountered an error while processing your message."
            )

    async def handle_event(self, data: dict):
        event = data.get("event", {})
        event_id = data.get("event_id")
        team_id = data.get("team_id", "team_default")

        if not event_id or SlackService.is_duplicate(event_id):
            logger.info(f"[SlackService] Duplicate or missing event_id: {event_id}")
            return

        if SlackService.is_user_message(event):
            message_text = event.get("text", "")
            channel = event.get("channel")
            thread_ts = event.get("thread_ts", event.get("ts"))

            logger.info(f"[SlackService] Processing user message: {message_text}")
            token = await get_slack_token_by_team(team_id)
            if not token:
                logger.error(f"[SlackService] No bot token for team {team_id}")
                return

            self.token = token
            self.client = WebClient(token=token)

            flow_config = get_user_flow(team_id)
            print(flow_config)

            await self.process_message(
                message_text=message_text,
                channel=channel,
                thread_ts=thread_ts,
                team_id=team_id,
                flow_config=flow_config
            )

    async def handle_oauth_callback(self, code: str) -> dict:
        slack_client = WebClient()
        try:
            response = slack_client.oauth_v2_access(
                client_id=SlackConfig.CLIENT_ID,
                client_secret=SlackConfig.CLIENT_SECRET,
                code=code,
                redirect_uri=SlackConfig.REDIRECT_URI
            )

            access_token = response.get("access_token")
            team = response.get("team", {})
            team_id = team.get("id")

            if not access_token or not team_id:
                raise ValueError("Invalid OAuth response")

            await upsert_slack_installation(
                team_id=team_id,
                access_token=access_token,
                bot_user_id=response.get("bot_user_id", ""),
                team_name=team.get("name", "")
            )

            logger.info(f"[SlackService] Installed by team: {team.get('name')} ({team_id})")
            return {"status": "success", "message": "Slack integration successful"}

        except SlackApiError as e:
            logger.error(f"[SlackService] OAuth error: {e.response['error']}")
            return {"status": "error", "message": "Slack OAuth error"}
