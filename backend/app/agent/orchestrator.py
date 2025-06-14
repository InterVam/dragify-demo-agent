import logging
import asyncio
from langchain.agents import create_tool_calling_agent, AgentExecutor
from app.config.llm import get_llm
from app.agent.tools.registry import TOOL_REGISTRY
from app.agent.prompt import get_prompt_template

logger = logging.getLogger(__name__)

class AgentOrchestrator:
    """
    Builds a LangChain AgentExecutor for a given team,
    injecting team_id and flow_config into the prompt and wiring up tools dynamically.
    """
    def __init__(self, team_id: str, flow_config: dict):
        self.team_id     = team_id
        self.flow_config = flow_config
        self.llm         = get_llm()
        # Simple prompt that works with Groq, but intelligent tool loading
        self.prompt      = get_prompt_template()
        self.tools       = self._load_tools()
        logger.info(f"[AgentOrchestrator] Initialized for team {team_id} with flow {flow_config}")

    def _load_tools(self):
        missing = []
        tools = []
        
        # Always include lead extraction tool
        required_tools = ["extract_lead_info"]
        
        # Add configured tools with null checks
        data_source = self.flow_config.get("data_source")
        crm = self.flow_config.get("crm")
        notification_channel = self.flow_config.get("notification_channel")
        
        if data_source:
            required_tools.append(data_source)
        if crm:
            required_tools.append(crm)
        if notification_channel:
            # Map notification channel to actual tool name
            if notification_channel == "gmail":
                required_tools.append("send_gmail_notification")
            elif notification_channel == "outlook":
                required_tools.append("send_outlook_notification")
            else:
                required_tools.append(notification_channel)
        
        for key in required_tools:
            tool = TOOL_REGISTRY.get(key)
            if not tool:
                missing.append(key)
            else:
                tools.append(tool)
                
        if missing:
            logger.warning(f"Missing tools in registry for team {self.team_id}: {missing}")
            # Don't raise exception, just log warning and continue with available tools
            
        if not tools:
            raise KeyError(f"No valid tools found for team {self.team_id}. Check flow configuration.")
            
        return tools

    def build(self) -> AgentExecutor:
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

    async def handle_message(self, message: str) -> str:
        """
        Executes the agent with input and team_id asynchronously,
        returns the final output text.
        """
        executor = self.build()
        
        # Map flow config to tool names for prompt
        data_source = self.flow_config.get("data_source", "")
        crm = self.flow_config.get("crm", "")
        notification_channel = self.flow_config.get("notification_channel", "")
        
        # Map notification channel to actual tool name
        notification_tool = ""
        if notification_channel == "gmail":
            notification_tool = "send_gmail_notification"
        elif notification_channel == "outlook":
            notification_tool = "send_outlook_notification"
        else:
            notification_tool = notification_channel
        
        # use async invocation to support StructuredTool
        result = await executor.ainvoke({
            "input": message,
            "team_id": self.team_id,
            "data_source": data_source,
            "crm": crm,
            "notification_tool": notification_tool
        })
        # extract and return output
        if isinstance(result, dict):
            return result.get("output", str(result))
        return str(result)
