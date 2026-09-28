from sqlalchemy import create_engine, text
from backend.app.core.config import settings

def apply_fix():
    engine = create_engine(settings.DATABASE_URL)
    with engine.connect() as conn:
        print("Applying column fixes to Neon DB...")
        try:
            conn.execute(text("ALTER TABLE thinking_results ADD COLUMN learner_response TEXT"))
            print("Added learner_response to thinking_results")
        except Exception as e:
            print(f"Thinking results fix: {e}")
        
        try:
            conn.execute(text("ALTER TABLE practical_results ADD COLUMN learner_response TEXT"))
            print("Added learner_response to practical_results")
        except Exception as e:
            print(f"Practical results fix: {e}")
        
        conn.commit()
        print("Fixes applied successfully.")

if __name__ == "__main__":
    apply_fix()
