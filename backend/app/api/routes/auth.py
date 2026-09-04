from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_access_token, hash_password, verify_password
from app.models.models import User
from app.schemas.schemas import LoginRequest, RegisterRequest, TokenOut, UserOut, MessageOut
from app.services.audit import log_action

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=201)
def register(body: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == body.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(
        email=body.email.lower(),
        name=body.name,
        password_hash=hash_password(body.password),
        role="operator",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    log_action(db, user.id, None, "user.registered", user.email)
    token = create_access_token(user.id, user.role)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email.lower()).first()
    if not user or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Incorrect email or password.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="This account is disabled.")
    log_action(db, user.id, None, "user.login", user.email)
    token = create_access_token(user.id, user.role)
    return TokenOut(access_token=token, user=UserOut.model_validate(user))


@router.post("/logout", response_model=MessageOut)
def logout():
    # Stateless JWT: client discards the token.
    return MessageOut(message="Signed out.")
