from helpers.config import get_settings

settings = get_settings()

if settings.DB_BACKEND.lower() == "mongodb":
    from .mongo.AssetModel import AssetModel
    from .mongo.ChunkModel import ChunkModel
    from .mongo.ProjectModel import ProjectModel
    from .mongo.BaseDataModel import BaseDataModel
    from .mongo.db_schema.Asset import Asset
    from .mongo.db_schema.DataChunk import DataChunk
    from .mongo.db_schema.Project import Project
    from .mongo.db_schema.RetrivedfDocument import RetrivedfDocument
elif settings.DB_BACKEND.lower() == "postgres":
    from .postgres.AssetModel import AssetModel
    from .postgres.ChunkModel import ChunkModel
    from .postgres.ProjectModel import ProjectModel
    from .postgres.BaseDataModel import BaseDataModel
    from .postgres.db_schema.Asset import Asset
    from .postgres.db_schema.DataChunk import DataChunk
    from .postgres.db_schema.Project import Project
    from .postgres.db_schema.RetrivedfDocument import RetrivedfDocument
else:
    raise RuntimeError(f"Unsupported DB_BACKEND: {settings.DB_BACKEND}")

__all__ = [
    "AssetModel",
    "ChunkModel",
    "ProjectModel",
    "BaseDataModel",
    "Asset",
    "DataChunk",
    "Project",
    "RetrivedfDocument",
]
