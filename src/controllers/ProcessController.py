from .BaseController import BaseController
from .ProjectController import ProjectController
from models import ProcessingEnums
from pathlib import Path
from typing import List, Optional
from langchain_core.documents.base import Document
from langchain_community.document_loaders import TextLoader, PyMuPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

class ProcessController(BaseController):
    def __init__(self, project_id):
        super().__init__()
        self.project_id: str = project_id
        self.project_path: Path = ProjectController().get_project_path(project_id=project_id)
        
    def get_file_content(self, file_id: str) -> Optional[List[Document]]:
        file_path: Path = self.project_path/file_id
        loader = None
        
        if not file_path.exists:
            return None
        
        if file_path.suffix == ProcessingEnums.TXT.value:
            loader = TextLoader(file_path=file_path, encoding="utf-8")
        
        if file_path.suffix == ProcessingEnums.PDF.value:
            loader =  PyMuPDFLoader(file_path=str(file_path))
        
        if loader:
            return loader.load()
        
        return None
    
    def process_file_content(self, file_content:List[Document], file_id:str, chunk_size:int =100,
                             overlap_size: int=20) -> List[Document]:
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size = chunk_size,
            chunk_overlap = overlap_size,
            length_function = len,
    
        )
        
        file_content_texts = [rec.page_content for rec in file_content]
        file_content_metadata = [rec.metadata for rec in file_content]
        chunks = text_splitter.create_documents(
            texts=file_content_texts,
            metadatas= file_content_metadata)
        return chunks
        
        
