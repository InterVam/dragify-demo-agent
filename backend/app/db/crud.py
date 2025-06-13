# app/db/crud.py
from sqlalchemy.future import select
from app.db.session import AsyncSessionLocal
from app.db.models import SlackInstallation
from app.db.models import Project, Lead
from app.db.models import ZohoInstallation
import uuid

async def get_matching_projects(location: str, budget: int, bedrooms: int, property_type: str):
    async with AsyncSessionLocal() as session:
        stmt = select(Project).where(
            Project.location.ilike(f"%{location}%"),
            Project.min_price <= budget,
            Project.max_price >= budget,
            Project.min_bedrooms <= bedrooms,
            Project.max_bedrooms >= bedrooms,
            Project.property_type == property_type
        )
        result = await session.execute(stmt)
        return result.scalars().all()

async def upsert_slack_installation(team_id: str, access_token: str, bot_user_id: str, team_name: str = ""):
    async with AsyncSessionLocal() as session:
        stmt = select(SlackInstallation).where(SlackInstallation.team_id == team_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            existing.access_token = access_token
            existing.bot_user_id = bot_user_id
            existing.team_name = team_name
            existing.installed = True
        else:
            new_install = SlackInstallation(
                team_id=team_id,
                access_token=access_token,
                bot_user_id=bot_user_id,
                team_name=team_name,
            )
            session.add(new_install)

        await session.commit()


# Get Slack token by team ID
async def get_slack_token_by_team(team_id: str) -> str | None:
    async with AsyncSessionLocal() as session:
        stmt = select(SlackInstallation.access_token).where(SlackInstallation.team_id == team_id)
        result = await session.execute(stmt)
        token = result.scalar_one_or_none()
        return token

async def upsert_zoho_installation(user_id: str, access_token: str, refresh_token: str, api_domain: str, expires_in: int):
    """
    Insert or update a Zoho token record for a user.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(ZohoInstallation).where(ZohoInstallation.user_id == user_id)
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()

        expires_at = datetime.utcnow() + timedelta(seconds=expires_in)

        if existing:
            existing.access_token = access_token
            existing.refresh_token = refresh_token
            existing.api_domain = api_domain
            existing.expires_at = expires_at
        else:
            new_install = ZohoInstallation(
                user_id=user_id,
                access_token=access_token,
                refresh_token=refresh_token,
                api_domain=api_domain,
                expires_at=expires_at
            )
            session.add(new_install)

        await session.commit()


async def get_zoho_tokens_by_user(user_id: str) -> ZohoInstallation | None:
    """
    Retrieve Zoho tokens for a specific user.
    """
    async with AsyncSessionLocal() as session:
        stmt = select(ZohoInstallation).where(ZohoInstallation.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()