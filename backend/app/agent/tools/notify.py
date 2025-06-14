import logging
from langchain_core.tools import tool

logger = logging.getLogger(__name__)

@tool
async def send_gmail_notification(lead_info: dict = None, success: bool = True, error_message: str = "", team_id: str = "", lead_info_enhanced: dict = None) -> str:
    """Send email notification via Gmail. Use lead_info_enhanced if available, otherwise lead_info."""
    try:
        # Import here to avoid circular imports and startup issues
        from app.services.gmail_service import GmailService
        from app.config.gmail_config import GmailConfig
        
        config = GmailConfig()
        gmail_service = GmailService(
            client_id=config.client_id,
            client_secret=config.client_secret,
            redirect_uri=config.redirect_uri
        )
        
        # Use lead_info_enhanced if available and lead_info is empty
        actual_lead_info = lead_info or {}
        if lead_info_enhanced and (not actual_lead_info or not actual_lead_info.get('first_name')):
            actual_lead_info = lead_info_enhanced
            
        team_id_local = team_id or actual_lead_info.get("team_id", "")
        
        if success:
            subject = f"✅ New Lead Processed Successfully - {actual_lead_info.get('first_name', '')} {actual_lead_info.get('last_name', '')}"
            body_html = gmail_service.generate_lead_success_email(actual_lead_info, {"status": "success"})
        else:
            subject = f"❌ Lead Processing Failed - {actual_lead_info.get('first_name', '')} {actual_lead_info.get('last_name', '')}"
            body_html = gmail_service.generate_lead_failure_email(actual_lead_info, error_message)
        
        await gmail_service.send_notification_email(
            team_id=team_id_local,
            subject=subject,
            body_html=body_html
        )
        
        logger.info(f"[Gmail Notification] Sent {'success' if success else 'failure'} notification for team {team_id_local}")
        
        return "📧 Email notification sent successfully"
        
    except Exception as e:
        logger.error(f"[Gmail Notification] Error sending notification: {e}")
        return f"❌ Failed to send email notification: {str(e)}"

@tool
async def send_outlook_notification(lead_info: dict, success: bool = True, error_message: str = "") -> str:
    """Send email notification via Outlook."""
    logger.info(f"[Outlook Notification] Mock notification for team {lead_info.get('team_id', '')}")
    return "📧 Outlook notification (mock) sent successfully"
