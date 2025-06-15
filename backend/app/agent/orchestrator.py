import logging
import asyncio
from langchain.agents import create_tool_calling_agent, AgentExecutor
from app.config.llm import get_llm
from app.agent.tools.registry import TOOL_REGISTRY
from app.agent.prompt import get_prompt_template
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

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
        self.tools       = self._load_tools()
        
        # Create prompt with actual tool names filled in
        self.prompt      = self._create_prompt_with_tools()
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

    def _create_prompt_with_tools(self) -> ChatPromptTemplate:
        """Create prompt template with actual tool names filled in"""
        # Map flow config to tool names
        data_source = self.flow_config.get("data_source", "fetch_from_postgres")
        crm = self.flow_config.get("crm", "insert_into_zoho")
        notification_channel = self.flow_config.get("notification_channel", "gmail")
        
        # Map notification channel to actual tool name
        if notification_channel == "gmail":
            notification_tool = "send_gmail_notification"
        elif notification_channel == "outlook":
            notification_tool = "send_outlook_notification"
        else:
            notification_tool = "send_gmail_notification"  # fallback
        
        # Create prompt with actual tool names
        system_message = f"You are a real estate assistant. For each lead message, execute these steps ONCE in order: 1) Call extract_lead_info to extract lead data 2) Call {data_source} with the lead data to find matching properties 3) Call {crm} with the enhanced lead data 4) Call {notification_tool} with the lead data from step 3. Pass the complete lead_info between steps. Do not repeat any step."
        
        return ChatPromptTemplate.from_messages([
            ("system", system_message),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
            ("human", "Input: {input} Team: {team_id}")
        ])

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
        
        # use async invocation to support StructuredTool
        result = await executor.ainvoke({
            "input": message,
            "team_id": self.team_id
        })
        # extract and return output
        if isinstance(result, dict):
            return result.get("output", str(result))
        return str(result)
