from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from uuid import UUID, uuid4

class UserCreate(BaseModel):
    username: str
    password: str

class User(BaseModel):
    user_id: UUID = Field(default_factory=uuid4)
    username: str
    is_admin: bool = False
    plan_name: Optional[str] = None
    subscription_start: Optional[datetime] = None
    subscription_end: Optional[datetime] = None

class Permission(BaseModel):
    name: str
    endpoint: str
    description: str
    created_at: datetime = datetime.now()
    created_by: str  

class Plan(BaseModel):
    name: str
    description: str
    permissions: List[str]  
    call_limit: int
    created_at: datetime = datetime.now()
    created_by: str  
    is_active: bool = True

class SubscriptionDetails(BaseModel):
    plan: Plan
    usage: int
    start_date: datetime
    end_date: datetime

class UsageStats(BaseModel):
    user_id: UUID
    endpoint: str
    count: int
    last_updated: datetime = datetime.now()

class PlanCreate(BaseModel):
    name: str
    description: str
    permissions: List[str]
    call_limit: int

class PermissionCreate(BaseModel):
    name: str
    endpoint: str
    description: str 