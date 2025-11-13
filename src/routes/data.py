from fastapi import APIRouter, Depends, UploadFile, status, Request
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import cast
from pathlib import Path
import aiofiles
import logging
from helpers.config import get_settings, Settings
from controllers import DataController, ProjectController, ProcessController
from models import ResponseSignals
from .schemas.data_schema import ProcessRequest
from models.PtojectModel import ProjectModel
from models.ChunkModel import ChunkModel
from models.db_schemas import DataChunk

logger = logging.getLogger("uvicorn.error")

data_router = APIRouter(
    prefix="/api/v1/data",
    tags=["api_v1", "data"],
)    

@data_router.post(path="/upload/{project_id}")
async def upload_data(request: Request, project_id: str, file: UploadFile,
                      app_settings: Settings = Depends(get_settings)) -> JSONResponse:

    # create project-model
    db = cast(AsyncIOMotorDatabase, request.app.state.db)
    project_model = await ProjectModel.create_instance(db_client=db)
    project = await project_model.get_project(project_id= project_id)
    
    # create data_controller object
    data_controller:DataController = DataController()
    
    # validate the file propertise (type and size)
    is_valid, res = data_controller.validate_uploaded_file(file=file)

    if not is_valid:
        return JSONResponse(
            status_code= status.HTTP_400_BAD_REQUEST,
            content= {
                "valid": is_valid,
                "signal": res
            }
        )
    
    # create folder for upload based project id and save the file
    project_path: Path = ProjectController().get_project_path(project_id=project_id)
    
    # check if file name is not corrupted else send error signal
    if file.filename:
        # create unique file name
        final_filename = data_controller.generate_unique_filename(orig_file_name= file.filename,
                                                                  orig_file_path= project_path)
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
                status_code= status.HTTP_400_BAD_REQUEST,
                content= {
                    "valid": is_valid,
                    "signal": ResponseSignals.FILE_UPLOAD_FAILED.value
                }
            )
        
        # return success if file was uploaded correctly
        return JSONResponse(
            content= {
                "valid": is_valid,
                "file_id": final_filename,
                "signal": ResponseSignals.FILE_UPLOAD_SUCESS.value,
                "project_id": str(project_id)
            }
        )

    # return error signal if if file name is corrupted
    return JSONResponse(
        status_code= status.HTTP_400_BAD_REQUEST,
        content= {
            "valid": is_valid,
            "signal": ResponseSignals.FILE_NAME_CORRUPTED.value
        }
    )


@data_router.post("/process/{project_id}")
async def process_endpoint(request: Request, project_id: str, process_request:ProcessRequest) -> JSONResponse:
    
    db = cast(AsyncIOMotorDatabase, request.app.state.db)
    project_model = await ProjectModel.create_instance(db_client=db)
    project = await project_model.get_project(project_id= project_id)
    
    process_controller = ProcessController(project_id=project_id)
    file_content = process_controller.get_file_content(file_id=process_request.file_id)

    if file_content:
        file_chunks = process_controller.process_file_content(
            file_content=file_content,
            file_id=process_request.file_id,
            chunk_size= process_request.chunk_size,
            overlap_size= process_request.overlap_size
        )
        if file_chunks is not None and len(file_chunks) > 0:
            file_chunks_records = [
                DataChunk(
                    chunk_text= chunk.page_content,
                    chunk_metadata= chunk.metadata,
                    chunk_order= i+1,
                    chunk_project_id= project.id
                )
                for i, chunk in enumerate(file_chunks)
            ]
            chunk_model = await ChunkModel.create_instance(db_client= db)
            if process_request.do_reset:
                deleted = await chunk_model.delete_chunks_by_project_id(project_ref=project.id) # type: ignore

            no_records = await chunk_model.insert_many_chunks(chunks=file_chunks_records)    
            return JSONResponse(
                content= {
                    "signal": ResponseSignals.PROCESSING_SUCCESS.value,
                    "inserted_chunks": no_records
                }
            )
        else:
            return JSONResponse(
                status_code= status.HTTP_400_BAD_REQUEST,
                content= {
                    "signal": ResponseSignals.PROCESSING_FAILED.value
                }
            )
    else:
        return JSONResponse(
            status_code= status.HTTP_400_BAD_REQUEST,
            content= {
                "signal": ResponseSignals.FILE_NO_CONTENT.value
            }
        )