# app/db/crud.py
from datetime import datetime, timedelta
from sqlalchemy.future import select
from app.db.session import AsyncSessionLocal
from app.db.models import SlackInstallation, Project, Lead, ZohoInstallation, Team
import logging

logger = logging.getLogger(__name__)

async def ensure_team_exists(team_id: str, team_name: str = None, domain: str = None, session_id: str = None) -> Team:
    """
    Ensure a team record exists, create if it doesn't
    Now includes session_id for user isolation
    """
    async with AsyncSessionLocal() as session:
        stmt = select(Team).where(Team.team_id == team_id)
        result = await session.execute(stmt)
        team = result.scalar_one_or_none()
        
        if not team:
            # Create new team with session association
            team = Team(
                team_id=team_id,
                team_name=team_name,
                domain=domain,
                session_id=session_id,
                is_active=True
            )
            session.add(team)
            await session.commit()
            logger.info(f"Created new team: {team_id} ({team_name}) for session: {session_id}")
        else:
            # Update existing team if new info provided
            updated = False
            if team_name and team.team_name != team_name:
                team.team_name = team_name
                updated = True
            if domain and team.domain != domain:
                team.domain = domain
                updated = True
            if session_id and team.session_id != session_id:
                team.session_id = session_id
                updated = True
            
            if updated:
                await session.commit()
                logger.info(f"Updated team: {team_id}")
        
        return team

async def get_matching_projects(location: str, budget: int, bedrooms: int, property_type: str):
    async with AsyncSessionLocal() as session:
        stmt = select(Project).where(
            Project.location.ilike(f"%{location}%"),
            Project.min_price <= budget,
            Project.max_price >= budget,
            Project.min_bedrooms <= bedrooms,
            Project.max_bedrooms >= bedrooms,
            Project.property_type.ilike(f"%{property_type}%")
        )
        result = await session.execute(stmt)
        return result.scalars().all()

async def upsert_slack_installation(team_id: str, access_token: str, bot_user_id: str, team_name: str = "", domain: str = "", session_id: str = None):
    """
    Insert or update Slack installation and ensure team exists
    """
    # First, ensure the team exists with session association
    await ensure_team_exists(team_id, team_name, domain, session_id)
    
    async with AsyncSessionLocal() as session:
        stmt = select(SlackInstallation).where(SlackInstallation.team_id == team_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.access_token = access_token
            existing.bot_user_id = bot_user_id
            existing.installed = True
            existing.updated_at = datetime.utcnow()
        else:
            new_install = SlackInstallation(
                team_id=team_id,
                access_token=access_token,
                bot_user_id=bot_user_id,
                installed=True
            )
            session.add(new_install)

        await session.commit()
        logger.info(f"Upserted Slack installation for team: {team_id}")

async def get_slack_token_by_team(team_id: str) -> str | None:
    async with AsyncSessionLocal() as session:
        stmt = select(SlackInstallation.access_token).where(SlackInstallation.team_id == team_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def upsert_zoho_installation(team_id: str, access_token: str, refresh_token: str, api_domain: str, expires_in: int, session_id: str = None):
    """
    Insert or update a Zoho token record for a Slack team and ensure team exists.
    """
    # First, ensure the team exists
    await ensure_team_exists(team_id, session_id=session_id)
    
    expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
    async with AsyncSessionLocal() as session:
        stmt = select(ZohoInstallation).where(ZohoInstallation.team_id == team_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.access_token = access_token
            existing.refresh_token = refresh_token
            existing.api_domain = api_domain
            existing.expires_at = expires_at
            existing.updated_at = datetime.utcnow()
        else:
            new_install = ZohoInstallation(
                team_id=team_id,
                access_token=access_token,
                refresh_token=refresh_token,
                api_domain=api_domain,
                expires_at=expires_at
            )
            session.add(new_install)

        await session.commit()
        logger.info(f"Upserted Zoho installation for team: {team_id}")

async def get_zoho_tokens_by_team(team_id: str) -> ZohoInstallation | None:
    """
    Retrieve Zoho tokens for a specific Slack team.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(ZohoInstallation).where(ZohoInstallation.team_id == team_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

async def get_teams_by_session(session_id: str):
    """
    Get all teams associated with a specific session
    """
    async with AsyncSessionLocal() as session:
        stmt = select(Team).where(Team.session_id == session_id, Team.is_active == True)
        result = await session.execute(stmt)
        return result.scalars().all()

async def get_team_by_id_and_session(team_id: str, session_id: str) -> Team | None:
    """
    Get a specific team only if it belongs to the session
    """
    async with AsyncSessionLocal() as session:
        stmt = select(Team).where(
            Team.team_id == team_id, 
            Team.session_id == session_id,
            Team.is_active == True
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
