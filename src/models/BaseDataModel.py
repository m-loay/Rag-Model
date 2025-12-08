from helpers.config import get_settings

settings = get_settings()

if settings.DB_BACKEND.lower() == "mongodb":
    from .db.mongo.BaseDataModel import BaseDataModel
elif settings.DB_BACKEND.lower() == "postgres":
    from .db.postgres.BaseDataModel import BaseDataModel
else:
    raise RuntimeError(f"Unsupported DB_BACKEND: {settings.DB_BACKEND}")
