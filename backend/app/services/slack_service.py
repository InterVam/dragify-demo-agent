import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from app.agent.orchestrator import AgentOrchestrator

logger = logging.getLogger(__name__)

class SlackService:
    def __init__(self, token: str):
        self.client = WebClient(token=token)

    def post_message(self, channel: str, thread_ts: str, text: str):
        """
        Send a message to Slack.
        """
        try:
            self.client.chat_postMessage(channel=channel, thread_ts=thread_ts, text=text)
            logger.info(f"[SlackService] Message sent to channel {channel}")
        except SlackApiError as e:
            logger.error(f"[SlackService] Failed to send message: {e.response['error']}")

    async def process_message(self, message_text: str, channel: str, thread_ts: str, team_id: str):
        """
        Process an incoming Slack message through the LangChain agent.
        """
        logger.info(f"[SlackService] Processing message for team {team_id}: {message_text}")

        try:
            agent = AgentOrchestrator(team_id).build()
            if not agent:
                raise RuntimeError(f"Failed to create agent for team: {team_id}")

            result = await agent.ainvoke({"input": message_text})
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
