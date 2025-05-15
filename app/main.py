from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .database import connect_to_mongo, close_mongo_connection
from .routes import admin, subscription, auth, service
from .models import User
import os

app = FastAPI(title="API Management System")
#uvicorn app.main:app --reload



app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(subscription.router)
app.include_router(service.router)

@app.on_event("startup")
async def startup_db_client():
    await connect_to_mongo()

@app.on_event("shutdown")
async def shutdown_db_client():
    await close_mongo_connection()


