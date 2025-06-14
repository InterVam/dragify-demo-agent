from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.api import slack
from app.api import zoho
from app.api import gmail
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
async def websocket_logs(websocket: WebSocket):
    # Log connection attempt details
    client_host = websocket.client.host if websocket.client else "unknown"
    origin = websocket.headers.get("origin", "unknown")
    logger.info(f"WebSocket connection attempt from: {client_host}, origin: {origin}")
    
    try:
        # Accept connection regardless of origin for now
        await websocket.accept()
        logger.info(f"WebSocket connection established for live logs from {client_host}")
        
        await event_logger.subscribe_to_events(websocket)
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
        
        # If no logs in database, return some sample data for demo
        if not logs:
            logs = [
                {
                    "id": 1,
                    "event_type": "lead_processed",
                    "event_data": {
                        "first_name": "Yasmine",
                        "last_name": "Ahmed",
                        "phone": "01023456789",
                        "location": "Sheikh Zayed",
                        "property_type": "duplex",
                        "bedrooms": 3,
                        "budget": 5500000,
                        "team_id": "T090NR297QD",
                        "matched_projects": ["Al Burouj Phase 3", "Swan Lake Phase 2", "Badya Phase 5"]
                    },
                    "status": "success",
                    "error_message": None,
                    "team_id": "T090NR297QD",
                    "created_at": "2025-06-14T08:03:16+00:00",
                    "updated_at": "2025-06-14T08:03:16+00:00"
                },
                {
                    "id": 2,
                    "event_type": "crm_insertion",
                    "event_data": {
                        "team_id": "T090NR297QD",
                        "crm_type": "zoho",
                        "lead_id": "6829239000000606002"
                    },
                    "status": "success",
                    "error_message": None,
                    "team_id": "T090NR297QD",
                    "created_at": "2025-06-14T08:03:15+00:00",
                    "updated_at": "2025-06-14T08:03:15+00:00"
                },
                {
                    "id": 3,
                    "event_type": "email_notification",
                    "event_data": {
                        "team_id": "T090NR297QD",
                        "recipient": "yfathi2008@gmail.com",
                        "subject": "✅ New Lead Processed Successfully - Yasmine Ahmed"
                    },
                    "status": "success",
                    "error_message": None,
                    "team_id": "T090NR297QD",
                    "created_at": "2025-06-14T08:03:17+00:00",
                    "updated_at": "2025-06-14T08:03:17+00:00"
                }
            ]
        
        return {"logs": logs}
        
    except Exception as e:
        logger.error(f"Error fetching logs: {e}")
        return {"logs": [], "error": str(e)}

# Test endpoint to create sample events
@app.post("/api/test-event")
async def create_test_event():
    """Create a test event for demonstration"""
    try:
        event_id = await event_logger.log_event(
            event_type="test_event",
            event_data={
                "message": "This is a test event",
                "timestamp": "2025-01-01T12:00:00Z"
            },
            status="success",
            team_id="T090NR297QD"
        )
        
        return {"status": "success", "event_id": event_id, "message": "Test event created"}
        
    except Exception as e:
        logger.error(f"Error creating test event: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 