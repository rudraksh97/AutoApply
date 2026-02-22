from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from src.db import get_db
from src.models import User
from api.schemas.auth import UserResponse
from api.schemas.admin import UserRoleUpdate
from api.dependencies import get_current_admin_user

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_admin_user)],
    responses={404: {"description": "Not found"}},
)

@router.get("/users", response_model=List[UserResponse])
def get_all_users(db: Session = Depends(get_db)):
    users = db.query(User).all()
    return users

@router.put("/users/{user_id}/roles", response_model=UserResponse)
def update_user_roles(user_id: str, role_update: UserRoleUpdate, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Validate roles maybe? 
    # For now assume any string is valid or check against ['admin', 'basic', 'customer']
    valid_roles = {"admin", "basic", "customer"}
    if not set(role_update.roles).issubset(valid_roles):
         raise HTTPException(status_code=400, detail=f"Invalid roles. Allowed: {valid_roles}")

    # Directly setting list to array column
    # SQLAlchemy requires flagging modified for JSON/Array usually if mutating in place
    # but here we are replacing.
    user.roles = role_update.roles
    db.commit()
    db.refresh(user)
    return user
