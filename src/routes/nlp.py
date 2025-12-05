from fastapi import APIRouter, status, Request
from fastapi.responses import JSONResponse
from motor.motor_asyncio import AsyncIOMotorDatabase
from typing import Optional, List, cast, Tuple, Dict
import logging
from routes.schemas.nlp_schema import PushRequest, SearchRequest
from models.db_schemas import Project, DataChunk, RetrivedfDocument
from models import ResponseSignals
from models.PtojectModel import ProjectModel
from models.ChunkModel import ChunkModel
from controllers import NLPController
from stores.llm.LLMInterface import LLMInterface
from stores.vectordb.VectorDBInterface import VectorDBInterface

logger = logging.getLogger("uvicorn.error")

nlp_router = APIRouter(
    prefix="/api/v1/nlp",
    tags=["api_v1", "nlp"],
)


@nlp_router.post(path="/index/push/{project_id}")
async def index_project(
    request: Request, project_id: str, push_request: PushRequest
) -> JSONResponse:
    # 1) create clients
    db: AsyncIOMotorDatabase = cast(AsyncIOMotorDatabase, request.app.state.db)
    generation_client: LLMInterface = cast(LLMInterface, request.app.state.generation_client)
    embedding_client: LLMInterface = cast(LLMInterface, request.app.state.embedding_client)
    vectordb_client: VectorDBInterface = cast(VectorDBInterface, request.app.state.vectordb_client)

    # 2) create models
    project_model: ProjectModel = await ProjectModel.create_instance(db_client=db)
    project: Project = await project_model.get_project(project_id=project_id)
    if project.id is None or project.id is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignals.PROECT_ID_NOT_EXIST.value,
                "project_id": project_id,
            },
        )
    chunk_model: ChunkModel = await ChunkModel.create_instance(db_client=db)

    # 3) create nlp controller
    nlp_controller = NLPController(
        vectordb_client=vectordb_client,
        generation_client=generation_client,
        embedding_client=embedding_client,
    )

    # 4) get chunks related to project.id
    page: int = 1
    page_size: int = 50
    inserted_chunks_count: int = 0
    is_first_batch: bool = True

    while True:
        result: Optional[Tuple[List[DataChunk], int]] = await chunk_model.get_project_chunks(
            project_id=project.id,
            page=page,
            page_size=page_size,
        )

        if result is None:
            logger.error(f"Error retrieving chunks for project id: {project_id} ({project.id}")
            break

        chunk_list, total_pages = result

        if not chunk_list or total_pages == 0:
            logger.error(f"No chunks found for project id: {project_id} ({project.id})")
            break

        # 5) Insert chunks to vectorDB
        is_inserted: bool = nlp_controller.index_info_vector_db(
            project=project,
            chunks=chunk_list,
            do_reset=bool(push_request.do_reset) and is_first_batch,
        )

        if not is_inserted:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"signal": ResponseSignals.VECTORDB_INSERT_ERROR.value},
            )

        # increment counter
        inserted_chunks_count += len(chunk_list)
        is_first_batch = False

        # break loop when there is more pages to analyze
        if page >= total_pages:
            break
        page += 1
    return JSONResponse(
        content={
            "signal": ResponseSignals.VECTORDB_INSERT_SUCCESS.value,
            "inserted_chunks": inserted_chunks_count,
        }
    )


@nlp_router.get(path="/index/info/{project_id}")
async def get_project_index_info(request: Request, project_id: str) -> JSONResponse:
    # 1) create clients
    db: AsyncIOMotorDatabase = cast(AsyncIOMotorDatabase, request.app.state.db)
    generation_client: LLMInterface = cast(LLMInterface, request.app.state.generation_client)
    embedding_client: LLMInterface = cast(LLMInterface, request.app.state.embedding_client)
    vectordb_client: VectorDBInterface = cast(VectorDBInterface, request.app.state.vectordb_client)

    # 1) create models
    project_model: ProjectModel = await ProjectModel.create_instance(db_client=db)
    project: Project = await project_model.get_project(project_id=project_id)
    if project.id is None or project.id is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignals.PROECT_ID_NOT_EXIST.value,
                "project_id": project_id,
            },
        )

    # 3) create nlp controller
    nlp_controller = NLPController(
        vectordb_client=vectordb_client,
        generation_client=generation_client,
        embedding_client=embedding_client,
    )

    # 4)get the info of specific collection
    collection_info: Optional[Dict] = nlp_controller.get_vector_db_collection_info(project=project)
    if not collection_info:
        return JSONResponse(
            content={
                "signal": ResponseSignals.VECTORDB_INFO_RETRIEVAL_FAILED.value,
                "info": None,
            }
        )

    return JSONResponse(
        content={
            "signal": ResponseSignals.VECTORDB_INFO_RETRIEVED_SUCCESS.value,
            "info": collection_info,
        }
    )


