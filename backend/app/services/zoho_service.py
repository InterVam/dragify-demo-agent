import logging
import httpx
from datetime import datetime, timedelta
from sqlalchemy.exc import SQLAlchemyError
from app.db.session import AsyncSessionLocal
from app.db.models import ZohoInstallation
from sqlalchemy import select

logger = logging.getLogger(__name__)

ZOHO_TOKEN_URL = "https://accounts.zoho.com/oauth/v2/token"

class ZohoService:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri

    def get_authorization_url(self, team_id: str) -> str:
        """Generate Zoho OAuth authorization URL with team_id as state"""
        base_url = "https://accounts.zoho.com/oauth/v2/auth"
        params = {
            "scope": "ZohoCRM.modules.ALL,ZohoCRM.settings.ALL",
            "client_id": self.client_id,
            "response_type": "code",
            "access_type": "offline",
            "redirect_uri": self.redirect_uri,
            "state": team_id
        }
        
        # Build URL with parameters
        param_string = "&".join([f"{key}={value}" for key, value in params.items()])
        return f"{base_url}?{param_string}"

    async def exchange_code_for_tokens(self, code: str, team_id: str):
        payload = {
            "code": code,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(ZOHO_TOKEN_URL, data=payload)
                res.raise_for_status()
                data = res.json()
        except httpx.HTTPError as e:
            logger.error(f"[ZohoService] HTTP error during token exchange: {e}")
            raise
        except Exception as e:
            logger.error(f"[ZohoService] Unexpected error during token exchange: {e}")
            raise

        logger.info(f"[ZohoService] Token exchange response: {data}")

        expires_in = int(data.get("expires_in", 0))
        
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(ZohoInstallation).where(ZohoInstallation.team_id == team_id)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    existing.access_token = data["access_token"]
                    if data.get("refresh_token"):
                        existing.refresh_token = data["refresh_token"]
                    existing.api_domain = data.get("api_domain", "https://www.zohoapis.com")
                    existing.expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
                else:
                    session.add(ZohoInstallation(
                        team_id=team_id,
                        access_token=data["access_token"],
                        refresh_token=data.get("refresh_token"),
                        api_domain=data.get("api_domain", "https://www.zohoapis.com"),
                        expires_at=datetime.utcnow() + timedelta(seconds=expires_in)
                    ))

                await session.commit()
        except SQLAlchemyError as e:
            logger.error(f"[ZohoService] Database error during token storage: {e}")
            raise
        except Exception as e:
            logger.error(f"[ZohoService] Unexpected error during token storage: {e}")
            raise

    async def _refresh_access_token(self, tokens: ZohoInstallation):
        logger.info("[ZohoService] Refreshing Zoho access token for team %s", tokens.team_id)
        payload = {
            "refresh_token": tokens.refresh_token,
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "refresh_token",
        }
        
        try:
            async with httpx.AsyncClient() as client:
                res = await client.post(ZOHO_TOKEN_URL, data=payload)
                res.raise_for_status()
                data = res.json()
        except httpx.HTTPError as e:
            logger.error(f"[ZohoService] HTTP error during token refresh: {e}")
            raise
        except Exception as e:
            logger.error(f"[ZohoService] Unexpected error during token refresh: {e}")
            raise

        logger.info(f"[ZohoService] Refresh response: {data}")
        tokens.access_token = data["access_token"]
        tokens.expires_at = datetime.utcnow() + timedelta(seconds=int(data.get("expires_in", 0)))
        
        # persist updated token
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(ZohoInstallation).where(ZohoInstallation.team_id == tokens.team_id)
                result = await session.execute(stmt)
                obj = result.scalar_one()
                obj.access_token = tokens.access_token
                obj.expires_at = tokens.expires_at
                await session.commit()
        except SQLAlchemyError as e:
            logger.error(f"[ZohoService] Database error during token refresh storage: {e}")
            raise
        except Exception as e:
            logger.error(f"[ZohoService] Unexpected error during token refresh storage: {e}")
            raise

    async def insert_lead(self, team_id: str, lead_info: dict):
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(ZohoInstallation).where(ZohoInstallation.team_id == team_id)
                result = await session.execute(stmt)
                tokens = result.scalar_one_or_none()
                if not tokens:
                    raise Exception(f"No Zoho tokens found for team_id: {team_id}")
        except SQLAlchemyError as e:
            logger.error(f"[ZohoService] Database error retrieving tokens: {e}")
            raise
        except Exception as e:
            logger.error(f"[ZohoService] Error retrieving tokens: {e}")
            raise

        # Use the stored api_domain instead of hardcoded value
        url = f"{tokens.api_domain}/crm/v2/Leads"
        payload = {
            "data": [{
                "First_Name": lead_info.get("first_name") or "Unknown",
                "Last_Name": lead_info.get("last_name") or "Unknown",
                "Phone": lead_info.get("phone"),
                "City": lead_info.get("location"),
                "Lead_Source": "Slack Bot",
                "Description": (
                    f"Looking for a {lead_info.get('bedrooms')} bedroom {lead_info.get('property_type')} "
                    f"with budget {lead_info.get('budget')}.\n"
                    f"Matched Projects: {', '.join(lead_info.get('matched_projects', []))}"
                )
            }]
        }

        headers = {"Authorization": f"Zoho-oauthtoken {tokens.access_token}"}

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, headers=headers, json=payload)

            # If token expired, refresh and retry once
            if response.status_code == 401 and response.json().get("code") == "INVALID_TOKEN":
                await self._refresh_access_token(tokens)
                headers["Authorization"] = f"Zoho-oauthtoken {tokens.access_token}"
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, headers=headers, json=payload)

            # Raise for other errors
            response.raise_for_status()
            data = response.json()
            logger.info(f"[ZohoService] Insert lead response: {data}")
            return data
        except httpx.HTTPError as e:
            logger.error(f"[ZohoService] HTTP error during lead insertion: {e}")
            raise
        except Exception as e:
            logger.error(f"[ZohoService] Unexpected error during lead insertion: {e}")
            raise
