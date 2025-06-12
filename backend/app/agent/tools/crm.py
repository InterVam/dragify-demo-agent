import logging
from langchain_core.tools import tool
from app.utils.logger import log_json

logger = logging.getLogger(__name__)

@tool
def insert_into_zoho(lead_info: dict) -> str:
    """
    Mock CRM submission: Simulate sending lead info to Zoho.
    """
    log_json("CRM - Zoho Lead Submitted", lead_info)
    return f"✅ Lead '{lead_info.get('name')}' successfully inserted into Zoho CRM."

@tool
def insert_into_odoo(lead_info: dict) -> str:
    """
    Mock CRM submission: Simulate sending lead info to Odoo.
    """
    log_json("CRM - Odoo Lead Submitted", lead_info)
    return f"✅ Lead '{lead_info.get('name')}' successfully inserted into Odoo CRM."