@nlp_router.post(path="/index/search/{project_id}")
async def search_index(
    request: Request, project_id: str, search_request: SearchRequest
) -> JSONResponse:
    # 1) create clients
    db: AsyncIOMotorDatabase = cast(AsyncIOMotorDatabase, request.app.state.db)
    generation_client: LLMInterface = cast(LLMInterface, request.app.state.generation_client)
    embedding_client: LLMInterface = cast(LLMInterface, request.app.state.embedding_client)
    vectordb_client: VectorDBInterface = cast(VectorDBInterface, request.app.state.vectordb_client)

    # 2) create models
    project_model: ProjectModel = await ProjectModel.create_instance(db_client=db)
    project: Project = await project_model.get_project(project_id=project_id)
    if project.id is None or project.id is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignals.PROECT_ID_NOT_EXIST.value,
                "project_id": project_id,
            },
        )

    # 3) create nlp controller
    nlp_controller = NLPController(
        vectordb_client=vectordb_client,
        generation_client=generation_client,
        embedding_client=embedding_client,
    )

    # 4) perfrom semantoc search
    results: Optional[List[RetrivedfDocument]] = nlp_controller.search_vector_db_collection(
        project=project, text=search_request.text, limit=search_request.limit
    )
    if results is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignals.VECTORDB_SEARCH_RETRIEVAL_FAILED.value,
                "results": None,
            },
        )

    return JSONResponse(
        content={
            "signal": ResponseSignals.VECTORDB_SEARCH_RETRIEVED_SUCCESS.value,
            "results": [doc.model_dump() for doc in results],
        }
    )


@nlp_router.post(path="/index/answer/{project_id}")
async def answer_rag(
    request: Request, project_id: str, search_request: SearchRequest
) -> JSONResponse:
    # 1) create clients
    db: AsyncIOMotorDatabase = cast(AsyncIOMotorDatabase, request.app.state.db)
    generation_client: LLMInterface = cast(LLMInterface, request.app.state.generation_client)
    embedding_client: LLMInterface = cast(LLMInterface, request.app.state.embedding_client)
    vectordb_client: VectorDBInterface = cast(VectorDBInterface, request.app.state.vectordb_client)

    # 2) create models
    project_model: ProjectModel = await ProjectModel.create_instance(db_client=db)
    project: Project = await project_model.get_project(project_id=project_id)
    if project.id is None or project.id is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignals.PROECT_ID_NOT_EXIST.value,
                "project_id": project_id,
            },
        )

    # 3) create nlp controller
    nlp_controller = NLPController(
        vectordb_client=vectordb_client,
        generation_client=generation_client,
        embedding_client=embedding_client,
    )

    # 4) perfrom LLM call
    answer: Optional[str] = None
    full_prompt: Optional[str] = None
    chat_history: Optional[List[Dict[str, str]]] = None

    answer, full_prompt, chat_history = nlp_controller.answer_rag_question(
        project=project, query=search_request.text, limit=search_request.limit
    )

    if answer is None:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "signal": ResponseSignals.RAG_ANSWER_ERROR.value,
                "results": None,
            },
        )

    return JSONResponse(
        content={
            "signal": ResponseSignals.RAG_ANSWER_SUCCESS.value,
            "answer": answer,
            "full_prompt": full_prompt,
            "chat_history": chat_history,
        }
    )
