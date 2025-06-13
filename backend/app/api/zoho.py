from fastapi import APIRouter, Request, HTTPException, Query
from app.services.zoho_service import ZohoService
from app.config.zoho_config import ZohoConfig
import logging

router = APIRouter(prefix="/zoho", tags=["Zoho"])
logger = logging.getLogger(__name__)

# Initialize service with config
zoho_service = ZohoService(
    client_id=ZohoConfig.client_id,
    client_secret=ZohoConfig.client_secret,
    redirect_uri=ZohoConfig.redirect_uri
)

@router.get("/oauth/callback")
async def zoho_oauth_callback(code: str = Query(...), state: str = Query(...)):
    """
    Callback endpoint for Zoho OAuth. Expects a code and state (user_id).
    """
    try:
        logger.info(f"[Zoho OAuth] Callback received for user_id={state}")
        await zoho_service.exchange_code_for_tokens(code=code, user_id=state)
        return {"status": "success", "message": "Zoho integration successful."}
    except Exception as e:
        logger.error(f"[Zoho OAuth] Error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Zoho OAuth callback failed.")


@router.post("/leads/{user_id}")
async def insert_zoho_lead(user_id: str, lead_info: dict):
    """
    Insert a lead into Zoho CRM using stored access tokens for the given user.
    """
    try:
        response = await zoho_service.insert_lead(user_id=user_id, lead_info=lead_info)
        return {"status": "success", "zoho_response": response}
    except Exception as e:
        logger.error(f"[Zoho Lead] Error inserting lead for {user_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Zoho lead insertion failed.")
