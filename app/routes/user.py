from fastapi import APIRouter, Header, HTTPException, Depends
from ..models import SubscriptionDetails, Plan
from ..database import get_user, db
from ..auth import get_current_user

router = APIRouter(tags=["user"])

@router.get("/subscription/", response_model=SubscriptionDetails)
async def view_subscription(current_user: dict = Depends(get_current_user)):
    if not current_user.get("plan_name"):
        raise HTTPException(status_code=404, detail="No subscription")
    plan_data = await db.plans.find_one({"name": current_user["plan_name"]})
    usage_data = await db.usage.find_one({"api_key": current_user["api_key"]}) or {"count": 0}
    return SubscriptionDetails(plan=Plan(**plan_data), usage=usage_data["count"]) 