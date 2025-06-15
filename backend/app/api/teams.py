from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import List, Dict, Any
import logging

from app.db.session import AsyncSessionLocal
from app.db.models import Team, SlackInstallation, ZohoInstallation, GmailInstallation, EventLog
from app.db.crud import get_teams_by_session, get_team_by_id_and_session
from app.utils.session import SessionManager
from datetime import datetime

router = APIRouter(prefix="/teams", tags=["Teams"])
logger = logging.getLogger(__name__)

@router.post("/init-session", summary="Initialize user session")
async def init_session(request: Request):
    """
    Initialize a new session for the user
    Returns a session ID that should be used in subsequent requests
    """
    try:
        # Generate new session ID
        session_id = SessionManager.generate_session_id()
        
        # Create browser fingerprint for additional validation
        fingerprint = SessionManager.create_browser_fingerprint(request)
        
        logger.info(f"Initialized new session: {session_id} with fingerprint: {fingerprint}")
        
        return {
            "session_id": session_id,
            "fingerprint": fingerprint,
            "message": "Session initialized successfully"
        }
        
    except Exception as e:
        logger.error(f"Error initializing session: {e}")
        raise HTTPException(status_code=500, detail="Failed to initialize session")



@router.get("/", summary="List teams for current session")
async def list_teams(request: Request):
    """
    Get teams associated with the current session
    """
    try:
        # Try to get session ID from request
        session_id = SessionManager.get_session_id_from_request(request)
        
        async with AsyncSessionLocal() as session:
            if session_id:
                # Get teams for this session with their integrations
                stmt = select(Team).options(
                    selectinload(Team.slack_installation),
                    selectinload(Team.zoho_installation),
                    selectinload(Team.gmail_installation)
                ).where(
                    Team.session_id == session_id,
                    Team.is_active == True
                ).order_by(Team.created_at.desc())
            else:
                # Fallback: get all teams (for backward compatibility)
                stmt = select(Team).options(
                    selectinload(Team.slack_installation),
                    selectinload(Team.zoho_installation),
                    selectinload(Team.gmail_installation)
                ).where(Team.is_active == True).order_by(Team.created_at.desc())
            
            result = await session.execute(stmt)
            teams = result.scalars().all()
            
            teams_data = []
            for team in teams:
                # Check Gmail token expiry
                gmail_connected = False
                gmail_expired = True
                if team.gmail_installation:
                    now_utc = datetime.utcnow()
                    exp = team.gmail_installation.expires_at
                    if exp.tzinfo is not None:
                        exp = exp.replace(tzinfo=None)
                    gmail_expired = exp <= now_utc
                    gmail_connected = bool(team.gmail_installation.access_token and not gmail_expired)
                
                teams_data.append({
                    "team_id": team.team_id,
                    "team_name": team.team_name,
                    "domain": team.domain,
                    "created_at": team.created_at.isoformat(),
                    "integrations": {
                        "slack": {
                            "connected": bool(team.slack_installation and team.slack_installation.access_token),
                            "installed": team.slack_installation.installed if team.slack_installation else False
                        },
                        "zoho": {
                            "connected": bool(team.zoho_installation and team.zoho_installation.access_token),
                            "expires_at": team.zoho_installation.expires_at.isoformat() if team.zoho_installation else None
                        },
                        "gmail": {
                            "connected": gmail_connected,
                            "user_email": team.gmail_installation.user_email if team.gmail_installation else None,
                            "expires_at": team.gmail_installation.expires_at.isoformat() if team.gmail_installation else None,
                            "is_expired": gmail_expired
                        }
                    }
                })
            
            return {
                "teams": teams_data,
                "total": len(teams_data)
            }
            
    except Exception as e:
        logger.error(f"Error listing teams: {e}")
        raise HTTPException(status_code=500, detail="Failed to list teams")

