import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime
from sqlalchemy import select, desc
from app.db.session import AsyncSessionLocal
from app.db.models import EventLog
from collections import deque
import json

logger = logging.getLogger(__name__)

class EventLogger:
    def __init__(self):
        # In-memory store for real-time updates (bounded to prevent memory leaks)
        self.live_events = deque(maxlen=1000)
        self.subscribers = set()
    
    async def log_event(
        self, 
        event_type: str, 
        event_data: Optional[Dict[str, Any]] = None,
        status: str = "processing",
        error_message: Optional[str] = None,
        team_id: Optional[str] = None
    ) -> int:
        """Log an event to both database and in-memory store"""
        try:
            async with AsyncSessionLocal() as session:
                event_log = EventLog(
                    event_type=event_type,
                    event_data=event_data,
                    status=status,
                    error_message=error_message,
                    team_id=team_id
                )
                session.add(event_log)
                await session.commit()
                await session.refresh(event_log)
                
                # Add to in-memory store for real-time updates
                event_dict = {
                    "id": event_log.id,
                    "event_type": event_log.event_type,
                    "event_data": event_log.event_data,
                    "status": event_log.status,
                    "error_message": event_log.error_message,
                    "team_id": event_log.team_id,
                    "created_at": event_log.created_at.isoformat(),
                    "updated_at": event_log.updated_at.isoformat()
                }
                
                self.live_events.appendleft(event_dict)  # Add to front for newest first
                
                # Notify all subscribers
                await self._notify_subscribers(event_dict)
                
                logger.info(f"Event logged: {event_type} - {status}")
                return event_log.id
                
        except Exception as e:
            logger.error(f"Failed to log event {event_type}: {e}")
            raise
    
    async def update_event_status(
        self, 
        event_id: int, 
        status: str, 
        error_message: Optional[str] = None,
        event_data: Optional[Dict[str, Any]] = None
    ):
        """Update an existing event's status"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(EventLog).where(EventLog.id == event_id)
                result = await session.execute(stmt)
                event_log = result.scalar_one_or_none()
                
                if event_log:
                    event_log.status = status
                    if error_message:
                        event_log.error_message = error_message
                    if event_data:
                        event_log.event_data = event_data
                    
                    await session.commit()
                    await session.refresh(event_log)
                    
                    # Update in-memory store
                    updated_event = {
                        "id": event_log.id,
                        "event_type": event_log.event_type,
                        "event_data": event_log.event_data,
                        "status": event_log.status,
                        "error_message": event_log.error_message,
                        "team_id": event_log.team_id,
                        "created_at": event_log.created_at.isoformat(),
                        "updated_at": event_log.updated_at.isoformat()
                    }
                    
                    # Update in live_events deque
                    for i, event in enumerate(self.live_events):
                        if event["id"] == event_id:
                            self.live_events[i] = updated_event
                            break
                    
                    # Notify subscribers
                    await self._notify_subscribers(updated_event)
                    
                    logger.info(f"Event {event_id} updated to status: {status}")
                    
        except Exception as e:
            logger.error(f"Failed to update event {event_id}: {e}")
            raise
    
    async def get_recent_events(self, limit: int = 50, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get recent events from database"""
        try:
            async with AsyncSessionLocal() as session:
                stmt = select(EventLog).order_by(desc(EventLog.created_at)).limit(limit)
                if team_id:
                    stmt = stmt.where(EventLog.team_id == team_id)
                
                result = await session.execute(stmt)
                events = result.scalars().all()
                
                return [
                    {
                        "id": event.id,
                        "event_type": event.event_type,
                        "event_data": event.event_data,
                        "status": event.status,
                        "error_message": event.error_message,
                        "team_id": event.team_id,
                        "created_at": event.created_at.isoformat(),
                        "updated_at": event.updated_at.isoformat()
                    }
                    for event in events
                ]
                
        except Exception as e:
            logger.error(f"Failed to get recent events: {e}")
            return []
    
    def get_live_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent events from in-memory store (faster for real-time)"""
        return list(self.live_events)[:limit]
    
    async def subscribe_to_events(self, websocket):
        """Subscribe to real-time event updates"""
        self.subscribers.add(websocket)
        try:
            # Send recent events on connection
            recent_events = self.get_live_events(20)
            if recent_events:
                await websocket.send_text(json.dumps({
                    "type": "initial_events",
                    "events": recent_events
                }))
            
            # Keep connection alive
            while True:
                await asyncio.sleep(1)
                
        except Exception as e:
            logger.error(f"WebSocket subscription error: {e}")
        finally:
            self.subscribers.discard(websocket)
    
    async def _notify_subscribers(self, event_data: Dict[str, Any]):
        """Notify all subscribers of new/updated events"""
        if not self.subscribers:
            return
            
        message = json.dumps({
            "type": "event_update",
            "event": event_data
        })
        
        # Remove disconnected subscribers
        disconnected = set()
        for subscriber in self.subscribers:
            try:
                await subscriber.send_text(message)
            except Exception:
                disconnected.add(subscriber)
        
        # Clean up disconnected subscribers
        self.subscribers -= disconnected

# Global event logger instance
event_logger = EventLogger() 