from fastapi import APIRouter, Depends
from helpers.config import get_settings, Settings
from typing import Dict

base_router = APIRouter(prefix="/api/v1", tags=["api/v1", "data"])


@base_router.get("/")
async def welcome(app_settings: Settings = Depends(get_settings)) -> Dict[str, str]:
    """Summary

    Returns
    -------
    Dict[str, str]
        Welcome message to server
    """
    app_name = app_settings.APP_NAME
    app_version = app_settings.APP_VERSION
    return {"app_name": app_name, "app_version": app_version}
