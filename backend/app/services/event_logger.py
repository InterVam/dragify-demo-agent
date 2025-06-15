"""
Event Logger Service

Provides comprehensive event logging and real-time streaming capabilities for the Dragify AI Agent.

Key Features:
- Database persistence of all events with status tracking
- In-memory event store for fast real-time updates (bounded to 1000 events)
- WebSocket subscriptions for live dashboard updates
- Automatic timeout handling for stuck "processing" events (5-minute default)
- Background monitoring task that runs every minute
- Session-based event filtering for multi-user support

Event Lifecycle:
1. Events start with "processing" status
2. Updated to "success" or "error" based on workflow outcome
3. Automatically marked as "error" if processing exceeds timeout
4. Real-time notifications sent to all WebSocket subscribers
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from sqlalchemy import select, desc, and_
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
        self.timeout_task = None
        self.timeout_minutes = 5  # Timeout after 5 minutes
    
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

    async def start_timeout_monitor(self, timeout_minutes: int = None):
        """Start the background task to monitor for timed-out events"""
        if timeout_minutes is not None:
            self.timeout_minutes = timeout_minutes
            
        if self.timeout_task is None:
            self.timeout_task = asyncio.create_task(self._timeout_monitor_loop())
            logger.info(f"Event timeout monitor started (timeout: {self.timeout_minutes} minutes)")

    async def stop_timeout_monitor(self):
        """Stop the background timeout monitor"""
        if self.timeout_task:
            self.timeout_task.cancel()
            try:
                await self.timeout_task
            except asyncio.CancelledError:
                pass
            self.timeout_task = None
            logger.info("Event timeout monitor stopped")

    def get_timeout_config(self) -> dict:
        """Get current timeout configuration"""
        return {
            "timeout_minutes": self.timeout_minutes,
            "monitor_running": self.timeout_task is not None and not self.timeout_task.done()
        }

    async def _timeout_monitor_loop(self):
        """Background loop to check for timed-out events"""
        while True:
            try:
                await self._check_and_timeout_events()
                # Check every minute for timed-out events
                await asyncio.sleep(60)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in timeout monitor: {e}")
                await asyncio.sleep(60)  # Continue checking even if there's an error

    async def _check_and_timeout_events(self):
        """Check for events that have been processing too long and mark them as errored"""
        try:
            cutoff_time = datetime.utcnow() - timedelta(minutes=self.timeout_minutes)
            
            async with AsyncSessionLocal() as session:
                # Find events that are still "processing" and older than timeout
                stmt = select(EventLog).where(
                    and_(
                        EventLog.status == "processing",
                        EventLog.created_at < cutoff_time
                    )
                )
                
                result = await session.execute(stmt)
                timed_out_events = result.scalars().all()
                
                if timed_out_events:
                    logger.info(f"Found {len(timed_out_events)} timed-out events")
                    
                    for event in timed_out_events:
                        # Update status to error
                        event.status = "error"
                        event.error_message = f"Event timed out after {self.timeout_minutes} minutes"
                        
                        # Update in-memory store and notify subscribers
                        updated_event = {
                            "id": event.id,
                            "event_type": event.event_type,
                            "event_data": event.event_data,
                            "status": event.status,
                            "error_message": event.error_message,
                            "team_id": event.team_id,
                            "created_at": event.created_at.isoformat(),
                            "updated_at": event.updated_at.isoformat()
                        }
                        
                        # Update in live_events deque
                        for i, live_event in enumerate(self.live_events):
                            if live_event["id"] == event.id:
                                self.live_events[i] = updated_event
                                break
                        
                        # Notify subscribers
                        await self._notify_subscribers(updated_event)
                        
                        logger.warning(f"Event {event.id} ({event.event_type}) timed out after {self.timeout_minutes} minutes")
                    
                    await session.commit()
                    
        except Exception as e:
            logger.error(f"Error checking for timed-out events: {e}")

# Global event logger instance
event_logger = EventLogger() 