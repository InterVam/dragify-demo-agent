# app/agent/tools/insert_into_zoho.py

import logging
from langchain_core.tools import tool
from app.services.zoho_service import ZohoService
from app.config.zoho_config import ZohoConfig

logger = logging.getLogger(__name__)

@tool
async def insert_into_zoho(lead_info: dict) -> str:
    """
    Inserts enriched lead info into Zoho CRM.

    Args:
        lead_info (dict): Must contain all extracted + enriched lead details including 'team_id'.

    Returns:
        str: Success or error message from Zoho CRM
    """
    try:
        team_id = lead_info.get("team_id")
        if not team_id:
            return "Missing team_id in lead_info."

        config = ZohoConfig()
        zoho = ZohoService(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=config.redirect_uri
        )
        result = await zoho.insert_lead(user_id=team_id, lead_info=lead_info)

        if result.get("data") and result["data"][0].get("code") == "SUCCESS":
            return "✅ Lead inserted into Zoho CRM successfully."
        else:
            logger.warning(f"[insert_into_zoho] Zoho response: {result}")
            return "❌ Failed to insert lead into Zoho CRM."

    except Exception as e:
        logger.error(f"[insert_into_zoho] Error: {str(e)}", exc_info=True)
        return "❌ Zoho CRM insertion failed due to internal error."


@tool
def insert_into_odoo(lead_info: dict) -> str:
    """
    Mock CRM submission: Simulate sending lead info to Odoo.
    """
    log_json("CRM - Odoo Lead Submitted", lead_info)
    return f"✅ Lead '{lead_info.get('name')}' successfully inserted into Odoo CRM."
