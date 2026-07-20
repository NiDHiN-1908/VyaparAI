# backend/database/connection.py
import logging
from supabase import create_client, Client
from backend.config import settings

logger = logging.getLogger("vyaparai.database")

# Setup logging
logging.basicConfig(level=logging.INFO)

class SupabaseConnection:
    def __init__(self):
        self.client: Client = None
        self.is_mock = True
        
        # Check if settings contain actual user inputs and not defaults
        has_real_url = "your-supabase-project" not in settings.SUPABASE_URL
        has_real_key = "your-supabase" not in settings.SUPABASE_KEY
        
        if has_real_url and has_real_key:
            try:
                self.client = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
                # Test query to check if credentials are valid
                self.client.table("youtube_channels").select("channel_id").limit(1).execute()
                self.is_mock = False
                logger.info("Successfully connected to Supabase Database!")
            except Exception as e:
                logger.error(f"Failed to connect or authenticate to Supabase: {e}. Falling back to mock db.")
                self.is_mock = True
                self.client = None
        else:
            logger.warning(
                "Supabase URL or Key not set. Running in Mock/In-Memory database mode. "
                "Set SUPABASE_URL and SUPABASE_KEY in .env to connect to a real database."
            )


# Global database connection instance and duration measurement
import time
_db_conn_start = time.time()
db_conn = SupabaseConnection()
db_conn_duration = time.time() - _db_conn_start

def get_supabase_client() -> Client:
    """Dependency injection helper to get the database client."""
    return db_conn.client
