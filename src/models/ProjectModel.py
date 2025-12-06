from helpers.config import get_settings

settings = get_settings()

if settings.DB_BACKEND.lower() == "mongodb":
    from .db.mongo.ProjectModel import ProjectModel
elif settings.DB_BACKEND.lower() == "postgres":
    from .db.postgres.ProjectModel import ProjectModel
else:
    raise RuntimeError(f"Unsupported DB_BACKEND: {settings.DB_BACKEND}")
