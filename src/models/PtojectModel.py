from motor.motor_asyncio import AsyncIOMotorDatabase
from motor.motor_asyncio import AsyncIOMotorCollection
from typing import List, Tuple

from numpy import indices
from .BaseDataModel import BaseDataModel
from .db_schemas import Project
from .Enum.DataBaseEnums import DataBaseEnums


class ProjectModel(BaseDataModel):
    def __init__(self, db_client: AsyncIOMotorDatabase) -> None:
        super().__init__(db_client=db_client)
        self.collection: AsyncIOMotorCollection = self.db_client[
            DataBaseEnums.COLLECTION_PROJECT_NAME.value
        ]
    
    
    @classmethod
    async def create_instance(cls, db_client: AsyncIOMotorDatabase):
        instance = cls(db_client)
        await instance.init_collection()
        return instance


    async def init_collection(self):
        all_collection = await self.db_client.list_collection_names()
        if DataBaseEnums.COLLECTION_PROJECT_NAME.value not in all_collection:
            self.collection = self.db_client[DataBaseEnums.COLLECTION_PROJECT_NAME.value]
            indxes = Project.get_indices()
            for index in indxes:
                await self.collection.create_index(
                    keys=index["key"],
                    name = index["name"],
                    unique = index["unique"]
                )


    async def create_project(self, project: Project) -> Project:
        doc = project.model_dump(by_alias=True, exclude_none=True)
        result = await self.collection.insert_one(doc)
        project.id = result.inserted_id
        return project


    async def get_project(self, project_id: str) -> Project:
        record = await self.collection.find_one({"project_id": project_id})
        if record is None:
            project = Project(project_id=project_id)
            return await self.create_project(project=project)
        return Project.model_validate(record)


    async def get_all_prjects(
        self, page: int = 1, page_size: int = 10
    ) -> Tuple[List[Project], int]:
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
        projects: List[Project] = []
        async for doc in cursor:
            projects.append(Project.model_validate(doc))
        return projects, total_pages
