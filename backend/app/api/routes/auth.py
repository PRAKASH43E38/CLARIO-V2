from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.api.schemas import AuthRequest, AuthResponse, UserProfileResponse
from backend.app.core.database import get_db
from backend.app.models.repositories import UserRepository, MindProfileRepository
from backend.app.services.auth_service import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _auth_response(db: Session, user, token: str = None) -> AuthResponse:
    return AuthResponse(
        user_id=user.id,
        email=user.email,
        authentication_provider=user.authentication_provider,
        profile_complete=user.name is not None,
        mind_profile_complete=MindProfileRepository.get_by_user_id(db, user.id) is not None,
        access_token=token,
    )


@router.get("/status", response_model=AuthResponse)
async def auth_status(user_id: str, db: Session = Depends(get_db)):
    user = UserRepository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return _auth_response(db, user)


@router.post("/register", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def register(request: AuthRequest, db: Session = Depends(get_db)):
    email = request.email.strip().lower()
    if "@" not in email or email.startswith("@") or email.endswith("@"):
        raise HTTPException(status_code=422, detail="Enter a valid email address.")
    if UserRepository.get_by_email(db, email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    try:
        user = UserRepository.create(
            db, email=email, password_hash=hash_password(request.password)
        )
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409, detail="An account with this email already exists."
        ) from exc

    token = create_access_token(data={"sub": user.id})
    return _auth_response(db, user, token=token)


@router.post("/login", response_model=AuthResponse)
async def login(request: AuthRequest, db: Session = Depends(get_db)):
    email = request.email.strip().lower()
    user = UserRepository.get_by_email(db, email)
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email or password is incorrect.",
        )

    token = create_access_token(data={"sub": user.id})
    return _auth_response(db, user, token=token)
