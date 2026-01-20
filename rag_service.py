"""
RAG Service - Xử lý logic RAG (Retrieval-Augmented Generation)
- Load PDF từ thư mục
- Chia nhỏ text thành chunks
- Tạo embeddings và lưu vào ChromaDB
- Tìm kiếm semantic và generate answer với Gemini
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path

from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate
from langchain.schema import Document

import logging

logger = logging.getLogger(__name__)


class RAGService:
    """Service xử lý RAG pipeline"""
    
    def __init__(
        self,
        data_dir: str = "./data",
        db_dir: str = "./db",
        api_key: Optional[str] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 100
    ):
        """
        Khởi tạo RAG Service
        
        Args:
            data_dir: Thư mục chứa file PDF
            db_dir: Thư mục lưu ChromaDB
            api_key: Google Gemini API key
            chunk_size: Kích thước mỗi chunk (ký tự)
            chunk_overlap: Số ký tự overlap giữa các chunks
        """
        self.data_dir = Path(data_dir)
        self.db_dir = Path(db_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        
        # Tạo thư mục nếu chưa tồn tại
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db_dir.mkdir(parents=True, exist_ok=True)
        
        # Khởi tạo models
        # Hỗ trợ cả GOOGLE_API_KEY và GEMINI_API_KEY (Firebase Functions)
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("Google Gemini API key is required. Set GOOGLE_API_KEY hoặc GEMINI_API_KEY in .env file hoặc environment variables.")
        
        self.api_key = api_key
        
        # Hỗ trợ cả GOOGLE_API_KEY và GEMINI_API_KEY (Firebase Functions)
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("Google Gemini API key is required. Set GOOGLE_API_KEY hoặc GEMINI_API_KEY in .env file hoặc environment variables.")
        
        # Initialize LLM và Embeddings
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.7
        )
        
        self.embeddings = GoogleGenerativeAIEmbeddings(
            model="models/text-embedding-004",
            google_api_key=api_key
        )
        
        # Vector store sẽ được khởi tạo sau khi ingest
        self.vector_store: Optional[Chroma] = None
        self.qa_chain: Optional[RetrievalQA] = None
        
        logger.info("RAG Service initialized successfully")
    
    def ingest_documents(self) -> Dict[str, Any]:
        """
        Quét toàn bộ PDF trong data_dir, chia nhỏ và lưu vào ChromaDB
        
        Returns:
            Dict chứa thông tin về quá trình ingest
        """
        logger.info(f"Bắt đầu ingest documents từ {self.data_dir}")
        
        # Kiểm tra thư mục data có tồn tại không
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Thư mục {self.data_dir} không tồn tại")
        
        # Load PDF files từ thư mục
        logger.info("Đang load PDF files...")
        loader = PyPDFDirectoryLoader(str(self.data_dir))
        
        try:
            documents = loader.load()
            logger.info(f"Đã load {len(documents)} documents từ PDF files")
        except Exception as e:
            logger.error(f"Lỗi khi load PDF: {e}")
            raise
        
        if not documents:
            return {
                "status": "warning",
                "message": "Không tìm thấy file PDF nào trong thư mục data",
                "total_documents": 0,
                "total_chunks": 0
            }
        
        # Chia nhỏ documents thành chunks
        logger.info(f"Đang chia nhỏ documents (chunk_size={self.chunk_size}, overlap={self.chunk_overlap})...")
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.chunk_size,
            chunk_overlap=self.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        chunks = text_splitter.split_documents(documents)
        logger.info(f"Đã chia thành {len(chunks)} chunks")
        
        # Tạo metadata cho mỗi chunk (tên file và số trang)
        for i, chunk in enumerate(chunks):
            # Extract metadata từ source
            source = chunk.metadata.get("source", "")
            page = chunk.metadata.get("page", 0)
            
            # Lấy tên file từ path
            file_name = Path(source).name if source else f"unknown_{i}"
            
            # Cập nhật metadata
            chunk.metadata["file_name"] = file_name
            chunk.metadata["page_number"] = page
            chunk.metadata["chunk_index"] = i
        
        # Lưu vào ChromaDB
        logger.info(f"Đang lưu {len(chunks)} chunks vào ChromaDB tại {self.db_dir}...")
        
        try:
            # Xóa vector store cũ nếu có
            if self.vector_store is not None:
                # ChromaDB sẽ tự động merge nếu collection đã tồn tại
                pass
            
            # Tạo hoặc load vector store
            self.vector_store = Chroma.from_documents(
                documents=chunks,
                embedding=self.embeddings,
                persist_directory=str(self.db_dir)
            )
            
            # Persist để lưu vào disk
            self.vector_store.persist()
            
            logger.info("Đã lưu thành công vào ChromaDB")
            
            # Tạo QA chain với custom prompt
            self._create_qa_chain()
            
            # Thống kê
            file_names = set(chunk.metadata.get("file_name", "unknown") for chunk in chunks)
            
            return {
                "status": "success",
                "message": f"Đã ingest thành công {len(chunks)} chunks từ {len(file_names)} files",
                "total_documents": len(documents),
                "total_chunks": len(chunks),
                "total_files": len(file_names),
                "files": list(file_names)
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi lưu vào ChromaDB: {e}", exc_info=True)
            raise
    
    def _create_qa_chain(self):
        """Tạo QA chain với custom prompt"""
        if self.vector_store is None:
            raise ValueError("Vector store chưa được khởi tạo. Hãy chạy ingest_documents() trước.")
        
        # Custom prompt template để Gemini trả lời dựa trên context
        prompt_template = """Bạn là một trợ lý AI thông minh. Hãy trả lời câu hỏi dựa trên các đoạn văn bản được cung cấp bên dưới.

