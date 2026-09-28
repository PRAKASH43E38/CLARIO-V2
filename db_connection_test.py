import asyncio
from sqlalchemy import create_engine, text
from backend.app.core.config import settings
from backend.app.core.database import SessionLocal

def test_connection():
    # Mask credentials for security
    url_parts = settings.DATABASE_URL.split('@')
    host = url_parts[-1] if len(url_parts) > 1 else "unknown"
    print(f"Testing connection to: {host}")
    
    try:
        # 1. Test basic engine connectivity
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            print("Basic Connectivity: SUCCESS")

        # 2. Test SessionLocal (the one used by FastAPI)
        db = SessionLocal()
        try:
            # Check for a core table (users)
            user_count = db.execute(text("SELECT count(*) FROM users")).scalar()
            print(f"Database Access: SUCCESS (Users found: {user_count})")
            
            # Check for orchestration table
            orch_count = db.execute(text("SELECT count(*) FROM clario_orchestrations")).scalar()
            print(f"Orchestration Table: SUCCESS (Records found: {orch_count})")
            
        finally:
            db.close()
            
    except Exception as e:
        print(f"Connection Failed: {str(e)}")
        return False
    return True

if __name__ == "__main__":
    if test_connection():
        print("\nDATABASE CONNECTION STATUS: HEALTHY")
    else:
        print("\nDATABASE CONNECTION STATUS: CRITICAL FAILURE")
