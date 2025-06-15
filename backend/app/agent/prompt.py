from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder


def get_prompt_template() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", "You are a real estate assistant. For each lead message, execute these steps ONCE in order: 1) Call extract_lead_info to extract lead data 2) Call {data_source} with the lead data to find matching properties 3) Call {crm} with the enhanced lead data 4) Call {notification_tool} with the lead data from step 3. Pass the complete lead_info between steps. Do not repeat any step."),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
        ("human", "Input: {input} Team: {team_id}")
    ])


def get_prompt_template_with_config(flow_config: dict) -> ChatPromptTemplate:
    """Generate prompt template with flow configuration injected"""
    # Simplified version that works with Groq
    return get_prompt_template()


# 3. Tag with team ID:
#    `if lead_info_enhanced.get('team_id') != team_id: lead_info_enhanced['team_id'] = team_id`