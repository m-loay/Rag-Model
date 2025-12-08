from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from typing import List, Tuple

from .BaseDataModel import BaseDataModel
from .db_schema.Project import Project


class ProjectModel(BaseDataModel):
    def __init__(self, db_client: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(cls, db_client: async_sessionmaker[AsyncSession]) -> "ProjectModel":
        return cls(db_client)

    async def create_project(self, project: Project) -> Project:
        async with self.session_factory() as session:
            session.add(project)
            await session.commit()
            await session.refresh(project)
        return project

    async def get_project(self, project_id: str) -> Project:
        async with self.session_factory() as session:
            query = select(Project).where(Project.project_id == project_id)
            result = await session.execute(query)
            project: Project = result.scalar_one_or_none()
            if project is None:
                project = Project(project_id=project_id)
                project = await self.create_project(project=project)
            return project

    async def get_all_prjects(
        self, page: int = 1, page_size: int = 10
    ) -> Tuple[List[Project], int]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10

        async with self.session_factory() as session:
            # count the total number of docs
            query_count = select(func.count(Project.id))
            results = await session.execute(query_count)
            total_documents: int = results.scalar_one()
            if total_documents == 0:
                return [], 0

            # calculate total number of pages
            total_pages = (total_documents + page_size - 1) // page_size

            # get prjects in memory efficient way
            query = (
                select(Project)
                .order_by(Project.created_at.asc(), Project.id.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            results = await session.execute(query)
            projects: List[Project] = list(results.scalars().all())
            return projects, total_pages
