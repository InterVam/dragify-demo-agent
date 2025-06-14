# app/tools/data_sources.py

import logging
from langchain_core.tools import tool
from sqlalchemy import select, and_
from app.db.session import AsyncSessionLocal
from app.db.models import Project

logger = logging.getLogger(__name__)

@tool
async def fetch_from_postgres(
    location: str = "",
    property_type: str = "",
    bedrooms: str = "",
    budget: int = 0,
    first_name: str = "",
    last_name: str = "",
    phone: str = "",
    team_id: str = ""
) -> dict:
    """Find matching projects from database. Returns enhanced lead info."""
    try:
        location = location.strip()
        property_type = property_type.strip().lower()
        bedrooms = int(bedrooms or 0)
        budget = int(budget or 0)
        tolerance = 200_000

        logger.info(f"[fetch_from_postgres] Searching: location={location}, type={property_type}, bedrooms={bedrooms}, budget={budget}")

        async with AsyncSessionLocal() as session:
            stmt = select(Project).where(
                and_(
                    Project.location.ilike(f"%{location}%"),
                    Project.property_type.ilike(f"%{property_type}%"),
                    Project.min_price <= budget + tolerance,
                    Project.max_price >= budget - tolerance,
                    Project.min_bedrooms <= bedrooms,
                    Project.max_bedrooms >= bedrooms,
                )
            )
            result = await session.execute(stmt)
            matched = result.scalars().all()

        lead_info_enhanced = {
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "location": location,
            "property_type": property_type,
            "bedrooms": bedrooms,
            "budget": budget,
            "team_id": team_id,
            "matched_projects": [p.name for p in matched] if matched else []
        }

        return lead_info_enhanced

    except Exception as e:
        logger.error(f"[fetch_from_postgres] Error: {str(e)}", exc_info=True)
        return {
            "first_name": first_name,
            "last_name": last_name,
            "phone": phone,
            "location": location,
            "property_type": property_type,
            "bedrooms": bedrooms,
            "budget": budget,
            "team_id": team_id,
            "matched_projects": []
        }

