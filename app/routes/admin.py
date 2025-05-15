from fastapi import APIRouter, HTTPException, Depends, Path
from uuid import uuid4
from ..models import Permission, Plan, PermissionCreate, PlanCreate, User
from ..database import (
    create_permission, get_permissions, update_permission, delete_permission,
    create_plan, get_plans, update_plan, delete_plan, db, serialize_doc
)
from ..auth import get_current_user
from typing import List
from datetime import datetime

router = APIRouter(prefix="/admin", tags=["admin"])

async def verify_admin(user: dict = Depends(get_current_user)):
    if not user.get("is_admin", False):
        raise HTTPException(status_code=403, detail="Admin access required")
    return user

# Permission Management
@router.post("/permissions", response_model=Permission)
async def create_new_permission(
    permission: PermissionCreate,
    admin: dict = Depends(verify_admin)
):
    full_permission = Permission(
        name=permission.name,
        endpoint=permission.endpoint,
        description=permission.description,
        created_at=datetime.now(),
        created_by=admin["username"]
    )
    return await create_permission(full_permission, admin["username"])

@router.get("/permissions", response_model=List[Permission])
async def list_permissions(admin: dict = Depends(verify_admin)):
    return await get_permissions()

@router.put("/permissions/{name}", response_model=Permission)
async def update_existing_permission(
    name: str,
    permission: PermissionCreate,
    admin: dict = Depends(verify_admin)
):
    existing = await db.permissions.find_one({"name": name})
    if not existing:
        raise HTTPException(status_code=404, detail="Permission not found")
    
    full_permission = Permission(
        name=permission.name,
        endpoint=permission.endpoint,
        description=permission.description,
        created_at=existing.get("created_at", datetime.now()),
        created_by=existing.get("created_by", admin["username"])
    )
    return await update_permission(name, full_permission)

@router.delete("/permissions/{name}")
async def remove_permission(name: str, admin: dict = Depends(verify_admin)):
    await delete_permission(name)
    return {"message": "Permission deleted successfully"}

# Plan Management
@router.post("/plans", response_model=Plan)
async def create_new_plan(
    plan: PlanCreate,
    admin: dict = Depends(verify_admin)
):
    full_plan = Plan(
        name=plan.name,
        description=plan.description,
        permissions=plan.permissions,
        call_limit=plan.call_limit,
        created_at=datetime.now(),
        created_by=admin["username"],
        is_active=True
    )
    return await create_plan(full_plan, admin["username"])

@router.get("/plans", response_model=List[Plan])
async def list_plans(admin: dict = Depends(verify_admin)):
    return await get_plans()

@router.put("/plans/{name}", response_model=Plan)
async def update_existing_plan(
    name: str,
    plan: PlanCreate,
    admin: dict = Depends(verify_admin)
):
    existing = await db.plans.find_one({"name": name})
    if not existing:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    full_plan = Plan(
        name=plan.name,
        description=plan.description,
        permissions=plan.permissions,
        call_limit=plan.call_limit,
        created_at=existing.get("created_at", datetime.now()),
        created_by=existing.get("created_by", admin["username"]),
        is_active=existing.get("is_active", True)
    )
    return await update_plan(name, full_plan)

@router.delete("/plans/{name}")
async def remove_plan(name: str, admin: dict = Depends(verify_admin)):
    await delete_plan(name)
    return {"message": "Plan deleted successfully"}

# User Management
@router.post("/users/")
async def create_user(admin: dict = Depends(verify_admin)):
    user_id = str(uuid4())
    user = {"user_id": user_id, "username": f"user_{user_id[:8]}", "plan_name": None, "is_admin": False}
    await db.users.insert_one(user)
    return {"user_id": user_id, "username": user["username"]}

@router.get("/users/")
async def list_users(admin: dict = Depends(verify_admin)):
    users = await db.users.find().to_list(None)
    return [serialize_doc(user) for user in users]

@router.get("/users/{username}")
async def get_user_details(
    username: str = Path(..., description="The username of the user to get details for"),
    admin: dict = Depends(verify_admin)
):
    user = await db.users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return serialize_doc(user)

@router.delete("/users/{username}")
async def delete_user(
    username: str = Path(..., description="The username of the user to delete"),
    admin: dict = Depends(verify_admin)
):
    user = await db.users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user_id = user["user_id"]
    
    result = await db.users.delete_one({"username": username})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    
    await db.usage.delete_many({"user_id": user_id})
    return {"message": "User deleted"}

@router.post("/users/{username}/assign-plan/{plan_name}")
async def assign_plan(
    username: str = Path(..., description="The username of the user to assign the plan to"),
    plan_name: str = Path(..., description="The name of the plan to assign"),
    admin: dict = Depends(verify_admin)
):
    if not await db.plans.find_one({"name": plan_name}):
        raise HTTPException(status_code=404, detail="Plan not found")
    
    user = await db.users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    result = await db.users.update_one(
        {"username": username},
        {"$set": {"plan_name": plan_name}}
    )
    
    await db.usage.delete_many({"user_id": user["user_id"]})
    return {"message": "Plan assigned"}

@router.get("/users/{username}/usage", summary="Get usage statistics for a user")
async def get_user_usage(
    username: str = Path(..., description="The username of the user to get usage for"),
    admin: dict = Depends(verify_admin)
):
    user = await db.users.find_one({"username": username})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    usage_stats = await db.usage.find({"user_id": user["user_id"]}).to_list(length=None)
    
    detailed_stats = []
    total_usage = 0
    
    for stat in usage_stats:
        endpoint = stat.get("endpoint", "unknown")
        permission = await db.permissions.find_one({"endpoint": endpoint})
        
        detailed_stat = {
            "endpoint": endpoint,
            "permission_name": permission["name"] if permission else "unknown",
            "count": stat.get("count", 0),
            "last_access": stat.get("last_updated", None)
        }
        detailed_stats.append(detailed_stat)
        total_usage += stat.get("count", 0)
    
    plan = None
    if user.get("plan_name"):
        plan_data = await db.plans.find_one({"name": user["plan_name"]})
        if plan_data:
            plan = {
                "name": plan_data["name"],
                "call_limit": plan_data["call_limit"],
                "usage_percentage": (total_usage / plan_data["call_limit"]) * 100 if plan_data["call_limit"] > 0 else 0
            }
    
    return {
        "username": username,
        "user_id": user["user_id"],
        "plan": plan,
        "total_usage": total_usage,
        "usage_by_endpoint": detailed_stats
    } 