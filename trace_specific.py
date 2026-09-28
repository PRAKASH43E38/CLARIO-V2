import asyncio
from sqlalchemy import text
from backend.app.api.routes.orchestration import get_orchestration_state, initialize_orchestration
from backend.app.core.database import SessionLocal
from fastapi import HTTPException

async def trace():
    session_id = "ses_de8ca6db80d8"
    user_id = "usr_d6377d9fffaf"
    
    db = SessionLocal()
    try:
        print(f"--- Testing GET /api/v1/sessions/{session_id}/orchestration ---")
        try:
            result = await get_orchestration_state(session_id=session_id, user_id=user_id, db=db)
            print("GET Result:", result)
        except HTTPException as e:
            print(f"GET caught HTTPException: {e.status_code} - {e.detail}")
        except Exception as e:
            import traceback
            traceback.print_exc()

        print(f"\n--- Testing POST /api/v1/sessions/{session_id}/orchestration ---")
        try:
            result = await initialize_orchestration(session_id=session_id, user_id=user_id, db=db)
            print("POST Result:", result)
        except HTTPException as e:
            print(f"POST caught HTTPException: {e.status_code} - {e.detail}")
        except Exception as e:
            import traceback
            traceback.print_exc()
            
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(trace())
