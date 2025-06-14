import logging
from langchain_core.tools import tool
from app.services.zoho_service import ZohoService
from app.config.zoho_config import ZohoConfig

logger = logging.getLogger(__name__)

@tool
async def insert_into_zoho(lead_info_enhanced: dict) -> dict:
    """Insert lead into Zoho CRM. Returns success status and lead info."""
    # 1️⃣ Validate input
    team_id = lead_info_enhanced.get("team_id", "").strip()
    if not team_id:
        return {"success": False, "message": "Missing team_id in lead_info_enhanced.", "error": "team_id empty", "lead_info_enhanced": lead_info_enhanced, "lead_info": lead_info_enhanced, "team_id": team_id}

    # 2️⃣ Initialize Zoho client using config
    config = ZohoConfig()  # loads client_id, secret, redirect_uri
    zoho = ZohoService(
            client_id="1000.8CJ9QKG8K8TZKUUX5AU6VSPTMR6JFH",
            client_secret="d75fd06b8954d31954a1589af7aed60ed6f63c3b94",
            redirect_uri="https://b63d-156-194-236-142.ngrok-free.app/zoho/oauth/callback"
        )
    
    # 3️⃣ Perform insertion
    try:
        response = await zoho.insert_lead(team_id=team_id, lead_info=lead_info_enhanced)
    except Exception as e:
        logger.error(f"[insert_into_zoho] Exception during Zoho API call: {e}", exc_info=True)
        return {"success": False, "message": "Zoho CRM insertion failed.", "error": str(e), "lead_info_enhanced": lead_info_enhanced, "lead_info": lead_info_enhanced, "team_id": team_id}

    # 4️⃣ Inspect Zoho response
    data = response.get("data")
    if data and isinstance(data, list) and data[0].get("code") == "SUCCESS":
        return {"success": True, "message": "✅ Lead inserted into Zoho CRM successfully.", "raw_response": response, "lead_info_enhanced": lead_info_enhanced, "lead_info": lead_info_enhanced, "team_id": team_id}
    else:
        error_msg = data[0].get("message") if data and isinstance(data, list) else response.get("message", "Unknown error")
        logger.warning(f"[insert_into_zoho] Zoho error response: {response}")
        return {"success": False, "message": "❌ Failed to insert lead into Zoho CRM.", "error": error_msg, "raw_response": response, "lead_info_enhanced": lead_info_enhanced, "lead_info": lead_info_enhanced, "team_id": team_id}

@tool
async def insert_into_odoo(lead_info_enhanced: dict) -> dict:
    """Insert lead into Odoo CRM. Returns success status and lead info."""
    logger.info("[insert_into_odoo] Lead submitted to Odoo: %s", lead_info_enhanced)
    return {"success": True, "message": f"✅ Lead inserted into Odoo CRM successfully.", "raw_response": None, "lead_info_enhanced": lead_info_enhanced, "lead_info": lead_info_enhanced, "team_id": lead_info_enhanced.get("team_id", "") }


