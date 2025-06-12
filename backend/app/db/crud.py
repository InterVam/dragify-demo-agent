# app/db/crud.py
from sqlalchemy.future import select
from app.db.session import AsyncSessionLocal
from app.db.models import SlackInstallation
from app.db.models import Project, Lead
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
