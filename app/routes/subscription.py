from fastapi import APIRouter, Depends, HTTPException
from ..models import SubscriptionDetails, User
from ..database import subscribe_user, get_user_subscription, serialize_doc, db
from ..auth import get_current_user
from typing import Optional

router = APIRouter(prefix="/subscription", tags=["subscription"])

@router.post("/subscribe/{plan_name}")
async def subscribe_to_plan(
    plan_name: str,
    duration_days: Optional[int] = 30,
    user: dict = Depends(get_current_user)
):
    result = await subscribe_user(user["user_id"], plan_name, duration_days)
    return result

@router.get("/details")
async def get_subscription_details(user: dict = Depends(get_current_user)):
    subscription = await get_user_subscription(user["user_id"])
    if isinstance(subscription["plan"], dict):
        subscription["plan"] = serialize_doc(subscription["plan"])
    
    usage_stats = await db.usage.find({"user_id": user["user_id"]}).to_list(length=None)
    
    total_usage = 0
    usage_by_endpoint = []
    
    for stat in usage_stats:
        endpoint = stat.get("endpoint", "unknown")
        count = stat.get("count", 0)
        
        permission = await db.permissions.find_one({"endpoint": endpoint})
        permission_name = permission["name"] if permission else "unknown"
        
        usage_by_endpoint.append({
            "endpoint": endpoint,
            "permission_name": permission_name,
            "count": count,
            "last_access": stat.get("last_updated")
        })
        total_usage += count
    
    subscription["usage"] = {
        "total": total_usage,
        "by_endpoint": usage_by_endpoint,
        "percentage": (total_usage / subscription["plan"]["call_limit"]) * 100 if subscription["plan"]["call_limit"] > 0 else 0
    }
    
    return subscription

@router.get("/usage", summary="View your API usage statistics")
async def get_my_usage(user: dict = Depends(get_current_user)):
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
        detailed_stats.append(serialize_doc(detailed_stat))
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
        "username": user["username"],
        "plan": plan,
        "total_usage": total_usage,
        "usage_by_endpoint": detailed_stats
    } 