Context (các đoạn văn bản liên quan):
{context}

Câu hỏi: {question}

Hướng dẫn:
- Chỉ trả lời dựa trên thông tin có trong context
- Nếu không tìm thấy thông tin trong context, hãy nói rõ "Tôi không tìm thấy thông tin này trong tài liệu"
- Trả lời bằng tiếng Việt nếu câu hỏi là tiếng Việt
- Trả lời ngắn gọn, chính xác và dễ hiểu

Câu trả lời:"""
        
        PROMPT = PromptTemplate(
            template=prompt_template,
            input_variables=["context", "question"]
        )
        
        # Tạo retriever với k=4 (lấy 4 chunks liên quan nhất)
        retriever = self.vector_store.as_retriever(
            search_type="similarity",
            search_kwargs={"k": 4}
        )
        
        # Tạo QA chain
        self.qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            chain_type_kwargs={"prompt": PROMPT},
            return_source_documents=True
        )
        
        logger.info("QA chain đã được tạo")
    
    def chat(self, query: str) -> Dict[str, Any]:
        """
        Nhận query từ user, tìm kiếm và generate answer
        
        Args:
            query: Câu hỏi của user
            
        Returns:
            Dict chứa answer và sources
        """
        if self.qa_chain is None:
            # Thử load vector store nếu đã có
            try:
                self.vector_store = Chroma(
                    persist_directory=str(self.db_dir),
                    embedding_function=self.embeddings
                )
                self._create_qa_chain()
                logger.info("Đã load vector store từ disk")
            except Exception as e:
                logger.error(f"Không thể load vector store: {e}")
                return {
                    "error": "Chưa có dữ liệu. Hãy chạy /ingest trước để load PDF files.",
                    "answer": None,
                    "sources": []
                }
        
        logger.info(f"Nhận query: {query}")
        
        try:
            # Chạy QA chain
            result = self.qa_chain.invoke({"query": query})
            
            answer = result.get("result", "Không thể tạo câu trả lời")
            source_documents = result.get("source_documents", [])
            
            # Format sources với tên file và số trang
            sources = []
            seen_sources = set()
            
            for doc in source_documents:
                file_name = doc.metadata.get("file_name", "unknown")
                page_number = doc.metadata.get("page_number", 0)
                
                # Tránh duplicate
                source_key = (file_name, page_number)
                if source_key not in seen_sources:
                    seen_sources.add(source_key)
                    sources.append({
                        "file_name": file_name,
                        "page_number": int(page_number) + 1,  # +1 vì page number bắt đầu từ 0
                        "content_preview": doc.page_content[:200] + "..." if len(doc.page_content) > 200 else doc.page_content
                    })
            
            logger.info(f"Đã tìm thấy {len(sources)} sources")
            
            return {
                "answer": answer,
                "sources": sources,
                "query": query
            }
            
        except Exception as e:
            logger.error(f"Lỗi khi xử lý query: {e}", exc_info=True)
            return {
                "error": f"Lỗi khi xử lý query: {str(e)}",
                "answer": None,
                "sources": []
            }
    
    def is_ready(self) -> bool:
        """Kiểm tra xem RAG service đã sẵn sàng chưa (đã ingest documents)"""
        if self.vector_store is None:
            # Thử load từ disk
            try:
                self.vector_store = Chroma(
                    persist_directory=str(self.db_dir),
                    embedding_function=self.embeddings
                )
                self._create_qa_chain()
                return True
            except:
                return False
        return True
