from bson import ObjectId
from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
from typing import Optional
from pathlib import Path
import aiofiles
import logging
from helpers.config import get_settings, Settings
from controllers import DataController, ProjectController, ProcessController
from models import ResponseSignals, AssetTypeEnum
from .schemas.data_schema import ProcessRequest
from models.db import Project, DataChunk, Asset
from models.db import ProjectModel, ChunkModel, AssetModel


logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)


@data_router.post(path="/upload/{project_id}")
async def upload_data(
    request: Request,
    project_id: str,
    file: UploadFile,
    app_settings: Settings = Depends(get_settings),
) -> JSONResponse:

    # create project-model
    db_client = request.app.state.db
    project_model: ProjectModel = await ProjectModel.create_instance(db_client=db_client)
    project: Project = await project_model.get_project(project_id=project_id)
    if project.id is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignals.PROECT_ID_NOT_EXIST.value,
                "project_id": str(project.id),
            },
        )

    # create data_controller object
    data_controller: DataController = DataController()

    # validate the file propertise (type and size)
    is_valid, res = data_controller.validate_uploaded_file(file=file)

    if not is_valid:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": res,
                "valid": is_valid,
            },
        )

    # create folder for upload based project id and save the file
    project_path: Optional[Path] = ProjectController().get_project_path(project_id=project_id)
    if project_path is None:
        logger.error(f"upload cant find file location")
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignals.FILE_UPLOAD_FAILED.value,
                "file_name": file.filename,
            },
        )

    # check if file name is not corrupted else send error signal
    if file.filename:
        # create unique file name
        final_filename = data_controller.generate_unique_filename(
            orig_file_name=file.filename, orig_file_path=project_path
        )
        file_path: Path = project_path / final_filename

        # upload the files on chuncks
        try:
            async with aiofiles.open(str(file_path), "wb") as f:
                while chunk := await file.read(app_settings.FILE_DEFAULT_CHUNK_SIZE):
                    await f.write(chunk)
        except Exception as e:
            # log error and send error signal
            logger.error(f"Error while uploading file {e}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "signal": ResponseSignals.FILE_UPLOAD_FAILED.value,
                    "file_name": final_filename,
                },
            )

        # return success if file was uploaded correctly
        # store assets iin db
        asse_model: AssetModel = await AssetModel.create_instance(db_client=db_client)
        asset_resource: Asset = Asset(
            asset_project_id=project.id,
            asset_type=AssetTypeEnum.FILE.value,
            asset_name=final_filename,
            asset_size=file_path.stat().st_size,
        )
        asset_record: Asset = await asse_model.create_Asset(asset=asset_resource)

        return JSONResponse(
            content={
                "signal": ResponseSignals.FILE_UPLOAD_SUCESS.value,
                "file_id": str(asset_record.id),
                "file_name": final_filename,
            }
        )

    # return error signal if if file name is corrupted
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "signal": ResponseSignals.FILE_NAME_CORRUPTED.value,
            "file_name": file.filename,
        },
    )


@data_router.post("/process/{project_id}")
async def process_endpoint(
    request: Request, project_id: str, process_request: ProcessRequest
) -> JSONResponse:

    # create database connection
    db_client = request.app.state.db
    db_backend: str = getattr(request.app.state, "db_backend", "mongodb").lower()

    # create project model
    project_model: ProjectModel = await ProjectModel.create_instance(db_client=db_client)
    project: Project = await project_model.get_project(project_id=project_id)
    if project.id is None:

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignals.PROECT_ID_NOT_EXIST.value,
                "project_id": str(project.id),
            },
        )

    # create asset model
    asset_model: AssetModel = await AssetModel.create_instance(db_client=db_client)

    # collect project files ids
    project_files_ids: dict[str, str]

    if process_request.file_id:
        asset_record: Optional[Asset] = await asset_model.get_asset_by_project_and_name(
            asset_project_id=project.id,
            asset_name=process_request.file_id,
        )
        logger.info(
            "find_one filter=%s",
            {"asset_project_id": project.id, "asset_name": process_request.file_id},
        )
        if asset_record is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "project_id": str(project.id),
                    "asset_name": process_request.file_id,
                    "signal": ResponseSignals.ASSET_RECORD_NOT_VALID.value,
                },
            )

        project_files_ids = {str(asset_record.id): asset_record.asset_name}
    else:
        assets: list[Asset] = await asset_model.get_asset_by_project_and_type(
            asset_project_id=project.id,
            asset_type=AssetTypeEnum.FILE.value,
        )

        if not assets:  # empty list => no records
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "project_id": str(project.id),
                    "signal": ResponseSignals.ASSET_RECORD_NOT_VALID.value,
                },
            )

        # Use string keys if you’ll JSON-serialize later
        project_files_ids = {str(rec.id): rec.asset_name for rec in assets if rec.id is not None}

    if len(project_files_ids) == 0:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignals.NO_FILES_ERROR.value,
            },
        )

    # create process controller
    process_controller: ProcessController = ProcessController(project_id=project_id)

    # create chunk model
    chunk_model: ChunkModel = await ChunkModel.create_instance(db_client=db_client)

    # do reset if required by process request
    if process_request.do_reset:
        deleted = await chunk_model.delete_chunks_by_project_id(chunk_project_id=project.id)

    # counters for records and files
    no_records = 0
    no_files = 0

    for asset_id, file_id in project_files_ids.items():
        # extract file content
        file_content = process_controller.get_file_content(file_id=file_id)
        if file_content is None:
            logger.error(f"Error while processing file: {file_id}")
            continue

        file_chunks = process_controller.process_file_content(
            file_content=file_content,
            file_id=file_id,
            chunk_size=process_request.chunk_size,
            overlap_size=process_request.overlap_size,
        )

        if file_chunks is None or len(file_chunks) == 0:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignals.PROCESSING_FAILED.value},
            )

        if db_backend == "mongodb":
            asset_reference = ObjectId(asset_id)
        else:
            asset_reference = int(asset_id)

        file_chunks_records = [
            DataChunk(
                chunk_text=chunk.page_content,
                chunk_metadata=chunk.metadata,
                chunk_order=i + 1,
                chunk_project_id=project.id,
                chunk_asset_id=asset_reference,
            )
            for i, chunk in enumerate(file_chunks)
        ]

        no_records = await chunk_model.insert_many_chunks(chunks=file_chunks_records)
        no_files += 1
    return JSONResponse(
        content={
            "signal": ResponseSignals.PROCESSING_SUCCESS.value,
            "inserted_chunks": no_records,
            "processed_files": no_files,
        }
    )
