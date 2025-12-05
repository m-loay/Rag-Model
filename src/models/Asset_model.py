from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import List, Tuple, Optional, Union
from helpers.oid import to_object_id


from .BaseDataModel import BaseDataModel
from .db_schemas import Asset
from .Enum.DataBaseEnums import DataBaseEnums

import logging

logger = logging.getLogger("uvicorn.error")


class AssetModel(BaseDataModel):
    def __init__(self, db_client: AsyncIOMotorDatabase) -> None:
        super().__init__(db_client=db_client)
        self.collection: AsyncIOMotorCollection = self.db_client[
            DataBaseEnums.COLLECTION_ASSET_NAME.value
        ]

    @classmethod
    async def create_instance(cls, db_client: AsyncIOMotorDatabase) -> "AssetModel":
        instance: AssetModel = cls(db_client)
        await instance.init_collection()
        return instance

    async def init_collection(self) -> None:
        all_collection = await self.db_client.list_collection_names()
        if DataBaseEnums.COLLECTION_ASSET_NAME.value not in all_collection:
            self.collection = self.db_client[DataBaseEnums.COLLECTION_ASSET_NAME.value]
            indxes = Asset.get_indices()
            for index in indxes:
                await self.collection.create_index(
                    keys=index["key"], name=index["name"], unique=index["unique"]
                )

    async def create_Asset(self, asset: Asset) -> Asset:
        doc = asset.model_dump(by_alias=True, exclude_none=True, mode="python")
        result = await self.collection.insert_one(doc)
        asset.id = result.inserted_id
        return asset

    async def get_asset_by_project_and_type(
        self,
        asset_project_id: Union[str, ObjectId],
        asset_type: str,
    ) -> List[Asset]:
        proj_oid: Optional[ObjectId] = to_object_id(asset_project_id)
        if proj_oid is None:
            return []

        cursor = self.collection.find(
            {"asset_project_id": proj_oid, "asset_type": asset_type},
            projection={
                "_id": 1,
                "asset_project_id": 1,
                "asset_type": 1,
                "asset_name": 1,
                "asset_size": 1,
                "asset_pushed_at": 1,
                "asset_config": 1,
            },
        ).sort("_id", 1)

        docs = await cursor.to_list(length=None)
        return [Asset.model_validate(d) for d in docs]

    async def get_asset_by_project_and_name(
        self,
        asset_project_id: Union[str, ObjectId],
        asset_name: str,
    ) -> Optional[Asset]:
        project_oid = to_object_id(asset_project_id)
        if project_oid is None:
            return None

        rec = await self.collection.find_one(
            {"asset_project_id": project_oid, "asset_name": asset_name}
        )
        return Asset.model_validate(rec) if rec else None

    async def get_all_assests(self, page: int = 1, page_size: int = 10) -> Tuple[List[Asset], int]:
        #
        # count the total number of docs
        total_documents = await self.collection.count_documents({})

        # calculate total number of pages
        total_pages = (total_documents + page_size - 1) // page_size

        # get prjects in memory efficient way
        cursor = self.collection.find().skip((page - 1) * page_size).limit(page_size)
        items: List[Asset] = []
        async for doc in cursor:
            items.append(Asset.model_validate(doc))
        return items, total_pages
