from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import FastAPI, HTTPException
import os
from dotenv import load_dotenv
from .models import User, Plan, Permission, UsageStats
from datetime import datetime, timedelta
from uuid import UUID
from bson import ObjectId
import json

load_dotenv()

MONGODB_URL = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
DATABASE_NAME = os.getenv("DATABASE_NAME", "api_management")

client = AsyncIOMotorClient(MONGODB_URL)
db = client[DATABASE_NAME]

def serialize_doc(doc):
    if doc is None:
        return None
    
    if "_id" in doc:
        doc["_id"] = str(doc["_id"])
    
    # Handle datetime objects
    for key, value in doc.items():
        if isinstance(value, datetime):
            doc[key] = value.isoformat()
        elif isinstance(value, ObjectId):
            doc[key] = str(value)
    
    return doc

async def connect_to_mongo():
    pass

async def close_mongo_connection():
    if client:
        client.close()

def get_database():
    return db

# Access control function
async def check_access(user_id: str, endpoint: str):
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid user ID")
    
    if not user.get("plan_name"):
        raise HTTPException(status_code=403, detail="User has no plan")

    plan_data = await db.plans.find_one({"name": user["plan_name"], "is_active": True})
    if not plan_data:
        raise HTTPException(status_code=404, detail="Plan not found or inactive")
    plan = Plan(**plan_data)

    if user.get("subscription_end") and user["subscription_end"] < datetime.now():
        raise HTTPException(status_code=403, detail="Subscription expired")

    permission = await db.permissions.find_one({"endpoint": endpoint})
    if not permission:
        raise HTTPException(status_code=404, detail="Permission not found")

    if permission["name"] not in plan.permissions:
        raise HTTPException(status_code=403, detail="Permission denied")

    usage_record = await db.usage.find_one({"user_id": user_id, "endpoint": endpoint})
    usage = usage_record["count"] if usage_record else 0
    if usage >= plan.call_limit:
        raise HTTPException(status_code=429, detail="API call limit exceeded")

    await db.usage.update_one(
        {"user_id": user_id, "endpoint": endpoint},
        {"$inc": {"count": 1}, "$set": {"last_updated": datetime.now()}},
        upsert=True
    )

# Admin functions for permission management
async def create_permission(permission: Permission, admin_username: str):
    existing = await db.permissions.find_one({"name": permission.name})
    if existing:
        raise HTTPException(status_code=400, detail="Permission already exists")
    
    permission_dict = permission.dict()
    permission_dict["created_by"] = admin_username
    await db.permissions.insert_one(permission_dict)
    return permission

async def get_permissions():
    cursor = db.permissions.find()
    permissions = await cursor.to_list(length=None)
    return [Permission(**p) for p in permissions]

async def update_permission(name: str, permission: Permission):
    result = await db.permissions.update_one(
        {"name": name},
        {"$set": permission.dict()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Permission not found")
    return permission

async def delete_permission(name: str):
    result = await db.permissions.delete_one({"name": name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Permission not found")

# Admin functions for plan management
async def create_plan(plan: Plan, admin_username: str):
    existing = await db.plans.find_one({"name": plan.name})
    if existing:
        raise HTTPException(status_code=400, detail="Plan already exists")
    
    for perm_name in plan.permissions:
        if not await db.permissions.find_one({"name": perm_name}):
            raise HTTPException(status_code=400, detail=f"Permission {perm_name} does not exist")
    
    plan_dict = plan.dict()
    plan_dict["created_by"] = admin_username
    await db.plans.insert_one(plan_dict)
    return plan

async def get_plans():
    cursor = db.plans.find()
    plans = await cursor.to_list(length=None)
    return [Plan(**p) for p in plans]

async def update_plan(name: str, plan: Plan):
    for perm_name in plan.permissions:
        if not await db.permissions.find_one({"name": perm_name}):
            raise HTTPException(status_code=400, detail=f"Permission {perm_name} does not exist")
    
    result = await db.plans.update_one(
        {"name": name},
        {"$set": plan.dict()}
    )
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Plan not found")
    return plan

async def delete_plan(name: str):
    result = await db.plans.delete_one({"name": name})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Plan not found")

# User subscription management
async def subscribe_user(user_id: str, plan_name: str, duration_days: int = 30):
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    plan = await db.plans.find_one({"name": plan_name, "is_active": True})
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found or inactive")

    start_date = datetime.now()
    end_date = start_date + timedelta(days=duration_days)
    
    await db.users.update_one(
        {"user_id": user_id},
        {
            "$set": {
                "plan_name": plan_name,
                "subscription_start": start_date,
                "subscription_end": end_date
            }
        }
    )
    
    await db.usage.delete_many({"user_id": user_id})
    
    return {"message": "Subscription successful", "end_date": end_date}

async def get_user_subscription(user_id: str):
    user = await db.users.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not user.get("plan_name"):
        raise HTTPException(status_code=404, detail="No active subscription")
    
    plan_data = await db.plans.find_one({"name": user["plan_name"]})
    if not plan_data:
        raise HTTPException(status_code=404, detail="Plan not found")
    
    plan_data = serialize_doc(plan_data)
    
    usage_stats = await db.usage.find({"user_id": user_id}).to_list(length=None)
    total_usage = sum(stat.get("count", 0) for stat in usage_stats)
    
    return {
        "plan": plan_data,
        "usage": total_usage,
        "start_date": user.get("subscription_start"),
        "end_date": user.get("subscription_end")
    }
