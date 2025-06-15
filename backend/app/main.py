"""
Dragify AI Agent - Main FastAPI Application

This is the main entry point for the Dragify AI Agent backend service.
It provides:
- RESTful API endpoints for team and integration management
- WebSocket connections for real-time event streaming
- OAuth integration flows for Slack, Zoho CRM, and Gmail
- Session-based authentication for multi-user support
- Event logging with automatic timeout handling (5-minute timeout)
- Database migrations and health checks

The application orchestrates AI-powered lead processing workflows
triggered by Slack messages and integrated with CRM and email systems.
"""

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import slack
from app.api import zoho
from app.api import gmail
from app.api import teams
from app.db.session import engine
from app.db.models import Base
from app.config.slack_config import SlackConfig
from app.config.zoho_config import ZohoConfig
from app.config.gmail_config import GmailConfig
from app.services.event_logger import event_logger
import logging
import traceback
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI()

# Error handling middleware
@app.middleware("http")
async def error_handling_middleware(request: Request, call_next):
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={
                "error": "Internal Server Error",
                "detail": str(e),
                "type": type(e).__name__
            }
        )

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(teams.router)
app.include_router(slack.router)
app.include_router(zoho.router)
app.include_router(gmail.router)

@app.on_event("startup")
async def on_startup():
    # Run database migrations first
    await run_migrations()
    
    # Then create any new tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Start the event timeout monitor
    from app.services.event_logger import event_logger
    await event_logger.start_timeout_monitor()

@app.on_event("shutdown")
async def on_shutdown():
    # Stop the event timeout monitor
    from app.services.event_logger import event_logger
    await event_logger.stop_timeout_monitor()

async def run_migrations():
    """Run database migrations"""
    try:
        async with engine.begin() as conn:
            # Check if projects table exists, if not create it
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'projects'
                );
            """))
            
            table_exists = result.scalar()
            
            if not table_exists:
                logger.info("Creating projects table...")
                await conn.execute(text("""
                    CREATE TABLE projects (
                        id SERIAL PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        location VARCHAR(255),
                        property_type VARCHAR(100),
                        bedrooms INTEGER,
                        min_budget BIGINT,
                        max_budget BIGINT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                    );
                """))
                logger.info("Projects table created successfully")
            
            # Check if event_logs table exists
            result = await conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'event_logs'
                );
            """))
            
            event_logs_exists = result.scalar()
            if not event_logs_exists:
                logger.info("Event logs table will be created by SQLAlchemy")
                
    except Exception as e:
        logger.error(f"Migration error: {e}")
        raise

# WebSocket endpoint for real-time logs
@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket, session_id: str = None, team_id: str = None):
    # Log connection attempt details
    client_host = websocket.client.host if websocket.client else "unknown"
    origin = websocket.headers.get("origin", "unknown")
    logger.info(f"WebSocket connection attempt from: {client_host}, origin: {origin}, session: {session_id}, team: {team_id}")
    
    try:
        # Accept connection regardless of origin for now
        await websocket.accept()
        logger.info(f"WebSocket connection established for live logs from {client_host}")
        
        await event_logger.subscribe_to_events(websocket, session_id=session_id, team_id=team_id)
    except WebSocketDisconnect:
        logger.info(f"WebSocket connection closed from {client_host}")
    except Exception as e:
        logger.error(f"WebSocket error from {client_host}: {e}")
        try:
            await websocket.close()
        except:
            pass

# Health check endpoint
@app.get("/health")
async def health_check():
    health_status = {
        "status": "healthy",
        "database": "unknown",
        "services": {
            "slack": "configured" if SlackConfig.CLIENT_ID else "not_configured",
            "zoho": "configured" if ZohoConfig().CLIENT_ID else "not_configured",
            "gmail": "configured" if GmailConfig.CLIENT_ID else "not_configured"
        }
    }
    
    try:
        # Test database connection
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        health_status["database"] = "connected"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["database"] = "disconnected"
        health_status["status"] = "unhealthy"
    
    return health_status

# API logs endpoint for frontend
@app.get("/api/logs")
async def get_logs(limit: int = 50, team_id: str = None):
    """Get recent activity logs for the dashboard"""
    try:
        # Get logs from the event logger
        logs = await event_logger.get_recent_events(limit=limit, team_id=team_id)
        
        # Return empty logs if none exist
        if not logs:
            logs = []
        
        return {"logs": logs}
        
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return {"logs": [], "error": str(e)}

# Manual timeout check endpoint (for testing/admin purposes)
@app.post("/api/logs/check-timeouts")
async def check_timeouts():
    """Manually check for and timeout processing events"""
    try:
        await event_logger._check_and_timeout_events()
        return {"message": "Timeout check completed successfully"}
    except Exception as e:
        logger.error(f"Error checking timeouts: {e}")
        return {"error": str(e)}

# Get timeout configuration
@app.get("/api/logs/timeout-config")
async def get_timeout_config():
    """Get current timeout configuration"""
    try:
        config = event_logger.get_timeout_config()
        return config
    except Exception as e:
        logger.error(f"Error getting timeout config: {e}")
        return {"error": str(e)}

# Test endpoint to create sample events
@app.post("/api/test-event")
async def create_test_event(team_id: str):
    """Create a test event for demonstration"""
    if not team_id:
        return {"status": "error", "error": "team_id is required"}
        
    try:
        event_id = await event_logger.log_event(
            event_type="test_event",
            event_data={
                "message": "This is a test event",
                "timestamp": "2025-01-01T12:00:00Z",
                "team_id": team_id
            },
            status="success",
            team_id=team_id
        )
        
        return {"status": "success", "event_id": event_id, "message": "Test event created"}
        
    except Exception as e:
        logger.error(f"Error creating test event: {e}")
        return {"status": "error", "error": str(e)}

# Test endpoint to create a processing event (for timeout testing)
@app.post("/api/test-processing-event")
async def create_test_processing_event(team_id: str):
    """Create a test processing event to test timeout functionality"""
    if not team_id:
        return {"status": "error", "error": "team_id is required"}
        
    try:
        event_id = await event_logger.log_event(
            event_type="test_processing_event",
            event_data={
                "message": "This is a test processing event that will timeout",
                "timestamp": datetime.utcnow().isoformat(),
                "team_id": team_id
            },
            status="processing",  # This will remain processing until timeout
            team_id=team_id
        )
        
        return {"status": "success", "event_id": event_id, "message": "Test processing event created (will timeout in 5 minutes)"}
        
    except Exception as e:
        logger.error(f"Error creating test processing event: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 