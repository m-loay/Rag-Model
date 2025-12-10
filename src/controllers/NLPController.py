from typing import Dict, Optional, List, Tuple, Any
from .BaseController import BaseController
from models.db import Project, DataChunk, RetrivedfDocument
from stores.llm.LLMInterface import LLMInterface, ChatMessage
from stores.llm.LLMEnums import DocumentTypeEnums
from stores.llm import RagPromptFactory, BasePrompt
from stores.vectordb.VectorDBInterface import VectorDBInterface
import logging


class NLPController(BaseController):
    def __init__(
        self,
        vectordb_client: VectorDBInterface,
        generation_client: LLMInterface,
        embedding_client: LLMInterface,
    ) -> None:
        super().__init__()
        self.vectordb_client: VectorDBInterface = vectordb_client
        self.generation_client: LLMInterface = generation_client
        self.embedding_client: LLMInterface = embedding_client
        self.logger = logging.getLogger(__name__)

    def create_collection_name(self, project_id: str) -> str:
        return f"collection_{project_id}".strip()

    async def reset_vector_db_collection(self, project: Project) -> bool:
        collection_name: str = self.create_collection_name(project_id=project.project_id)
        return await self.vectordb_client.delete_collection(collection_name=collection_name)

    async def get_vector_db_collection_info(self, project: Project) -> Optional[Dict]:
        collection_name: str = self.create_collection_name(project_id=project.project_id)
        collection_info: Optional[Dict] = await self.vectordb_client.get_collect_info(
            collection_name=collection_name
        )
        if not collection_info:
            self.logger.error(f"No info about this collection {collection_name}")
            return None
        return collection_info

    async def index_info_vector_db(
        self, project: Project, chunks: List[DataChunk], do_reset: bool = False
    ) -> bool:
        # 1) get collection name
        collection_name: str = self.create_collection_name(project_id=project.project_id)

        # 2) manage items
        texts: List[str] = []
        metadata: List[Dict[str, Any]] = []
        vectors: Optional[List[List[float]]] = []
        record_ids: List[str] = []
        for c in chunks:
            texts.append(c.chunk_text)
            metadata.append(c.chunk_metadata or {})
            record_ids.append(str(c.id))

        if not texts:
            self.logger.error("No valid chunks to index after embedding.")
            return False
        vectors = self.embedding_client.embed_text(
            text=texts, document_type=DocumentTypeEnums.DOCUMENT.value
        )
        if vectors is None:
            self.logger.error("Embedding provider returned None for batch documents")
            return False

        # 3) create collection vector database
        _ = await self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_model_size,
            do_reset=do_reset,
        )

        # 4) insert vectors database
        _ = await self.vectordb_client.insert_many(
            collection_name=collection_name,
            texts=texts,
            metadata=metadata,
            vectors=vectors,
            record_ids=record_ids,
        )
        return True

    async def search_vector_db_collection(
        self,
        project: Project,
        text: str,
        limit: int = 10,
    ) -> Optional[List[RetrivedfDocument]]:
        # 1) get collection name
        collection_name: str = self.create_collection_name(project_id=project.project_id)

        # 2) get text embedding vector
        vectors = self.embedding_client.embed_text(
            text=text,
            document_type=DocumentTypeEnums.QUERY.value,
        )

        if not vectors or len(vectors) == 0:
            self.logger.error("Embedding vector is None (embedding provider failed)")
            return None

        # 3) semantic search
        try:
            hits: Optional[List[RetrivedfDocument]] = await self.vectordb_client.search_by_vector(
                collection_name=collection_name,
                vector=vectors[0],
                limit=limit,
            )
        except Exception as e:
            self.logger.error(f"search_by_vector results error {e}")
            return None

        if hits is None:
            self.logger.error("Vector DB search returned None")
            return None
        return hits

    async def answer_rag_question(
        self,
        project: Project,
        query: str,
        limit: int = 10,
        language: str = "en",
    ) -> Tuple[Optional[str], Optional[str], Optional[List[ChatMessage]]]:
        answer: Optional[str] = None
        full_prompt: Optional[str] = None
        chat_history: Optional[List[ChatMessage]] = None

        # 1) retrieve document
        retrieved_documents: Optional[List[RetrivedfDocument]] = (
            await self.search_vector_db_collection(project=project, text=query, limit=limit)
        )

        if not retrieved_documents:
            return answer, full_prompt, chat_history

        # 2) Build the prompt(system prompt, then retrive doc, finally full prompt)
        rag_prompt: BasePrompt = RagPromptFactory.get_rag_prompt(language=language)
        system_prompt: str = rag_prompt.system_prompt()
        doc_texts: List[str] = [
            self.generation_client.limit_txt(doc.text) for doc in retrieved_documents
        ]
        full_prompt = rag_prompt.build_full_prompt(query=query, documents=doc_texts)

        # 3) call LLM
        answer, chat_history = self.generation_client.generate_text(
            prompt=full_prompt,
            system_prompt=system_prompt,
            max_output_tokens=self.generation_client.default_generation_max_output,
            temperture=self.generation_client.default_generation_temperture,
        )

        if answer is not None:
            self.logger.info("[RAG] LLM answer: \n" + answer)

        return answer, full_prompt, chat_history
