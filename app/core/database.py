from motor.motor_asyncio import AsyncIOMotorClient
from typing import Optional
import asyncio
from app.core.config import settings
import logging
import os

logger = logging.getLogger(__name__)

class DatabaseManager:
    _instance: Optional['DatabaseManager'] = None
    _client: Optional[AsyncIOMotorClient] = None
    _db = None
    _max_retries = 5
    _retry_delay = 2  # seconds

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        if self._client is None:
            self._initialize_connection()

    def _initialize_connection(self):
        """Initialize the MongoDB connection."""
        try:
            # Configure the client
            self._client = AsyncIOMotorClient(
                settings.MONGODB_URL,
                maxPoolSize=50,
                minPoolSize=10,
                maxIdleTimeMS=30000,
                waitQueueTimeoutMS=10000,
                retryWrites=True,
                retryReads=True
            )
            
            self._db = self._client.get_database(settings.MONGODB_DB_NAME)
            
            logger.info("MongoDB connection initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MongoDB connection: {str(e)}")
            raise

    async def ensure_connection(self):
        """Ensure the MongoDB connection is established with retries."""
        for i in range(self._max_retries):
            try:
                if self._client is None or self._db is None:
                    logger.info(f"Attempting to connect to MongoDB (attempt {i + 1}/{self._max_retries})")
                    # Call the synchronous initialization method
                    self._initialize_connection()
                # Ping to verify the connection is truly active
                await self.ping()
                logger.info("MongoDB connection successfully established.")
                return
            except Exception as e:
                logger.warning(f"MongoDB connection failed on attempt {i + 1}: {e}")
                if i < self._max_retries - 1:
                    await asyncio.sleep(self._retry_delay)
                else:
                    logger.error("All MongoDB connection attempts failed.")
                    raise

    @property
    def db(self):
        """Get the database instance."""
        if self._db is None:
            self._initialize_connection()
        return self._db

    @property
    def client(self):
        """Get the MongoDB client instance."""
        if self._client is None:
            self._initialize_connection()
        return self._client

    async def close(self):
        """Close the MongoDB connection."""
        if self._client is not None:
            self._client.close()
            self._client = None
            self._db = None
            logger.info("MongoDB connection closed")

    async def ping(self):
        """Check if the database connection is alive."""
        try:
            await self.db.command('ping')
            return True
        except Exception as e:
            logger.error(f"Database ping failed: {str(e)}")
            return False

# Create a singleton instance
db_manager = DatabaseManager()

# Dependency for FastAPI
async def get_database():
    """Get the database instance for dependency injection."""
    return db_manager.db

async def connect_to_mongo():
    """Initialize MongoDB connection."""
    await db_manager.ensure_connection()

async def close_mongo_connection():
    """Close MongoDB connection."""
    await db_manager.close() 