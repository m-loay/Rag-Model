from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.future import select
from sqlalchemy import func
from typing import List, Tuple, Optional, Union


from .BaseDataModel import BaseDataModel
from .db_schema.Asset import Asset
import logging

logger = logging.getLogger("uvicorn.error")


class AssetModel(BaseDataModel):
    def __init__(self, db_client: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(db_client=db_client)

    @classmethod
    async def create_instance(cls, db_client: async_sessionmaker[AsyncSession]) -> "AssetModel":
        return cls(db_client)

    @staticmethod
    def _normalize_project_id(project_id: Union[int, str]) -> int:
        return int(project_id)

    async def create_Asset(self, asset: Asset) -> Asset:
        async with self.session_factory() as session:
            session.add(asset)
            await session.commit()
            await session.refresh(asset)
            return asset

    async def get_asset_by_project_and_type(
        self,
        asset_project_id: Union[int, str],
        asset_type: str,
    ) -> List[Asset]:
        project_pk = self._normalize_project_id(asset_project_id)
        async with self.session_factory() as session:
            query = (
                select(Asset)
                .where(Asset.asset_project_id == project_pk, Asset.asset_type == asset_type)
                .order_by(Asset.id.asc())
            )
            results = await session.execute(query)
            records: List[Asset] = list(results.scalars().all())
        return records

    async def get_asset_by_project_and_name(
        self,
        asset_project_id: Union[int, str],
        asset_name: str,
    ) -> Optional[Asset]:
        project_pk = self._normalize_project_id(asset_project_id)
        async with self.session_factory() as session:
            query = select(Asset).where(
                Asset.asset_project_id == project_pk, Asset.asset_name == asset_name
            )
            results = await session.execute(query)
            record: Optional[Asset] = results.scalar_one_or_none()
        return record

    async def get_all_assests(self, page: int = 1, page_size: int = 10) -> Tuple[List[Asset], int]:
        if page < 1:
            page = 1
        if page_size < 1:
            page_size = 10

        async with self.session_factory() as session:
            # count the total number of docs
            query = select(func.count(Asset.id))
            results = await session.execute(query)
            total_assets: int = results.scalar_one()
            if total_assets == 0:
                return [], 0

            total_pages = (total_assets + page_size - 1) // page_size

            # get assets
            stmt = (
                select(Asset)
                .order_by(Asset.id.asc())
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
            results = await session.execute(stmt)
            items: List[Asset] = list(results.scalars().all())
        return items, total_pages
