from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from ..db import database
from ..schemas import schemas
from ..services import auth_service
from ..models import User
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError



get_db = database.get_db
userCreate = schemas.userCreate

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post('/register')
def register(user: userCreate, db : Session = Depends(get_db)):
    user_exists = auth_service.get_user(user.email,db)
    if user_exists:
        raise HTTPException(status_code=400, detail="User already exists")
    
    new_user = User(email = user.email, password_hash = auth_service.hash_password(user.password))
    try:
        db.add(new_user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Email already exists")
    db.refresh(new_user)
    return {
    "id": new_user.id,
    "email": new_user.email
    }


@router.post("/login")
def login(user: userCreate, db : Session = Depends(get_db)):
    user_exists = auth_service.get_user(user.email,db)
    if not user_exists or not auth_service.verify_password(user.password, user_exists.password_hash):
        raise HTTPException(status_code=400, detail="Invalid credentials")
    token = auth_service.create_token({"sub": str(user_exists.id)})
    return {
    "access_token": token,
    "token_type": "bearer"
    }


@router.get("/me")
def get_me(current_user: User = Depends(auth_service.get_current_user)):
    return current_user