@router.get("/{team_id}", summary="Get team details")
async def get_team(team_id: str, request: Request):
    """
    Get detailed information about a specific team (session-filtered)
    """
    try:
        # Try to get session ID from request
        session_id = SessionManager.get_session_id_from_request(request)
        
        async with AsyncSessionLocal() as session:
            if session_id:
                # Filter by session if we have one
                stmt = select(Team).options(
                    selectinload(Team.slack_installation),
                    selectinload(Team.zoho_installation),
                    selectinload(Team.gmail_installation)
                ).where(
                    Team.team_id == team_id,
                    Team.session_id == session_id
                )
            else:
                # Fallback: get team without session filter (backward compatibility)
                stmt = select(Team).options(
                    selectinload(Team.slack_installation),
                    selectinload(Team.zoho_installation),
                    selectinload(Team.gmail_installation)
                ).where(Team.team_id == team_id)
            
            result = await session.execute(stmt)
            team = result.scalar_one_or_none()
            
            if not team:
                raise HTTPException(status_code=404, detail="Team not found")
            
            # Get event logs count
            logs_stmt = select(func.count(EventLog.id)).where(EventLog.team_id == team_id)
            logs_result = await session.execute(logs_stmt)
            logs_count = logs_result.scalar()
            
            # Check Gmail token expiry
            gmail_connected = False
            gmail_expired = True
            if team.gmail_installation:
                now_utc = datetime.utcnow()
                exp = team.gmail_installation.expires_at
                if exp.tzinfo is not None:
                    exp = exp.replace(tzinfo=None)
                gmail_expired = exp <= now_utc
                gmail_connected = bool(team.gmail_installation.access_token and not gmail_expired)
            
            return {
                "team_id": team.team_id,
                "team_name": team.team_name,
                "domain": team.domain,
                "is_active": team.is_active,
                "created_at": team.created_at.isoformat(),
                "updated_at": team.updated_at.isoformat(),
                "stats": {
                    "total_events": logs_count
                },
                "integrations": {
                    "slack": {
                        "connected": bool(team.slack_installation and team.slack_installation.access_token),
                        "installed": team.slack_installation.installed if team.slack_installation else False,
                        "bot_user_id": team.slack_installation.bot_user_id if team.slack_installation else None,
                        "created_at": team.slack_installation.created_at.isoformat() if team.slack_installation else None
                    },
                    "zoho": {
                        "connected": bool(team.zoho_installation and team.zoho_installation.access_token),
                        "api_domain": team.zoho_installation.api_domain if team.zoho_installation else None,
                        "expires_at": team.zoho_installation.expires_at.isoformat() if team.zoho_installation else None,
                        "created_at": team.zoho_installation.created_at.isoformat() if team.zoho_installation else None
                    },
                    "gmail": {
                        "connected": gmail_connected,
                        "user_email": team.gmail_installation.user_email if team.gmail_installation else None,
                        "expires_at": team.gmail_installation.expires_at.isoformat() if team.gmail_installation else None,
                        "is_expired": gmail_expired,
                        "created_at": team.gmail_installation.created_at.isoformat() if team.gmail_installation else None
                    }
                }
            }
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get team details")

@router.post("/{team_id}/ensure", summary="Ensure team exists")
async def ensure_team_exists(team_id: str, team_name: str = None, domain: str = None):
    """
    Create team if it doesn't exist, or update if it does
    Used during OAuth flows to ensure team record exists
    """
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(Team).where(Team.team_id == team_id)
            result = await session.execute(stmt)
            team = result.scalar_one_or_none()
            
            if not team:
                # Create new team
                team = Team(
                    team_id=team_id,
                    team_name=team_name,
                    domain=domain,
                    is_active=True
                )
                session.add(team)
                await session.commit()
                logger.info(f"Created new team: {team_id}")
                return {"status": "created", "team_id": team_id}
            else:
                # Update existing team if new info provided
                updated = False
                if team_name and team.team_name != team_name:
                    team.team_name = team_name
                    updated = True
                if domain and team.domain != domain:
                    team.domain = domain
                    updated = True
                
                if updated:
                    await session.commit()
                    logger.info(f"Updated team: {team_id}")
                    return {"status": "updated", "team_id": team_id}
                else:
                    return {"status": "exists", "team_id": team_id}
                    
    except Exception as e:
        logger.error(f"Error ensuring team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to ensure team exists")

@router.get("/{team_id}/integrations", summary="Get team integration status")
async def get_team_integrations(team_id: str, request: Request):
    """
    Get integration status for a specific team (session-filtered)
    """
    try:
        # Try to get session ID from request
        session_id = SessionManager.get_session_id_from_request(request)
        
        async with AsyncSessionLocal() as session:
            if session_id:
                # Filter by session if we have one
                stmt = select(Team).options(
                    selectinload(Team.slack_installation),
                    selectinload(Team.zoho_installation),
                    selectinload(Team.gmail_installation)
                ).where(
                    Team.team_id == team_id,
                    Team.session_id == session_id
                )
            else:
                # Fallback: get team without session filter (backward compatibility)
                stmt = select(Team).options(
                    selectinload(Team.slack_installation),
                    selectinload(Team.zoho_installation),
                    selectinload(Team.gmail_installation)
                ).where(Team.team_id == team_id)
            
            result = await session.execute(stmt)
            team = result.scalar_one_or_none()
            
            if not team:
                # Return default status for non-existent team
                return {
                    "slack": {"connected": False, "configured": True},
                    "zoho": {"connected": False, "configured": True},
                    "gmail": {"connected": False, "configured": True}
                }
            
            # Check Gmail token expiry
            gmail_connected = False
            if team.gmail_installation:
                now_utc = datetime.utcnow()
                exp = team.gmail_installation.expires_at
                if exp.tzinfo is not None:
                    exp = exp.replace(tzinfo=None)
                gmail_expired = exp <= now_utc
                gmail_connected = bool(team.gmail_installation.access_token and not gmail_expired)
            
            return {
                "slack": {
                    "connected": bool(team.slack_installation and team.slack_installation.access_token),
                    "configured": True
                },
                "zoho": {
                    "connected": bool(team.zoho_installation and team.zoho_installation.access_token),
                    "configured": True
                },
                "gmail": {
                    "connected": gmail_connected,
                    "configured": True,
                    "user_email": team.gmail_installation.user_email if team.gmail_installation else None
                }
            }
            
    except Exception as e:
        logger.error(f"Error getting integrations for team {team_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get team integrations") 