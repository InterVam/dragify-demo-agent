from app.agent.tools.lead_extraction import extract_lead_info
from app.agent.tools.data_sources import fetch_from_postgres
from app.agent.tools.crm import insert_into_zoho, insert_into_odoo
from app.agent.tools.notify import send_gmail_notification, send_outlook_notification

TOOL_REGISTRY = {
    "extract_lead_info": extract_lead_info,
    "postgresql": fetch_from_postgres,
    "fetch_from_postgres": fetch_from_postgres,
    "zoho": insert_into_zoho,
    "insert_into_zoho": insert_into_zoho,
    "odoo": insert_into_odoo,
    "insert_into_odoo": insert_into_odoo,
    "send_gmail_notification": send_gmail_notification,
    "send_outlook_notification": send_outlook_notification
}
