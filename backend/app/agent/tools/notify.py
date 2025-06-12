import logging
from langchain_core.tools import tool
from app.utils.logger import log_json

logger = logging.getLogger(__name__)

@tool
def send_gmail(lead_info: dict) -> str:
    """
    Mock notification: Simulate sending a confirmation via Gmail.
    """
    name = lead_info.get("name", "there")
    message = f"📩 Email sent to {name} via Gmail: Thanks for your interest in a property!"
    log_json("Gmail Notification", {"to": name, "message": message})
    return message

@tool
def send_outlook(lead_info: dict) -> str:
    """
    Mock notification: Simulate sending a confirmation via Outlook.
    """
    name = lead_info.get("name", "there")
    message = f"📩 Email sent to {name} via Outlook: We'll follow up with more info soon."
    log_json("Outlook Notification", {"to": name, "message": message})
    return message
