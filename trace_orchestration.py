import asyncio
from sqlalchemy import text
from backend.app.api.routes.orchestration import initialize_orchestration
from backend.app.core.database import SessionLocal
from fastapi import HTTPException

async def trace():
    db = SessionLocal()
    try:
        res = db.execute(text("SELECT id, user_id FROM learning_sessions LIMIT 1")).fetchone()
        if not res:
            print("No sessions found in database")
            return
        
        session_id, user_id = res
        print(f"Tracing POST /api/v1/sessions/{session_id}/orchestration?user_id={user_id}")
        result = await initialize_orchestration(session_id=session_id, user_id=user_id, db=db)
        print("Result:", result)
    except Exception as e:
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(trace())
