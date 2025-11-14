from bson import ObjectId
from bson.errors import InvalidId
from motor.motor_asyncio import AsyncIOMotorDatabase
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import List, Tuple, Optional, Union


from .BaseDataModel import BaseDataModel
from .db_schemas import Asset
from .Enum.DataBaseEnums import DataBaseEnums


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
                    keys=index["key"],
                    name = index["name"],
                    unique = index["unique"]
                )


    async def create_Asset(self, asset: Asset) -> Asset:
        doc = asset.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(doc)
        asset.id = result.inserted_id
        return asset


    async def get_asset(self, asset_project_id: str) -> Asset:
        record = await self.collection.find_one({"asset_project_id": asset_project_id})
        if record is None:
            asset = Asset(asset_project_id=asset_project_id)
            return await self.create_Asset(asset=asset)
        return Asset.model_validate(record)


    async def get_all_assests(
        self, page: int = 1, page_size: int = 10
    ) -> Tuple[List[Asset], int]:
        # count the total number of docs
        total_documents = await self.collection.count_documents({})

        # calculate total number of pages
        total_pages = (total_documents + page_size - 1) // page_size

        # get prjects in memory efficient way
        cursor = (
            self.collection.find()
            .skip((page - 1) * page_size)
            .limit(page_size)
        )
        projects: List[Asset] = []
        async for doc in cursor:
            projects.append(Asset.model_validate(doc))
        return projects, total_pages
    

    @staticmethod
    def _to_object_id(value: Union[str, ObjectId]) -> Optional[ObjectId]:
        if isinstance(value, ObjectId):
            return value
        try:
            return ObjectId(value)
        except (InvalidId, TypeError):
            return None
