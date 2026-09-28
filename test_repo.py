from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from backend.app.core.database import SessionLocal
from backend.app.models.repositories import UserRepository

db = SessionLocal()
user_id = 'usr_cd2dc4fdd525'
user = UserRepository.get_by_id(db, user_id)
print(f"User found: {user}")
db.close()
