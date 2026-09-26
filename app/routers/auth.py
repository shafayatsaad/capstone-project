from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Owner
from app.schemas import LoginRequest, OwnerCreate
from app.security import hash_password, issue_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201)
def register(payload: OwnerCreate, db: Session = Depends(get_db)):
    owner = Owner(email=payload.email, password_hash=hash_password(payload.password))
    db.add(owner)
    try:
        db.commit()
        db.refresh(owner)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="an account with this email already exists")
    return {"access_token": issue_token(owner.id), "token_type": "bearer", "owner_id": owner.id}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    owner = db.query(Owner).filter(Owner.email == payload.email).first()
    if owner is None or not verify_password(payload.password, owner.password_hash):
        raise HTTPException(status_code=401, detail="email or password is incorrect", headers={"WWW-Authenticate": "Bearer"})
    return {"access_token": issue_token(owner.id), "token_type": "bearer", "owner_id": owner.id}
