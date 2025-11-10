from fastapi import APIRouter
from typing import Dict
import os
base_router = APIRouter(
    prefix="/api/v1",
    tags=["api/v1"]
)

@base_router.get("/")
async def welcome() :
    """Summary

    Returns
    -------
    Dict[str, str]
        Welcome message to server
    """
    app_name = os.getenv("APP_NAME")
    app_version = os.getenv("APP_VERSION")
    return {"app_name":app_name,
            "app_version": app_version
            }