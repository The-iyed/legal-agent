from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.routes.conversation import router as conversation_router
from app.routes.agent import router as agent_router
from app.routes.message import router as message_router
from app.routes.admin import router as admin_router
from app.routes.document_intelligence import router as document_intelligence_router
from app.routes.claim_extractor import router as claim_extractor_router
from app.core.database import connect_to_mongo, close_mongo_connection, db_manager
from app.core.scheduler import task_scheduler
from contextlib import asynccontextmanager
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle app startup and shutdown."""
    # Startup
    logger.info("🚀 Starting FastAPI application")
    
    # Initialize database
    await connect_to_mongo()
    logger.info("Successfully connected to MongoDB")
    
    # Initialize and start the task scheduler
    db = db_manager.db
    await task_scheduler.initialize(db)
    task_scheduler.start()
    
    logger.info("✅ Application startup completed")
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down FastAPI application")
    
    # Shutdown scheduler
    task_scheduler.shutdown()
    
    # Close database connections
    await close_mongo_connection()
    logger.info("Successfully closed MongoDB connection")
    
    logger.info("✅ Application shutdown completed")

app = FastAPI(
    title="Maarefa Agent V2 API",
    description="""

    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    openapi_tags=[
        {
            "name": "agents",
            "description": "Agent operations for processing queries and managing agent interactions.",
        },
        {
            "name": "conversations",
            "description": "Conversation management operations including creating, retrieving, and managing conversations.",
        },
        {
            "name": "messages",
            "description": "Message management operations including creating and retrieving messages.",
        },
        {
            "name": "Document Intelligence",
            "description": "Enhanced document analysis using Azure Document Intelligence with multiple models and specialized legal document processing.",
        },
        {
            "name": "Claim Extractor",
            "description": "Specialized claim extraction and processing from legal documents with AI-powered refinement and validation.",
        }
    ],
    lifespan=lifespan
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
app.include_router(conversation_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
app.include_router(message_router, prefix="/api")
app.include_router(admin_router, prefix="/api")
app.include_router(document_intelligence_router)
app.include_router(claim_extractor_router)

@app.get("/", tags=["root"])
async def root():
    """
    Root endpoint that provides basic API information.
    
    Returns:
        dict: Basic API information including version and documentation URL.
    """
    jobs = task_scheduler.get_jobs()
    return {
        "message": "Welcome to the Maarefa Agent V2 API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "scheduler_status": "active" if task_scheduler.scheduler.running else "stopped",
        "scheduled_jobs": [
            {
                "id": job.id,
                "name": job.name,
                "next_run": job.next_run_time.isoformat() if job.next_run_time else None
            }
            for job in jobs
        ]
    }

@app.get("/health", tags=["health"])
async def health_check():
    """
    Health check endpoint to verify database connection.
    
    Returns:
        dict: Health status information
    """
    db_status = "disconnected"

    try:
        await db_manager.ping()
        db_status = "connected"
    except Exception as e:
        logger.error(f"Health check: MongoDB ping failed - {str(e)}")

    if db_status == "connected":
        return {
            "status": "healthy",
            "database": db_status,
            "timestamp": str(datetime.utcnow()),
            "scheduler_running": task_scheduler.scheduler.running
        }
    else:
        raise HTTPException(
            status_code=503,
            detail=f"Service unhealthy: Database {db_status}"
        ) 