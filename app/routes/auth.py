from fastapi import APIRouter, HTTPException, status, Depends
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from uuid import uuid4
from ..auth import (
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    verify_password,
    get_password_hash
)
from ..models import UserCreate, User
from ..database import db

router = APIRouter(tags=["authentication"])

@router.post("/register", response_model=User)
async def register(user_data: UserCreate):
    if await db.users.find_one({"username": user_data.username}):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    user_id = str(uuid4())
    hashed_password = get_password_hash(user_data.password)
    user = {
        "user_id": user_id,
        "username": user_data.username,
        "password": hashed_password,
        "is_admin": False,
        "plan_name": None
    }
    
    await db.users.insert_one(user)
    return User(**user)

@router.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = await db.users.find_one({"username": form_data.username})
    if user and verify_password(form_data.password, user["password"]):
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": str(user["user_id"])}, 
            expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer"}
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        ) 