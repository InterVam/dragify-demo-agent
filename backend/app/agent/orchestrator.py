from langchain.agents import AgentExecutor, create_tool_calling_agent
from app.config.llm import get_llm
from app.agent.prompt import get_prompt_template
from app.agent.tools.registry import TOOL_REGISTRY
from app.config.flow_config import get_user_flow
import logging

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """
    Builds a LangChain agent executor for a given team, with a tool chain
    based on dynamic flow configuration (data source, CRM, notification).
    """

    def __init__(self, team_id: str):
        self.team_id = team_id
        self.flow = get_user_flow(team_id)
        self.llm = get_llm()
        self.prompt = get_prompt_template()
        self.tools = self._load_tools()

        logger.info(f"Creating agent for team: {team_id}, flow: {self.flow}")

    def _load_tools(self):
        try:
            return [
                TOOL_REGISTRY["extract_lead_info"],
                TOOL_REGISTRY[self.flow["data_source"]],
                TOOL_REGISTRY[self.flow["crm"]],
                TOOL_REGISTRY[self.flow["notification_channel"]],
            ]
        except KeyError as e:
            logger.error(f"Missing tool in flow config: {e}")
            raise

    def build(self) -> AgentExecutor:
        """
        Returns a ready-to-use LangChain AgentExecutor.
        """
        agent = create_tool_calling_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=self.prompt
        )
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            return_intermediate_steps=True
        )
