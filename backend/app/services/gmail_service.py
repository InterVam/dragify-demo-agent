import logging
import base64
import json
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, Any, Optional

import httpx
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import AsyncSessionLocal
from app.db.models import GmailInstallation
from app.config.gmail_config import GmailConfig
from sqlalchemy import select
from app.db.crud import ensure_team_exists

logger = logging.getLogger(__name__)

class GmailService:
    def __init__(self, client_id: str, client_secret: str, redirect_uri: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.config = GmailConfig()

    def get_authorization_url(self, team_id: str) -> str:
        """Generate Gmail OAuth authorization URL with team_id as state"""
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": [self.redirect_uri]
                }
            },
            scopes=self.config.SCOPES
        )
        flow.redirect_uri = self.redirect_uri
        
        authorization_url, _ = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true',
            prompt='consent',  # Force consent screen to ensure refresh token
            state=team_id
        )
        return authorization_url

    async def exchange_code_for_tokens(self, code: str, team_id: str):
        """Exchange authorization code for tokens and store in database"""
        try:
            flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.redirect_uri]
                    }
                },
                scopes=self.config.SCOPES
            )
            flow.redirect_uri = self.redirect_uri
            
            # Exchange code for tokens
            flow.fetch_token(code=code)
            credentials = flow.credentials
            
            # Get user email
            user_email = await self._get_user_email(credentials)
            
            # Store tokens in database
            await self._store_tokens(team_id, credentials, user_email)
            
            logger.info(f"[GmailService] Successfully stored tokens for team {team_id}")
            
        except Exception as e:
            logger.error(f"[GmailService] Error exchanging code for tokens: {e}")
            raise

    async def _get_user_email(self, credentials: Credentials) -> str:
        """Get user email using OAuth2 userinfo endpoint"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {credentials.token}"}
                )
                response.raise_for_status()
                user_info = response.json()
                return user_info.get("email", "")
        except Exception as e:
            logger.error(f"[GmailService] Error getting user email: {e}")
            return ""

    async def _store_tokens(self, team_id: str, credentials: Credentials, user_email: str):
        """Store or update Gmail tokens in database and ensure team exists"""
        try:
            # First, ensure the team exists
            await ensure_team_exists(team_id)
            
            async with AsyncSessionLocal() as session:
                stmt = select(GmailInstallation).where(GmailInstallation.team_id == team_id)
                result = await session.execute(stmt)
                existing = result.scalar_one_or_none()

                # Normalize expiry to naive UTC datetime for consistent comparisons
                if credentials.expiry:
                    expires_at = credentials.expiry.replace(tzinfo=None)
                else:
                    expires_at = (datetime.utcnow() + timedelta(hours=1)).replace(tzinfo=None)

                if existing:
                    existing.access_token = credentials.token
                    existing.refresh_token = credentials.refresh_token
                    existing.user_email = user_email
                    existing.expires_at = expires_at
                else:
                    session.add(GmailInstallation(
                        team_id=team_id,
                        access_token=credentials.token,
                        refresh_token=credentials.refresh_token,
                        user_email=user_email,
                        expires_at=expires_at
                    ))

                await session.commit()
                logger.info(f"[GmailService] Stored tokens for team {team_id}")
        except SQLAlchemyError as e:
            logger.error(f"[GmailService] Database error storing tokens: {e}")
            raise
        except Exception as e:
            logger.error(f"[GmailService] Unexpected error storing tokens: {e}")
            raise

    async def _refresh_access_token(self, installation: GmailInstallation):
        """Refresh expired access token"""
        try:
            # Check if we have a refresh token
            if not installation.refresh_token:
                logger.error(f"[GmailService] No refresh token available for team {installation.team_id}")
                raise ValueError("No refresh token available - user needs to re-authorize")
            
            # Create credentials with all required fields
            credentials = Credentials(
                token=installation.access_token,
                refresh_token=installation.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret,
                scopes=self.config.SCOPES  # Add scopes for proper refresh
            )
            
            # Refresh the token
            credentials.refresh(Request())
            
            # Normalize expiry to naive UTC datetime
            if credentials.expiry:
                expires_at = credentials.expiry.replace(tzinfo=None)
            else:
                expires_at = (datetime.utcnow() + timedelta(hours=1)).replace(tzinfo=None)
            
            # Update stored tokens in database
            async with AsyncSessionLocal() as session:
                stmt = select(GmailInstallation).where(GmailInstallation.team_id == installation.team_id)
                result = await session.execute(stmt)
                obj = result.scalar_one_or_none()
                
                if obj:
                    obj.access_token = credentials.token
                    obj.expires_at = expires_at
                    # Update refresh token if a new one was provided
                    if credentials.refresh_token:
                        obj.refresh_token = credentials.refresh_token
                    await session.commit()
                    
                    # Update the installation object for immediate use
                    installation.access_token = credentials.token
                    installation.expires_at = expires_at
                    if credentials.refresh_token:
                        installation.refresh_token = credentials.refresh_token
                else:
                    logger.error(f"[GmailService] Installation not found for team {installation.team_id}")
                    raise ValueError("Installation not found in database")
                
            logger.info(f"[GmailService] Successfully refreshed tokens for team {installation.team_id}")
            
        except Exception as e:
            logger.error(f"[GmailService] Error refreshing tokens: {e}")
            # If refresh fails, the user needs to re-authorize
            if "invalid_grant" in str(e) or "invalid_request" in str(e):
                logger.warning(f"[GmailService] Refresh token invalid for team {installation.team_id} - user needs to re-authorize")
            raise

    async def send_notification_email(self, team_id: str, subject: str, body_html: str, recipient: Optional[str] = None):
        """Send notification email for lead processing results"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(GmailInstallation).where(GmailInstallation.team_id == team_id)
                result = await session.execute(stmt)
                installation = result.scalar_one_or_none()
                
                if not installation:
                    # Fall back to admin email if no Gmail integration
                    logger.warning(f"[GmailService] No Gmail tokens for team {team_id}, using admin email")
                    recipient = recipient or self.config.ADMIN_EMAIL
                    await self._send_fallback_email(subject, body_html, recipient)
                    return

            # Check if token needs refresh (handle tz-aware vs naive)
            now_utc = datetime.utcnow()
            exp = installation.expires_at
            if exp.tzinfo is not None:
                exp = exp.replace(tzinfo=None)

            if exp <= now_utc:
                try:
                    await self._refresh_access_token(installation)
                except Exception as refresh_error:
                    logger.error(f"[GmailService] Failed to refresh token for team {team_id}: {refresh_error}")
                    # Fall back to admin email if token refresh fails
                    recipient = recipient or self.config.ADMIN_EMAIL
                    await self._send_fallback_email(subject, body_html, recipient)
                    return

            # Build Gmail service
            credentials = Credentials(
                token=installation.access_token,
                refresh_token=installation.refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=self.client_id,
                client_secret=self.client_secret
            )
            
            service = build('gmail', 'v1', credentials=credentials)
            
            # Create email message
            to_email = recipient or self.config.ADMIN_EMAIL
            from_email = installation.user_email or self.config.FROM_EMAIL
            
            message = MIMEMultipart('alternative')
            message['to'] = to_email
            message['from'] = from_email
            message['subject'] = subject
            
            # Add HTML body
            html_part = MIMEText(body_html, 'html')
            message.attach(html_part)
            
            # Encode message
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send email
            service.users().messages().send(
                userId='me',
                body={'raw': raw_message}
            ).execute()
            
            logger.info(f"[GmailService] Sent email to {to_email} for team {team_id}")
            
        except Exception as e:
            logger.error(f"[GmailService] Error sending email: {e}")
            # Don't raise - email failures shouldn't break the main workflow
            
    async def _send_fallback_email(self, subject: str, body_html: str, recipient: str):
        """Fallback method when no Gmail integration is available"""
        logger.info(f"[GmailService] Fallback email would be sent to {recipient}: {subject}")
        # In a real implementation, this could use SMTP or another email service
    
    async def revoke_tokens(self, team_id: str):
        """Revoke and delete stored tokens for a team"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(GmailInstallation).where(GmailInstallation.team_id == team_id)
                result = await session.execute(stmt)
                installation = result.scalar_one_or_none()
                
                if installation:
                    # Revoke the token with Google
                    try:
                        async with httpx.AsyncClient() as client:
                            await client.post(
                                f"https://oauth2.googleapis.com/revoke?token={installation.access_token}"
                            )
                    except Exception as e:
                        logger.warning(f"[GmailService] Failed to revoke token with Google: {e}")
                    
                    # Delete from database
                    await session.delete(installation)
                    await session.commit()
                    logger.info(f"[GmailService] Revoked and deleted tokens for team {team_id}")
                    
        except Exception as e:
            logger.error(f"[GmailService] Error revoking tokens: {e}")
            raise

    def generate_lead_success_email(self, lead_info: Dict[str, Any], crm_response: Dict[str, Any]) -> str:
        """Generate HTML email for successful lead processing"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #28a745;">✅ New Lead Successfully Processed</h2>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3>Lead Information:</h3>
                <ul>
                    <li><strong>Name:</strong> {lead_info.get('first_name', '')} {lead_info.get('last_name', '')}</li>
                    <li><strong>Phone:</strong> {lead_info.get('phone', 'Not provided')}</li>
                    <li><strong>Location:</strong> {lead_info.get('location', 'Not provided')}</li>
                    <li><strong>Property Type:</strong> {lead_info.get('property_type', 'Not specified')}</li>
                    <li><strong>Bedrooms:</strong> {lead_info.get('bedrooms', 'Not specified')}</li>
                    <li><strong>Budget:</strong> {lead_info.get('budget', 'Not specified')}</li>
                </ul>
            </div>
            
            <div style="background-color: #e7f3ff; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3>Matched Projects:</h3>
                <ul>
                    {self._format_projects_list(lead_info.get('matched_projects', []))}
                </ul>
            </div>
            
            <div style="background-color: #d4edda; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>CRM Status:</strong> Successfully added to Zoho CRM</p>
                <p><strong>Team ID:</strong> {lead_info.get('team_id', '')}</p>
            </div>
            
            <hr style="margin: 30px 0;">
            <p style="color: #6c757d; font-size: 12px;">
                This is an automated notification from Dragify AI Agent.<br>
                Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            </p>
        </body>
        </html>
        """

    def generate_lead_failure_email(self, lead_info: Dict[str, Any], error_message: str) -> str:
        """Generate HTML email for failed lead processing"""
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2 style="color: #dc3545;">❌ Lead Processing Failed</h2>
            
            <div style="background-color: #f8d7da; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #dc3545;">
                <h3>Error Details:</h3>
                <p><strong>Error:</strong> {error_message}</p>
                <p><strong>Team ID:</strong> {lead_info.get('team_id', '')}</p>
            </div>
            
            <div style="background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3>Lead Information (for manual processing):</h3>
                <ul>
                    <li><strong>Name:</strong> {lead_info.get('first_name', '')} {lead_info.get('last_name', '')}</li>
                    <li><strong>Phone:</strong> {lead_info.get('phone', 'Not provided')}</li>
                    <li><strong>Location:</strong> {lead_info.get('location', 'Not provided')}</li>
                    <li><strong>Property Type:</strong> {lead_info.get('property_type', 'Not specified')}</li>
                    <li><strong>Bedrooms:</strong> {lead_info.get('bedrooms', 'Not specified')}</li>
                    <li><strong>Budget:</strong> {lead_info.get('budget', 'Not specified')}</li>
                </ul>
            </div>
            
            <div style="background-color: #fff3cd; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p><strong>Action Required:</strong> Please manually add this lead to your CRM system.</p>
            </div>
            
            <hr style="margin: 30px 0;">
            <p style="color: #6c757d; font-size: 12px;">
                This is an automated notification from Dragify AI Agent.<br>
                Generated at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC
            </p>
        </body>
        </html>
        """

    def _format_projects_list(self, projects: list) -> str:
        """Format projects list as HTML list items"""
        if not projects:
            return "<li>No matching projects found</li>"
        return "".join([f"<li>{project}</li>" for project in projects]) 