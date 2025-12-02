from os import system
from pydoc import text
import re
from typing import Dict, Optional, List, Tuple

from .BaseController import BaseController
from models.db_schemas import Project, DataChunk, RetrivedfDocument
from stores.llm.LLMInterface import LLMInterface
from stores.llm.LLMEnums import DocumentTypeEnums, OpenAIEnums, CoHereEnums
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

    def reset_vector_db_collection(self, project: Project) -> bool:
        collection_name: str = self.create_collection_name(project_id=project.project_id)
        return self.vectordb_client.delete_collection(collection_name=collection_name)

    def get_vector_db_collection_info(self, project: Project) -> Optional[Dict]:
        collection_name: str = self.create_collection_name(project_id=project.project_id)
        collection_info: Optional[Dict] = self.vectordb_client.get_collect_info(
            collection_name=collection_name
        )
        if not collection_info:
            self.logger.error(f"No info about this collection {collection_name}")
            return None
        return collection_info

    def index_info_vector_db(
        self, project: Project, chunks: List[DataChunk], do_reset: bool = False
    ) -> bool:
        # 1) get collection name
        collection_name: str = self.create_collection_name(project_id=project.project_id)

        # 2) manage items
        texts = [c.chunk_text for c in chunks]
        metadata = [c.chunk_metadata for c in chunks]

        vectors: List[List[float]] = []
        for text in texts:
            v = self.embedding_client.embed_text(
                text=text, document_type=DocumentTypeEnums.DOCUMENT.value
            )
            if v is None:
                self.logger.error("skipping chunk because of embeddings is None")
                continue
            if v and isinstance(v, list) and isinstance(v[0], (list, tuple)):
                v = v[0]
            vectors.append(v)  # type: ignore

        # 3) create collection vector database
        _ = self.vectordb_client.create_collection(
            collection_name=collection_name,
            embedding_size=self.embedding_client.embedding_model_size,
            do_reset=do_reset,
        )

        # 4) insert vectors database
        _ = self.vectordb_client.insert_many(
            collection_name=collection_name, texts=texts, metadata=metadata, vectors=vectors
        )
        return True

    def search_vector_db_collection(
        self,
        project: Project,
        text: str,
        limit: int = 10,
    ) -> Optional[List[RetrivedfDocument]]:
        # 1) get collection name
        collection_name: str = self.create_collection_name(project_id=project.project_id)

        # 2) get text embedding vector
        vector = self.embedding_client.embed_text(
            text=text,
            document_type=DocumentTypeEnums.QUERY.value,
        )

        if vector is None:
            self.logger.error("Embedding vector is None (embedding provider failed)")
            return None

        # 3) semantic search
        try:
            hits: Optional[List[RetrivedfDocument]] = self.vectordb_client.search_by_vector(
                collection_name=collection_name,
                vector=vector,
                limit=limit,
            )
        except Exception as e:
            self.logger.error(f"search_by_vector results error {e}")
            return None

        if hits is None:
            self.logger.error("Vector DB search returned None")
            return None
        return hits

    def answer_rag_question(
        self,
        project: Project,
        query: str,
        limit: int = 10,
        language: str = "en",
    ) -> Tuple[Optional[str], Optional[str], Optional[List[dict]]]:
        answer: Optional[str] = None
        full_prompt: Optional[str] = None
        chat_history: Optional[List[Dict[str, str]]] = None

        # 1) retrieve document
        retrieved_documents: Optional[List[RetrivedfDocument]] = self.search_vector_db_collection(
            project=project, text=query, limit=limit
        )

        if not retrieved_documents:
            return answer, full_prompt, chat_history

        # 2) Build the prompt(system prompt, then retrive doc, finally full prompt)
        rag_prompt: BasePrompt = RagPromptFactory.get_rag_prompt(language=language)
        system_prompt: str = rag_prompt.system_prompt()
        doc_texts: List[str] = [doc.text for doc in retrieved_documents]
        full_prompt = rag_prompt.build_full_prompt(query=query, documents=doc_texts)

        # 3) call LLM
        answer = self.generation_client.generate_text(
            prompt=full_prompt,
            chat_history=system_prompt,
            max_output_tokens=self.generation_client.default_generation_max_output,
            temperture=self.generation_client.default_generation_temperture,
        )

        if answer is not None:
            self.logger.info("[RAG] LLM answer (first 400 chars): " + answer[:400])

        return answer, full_prompt, chat_history
