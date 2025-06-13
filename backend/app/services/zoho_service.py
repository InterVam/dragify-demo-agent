import logging
import httpx
from datetime import datetime, timedelta
from app.db.session import AsyncSessionLocal
from app.db.models import ZohoInstallation
from sqlalchemy import select, update

logger = logging.getLogger(__name__)

ZOHO_TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"
ZOHO_API_BASE = "https://www.zohoapis.com/crm/v2"

class ZohoService:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    async def exchange_code_for_tokens(self, code: str, team_id: str):
        payload = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient() as client:
            res = await client.post(ZOHO_TOKEN_URL, data=payload)
            data = res.json()

        logger.info(f"[ZohoService] Token exchange response: {data}")

        async with AsyncSessionLocal() as session:
            stmt = select(ZohoInstallation).where(ZohoInstallation.team_id == team_id)
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()

            if existing:
                existing.access_token = data["access_token"]
                existing.refresh_token = data.get("refresh_token")
                existing.api_domain = data.get("api_domain", "https://www.zohoapis.com")
                existing.expires_at = datetime.utcnow() + timedelta(seconds=int(data["expires_in"]))
            else:
                session.add(ZohoInstallation(
                    team_id=team_id,
                    access_token=data["access_token"],
                    refresh_token=data.get("refresh_token"),
                    api_domain=data.get("api_domain", "https://www.zohoapis.com"),
                    expires_at=datetime.utcnow() + timedelta(seconds=int(data["expires_in"]))
                ))

            await session.commit()

    async def insert_lead(self, team_id: str, lead_info: dict):
        async with AsyncSessionLocal() as session:
            stmt = select(ZohoInstallation).where(ZohoInstallation.team_id == team_id)
            result = await session.execute(stmt)
            tokens = result.scalar_one_or_none()
            if not tokens:
                raise Exception(f"No Zoho tokens found for team_id: {team_id}")

            url = f"{tokens.api_domain or ZOHO_API_BASE}/Leads"
            payload = {
                "data": [
                    {
                        "Last_Name": lead_info.get("name") or "Unknown",
                        "Phone": lead_info.get("phone"),
                        "City": lead_info.get("location"),
                        "Lead_Source": "Slack Bot",
                        "Description": f"Looking for a {lead_info.get('bedrooms')} bedroom {lead_info.get('property_type')} "
                                       f"with budget {lead_info.get('budget')}.\n"
                                       f"Matched Projects: {', '.join(lead_info.get('matched_projects', []))}"
                    }
                ]
            }

            headers = {
                "Authorization": f"Zoho-oauthtoken {tokens.access_token}"
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)
                logger.info(f"[ZohoService] Insert lead response: {response.status_code} {response.text}")
                return response.json()
