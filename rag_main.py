"""
FastAPI Application cho RAG System
Endpoints:
- POST /ingest: Quét PDF và lưu vào ChromaDB
- POST /chat: Chat với RAG system
- GET /health: Health check
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import os
from dotenv import load_dotenv
import logging

from rag_service import RAGService

# Load environment variables
load_dotenv()

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Khởi tạo FastAPI app
app = FastAPI(
    title="RAG System API",
    description="Retrieval-Augmented Generation System với Gemini và ChromaDB",
    version="1.0.0"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Trong production nên chỉ định origins cụ thể
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo RAG Service
rag_service: Optional[RAGService] = None


def get_rag_service() -> RAGService:
    """Lấy hoặc khởi tạo RAG Service"""
    global rag_service
    
    if rag_service is None:
        # Hỗ trợ cả GOOGLE_API_KEY và GEMINI_API_KEY (Firebase Functions)
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY hoặc GEMINI_API_KEY không được tìm thấy. Hãy set trong .env file hoặc environment variables.")
        
        rag_service = RAGService(
            data_dir=os.getenv("DATA_DIR", "./data"),
            db_dir=os.getenv("DB_DIR", "./db"),
            api_key=api_key,
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "100"))
        )
    
    return rag_service


# Pydantic Models cho Request/Response
class ChatRequest(BaseModel):
    """Request model cho /chat endpoint"""
    query: str = Field(..., description="Câu hỏi của user", min_length=1, max_length=1000)
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Máy bơm có công suất bao nhiêu?"
            }
        }


class ChatResponse(BaseModel):
    """Response model cho /chat endpoint"""
    answer: str = Field(..., description="Câu trả lời từ RAG system")
    sources: List[Dict[str, Any]] = Field(..., description="Danh sách sources (file name, page number)")
    query: str = Field(..., description="Câu hỏi gốc")
    error: Optional[str] = Field(None, description="Lỗi nếu có")


class IngestResponse(BaseModel):
    """Response model cho /ingest endpoint"""
    status: str = Field(..., description="Status: success, warning, error")
    message: str = Field(..., description="Thông báo")
    total_documents: int = Field(..., description="Tổng số documents")
    total_chunks: int = Field(..., description="Tổng số chunks")
    total_files: Optional[int] = Field(None, description="Tổng số files")
    files: Optional[List[str]] = Field(None, description="Danh sách tên files")


class HealthResponse(BaseModel):
    """Response model cho /health endpoint"""
    status: str
    service: str
    rag_ready: bool
    data_dir: str
    db_dir: str


# API Endpoints
@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "message": "RAG System API",
        "version": "1.0.0",
        "endpoints": {
            "ingest": "POST /ingest - Ingest PDF files",
            "chat": "POST /chat - Chat with RAG system",
            "health": "GET /health - Health check"
        }
    }


@app.get("/health", tags=["General"], response_model=HealthResponse)
async def health():
    """
    Health check endpoint
    Kiểm tra trạng thái của service và RAG system
    """
    try:
        service = get_rag_service()
        rag_ready = service.is_ready()
        
        return HealthResponse(
            status="OK",
            service="RAG System",
            rag_ready=rag_ready,
            data_dir=str(service.data_dir),
            db_dir=str(service.db_dir)
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="ERROR",
            service="RAG System",
            rag_ready=False,
            data_dir=os.getenv("DATA_DIR", "./data"),
            db_dir=os.getenv("DB_DIR", "./db")
        )


@app.post("/ingest", tags=["RAG"], response_model=IngestResponse)
async def ingest_documents():
    """
    Ingest endpoint - Quét toàn bộ PDF trong thư mục data và lưu vào ChromaDB
    
    - Quét tất cả file PDF trong thư mục ./data
    - Chia nhỏ thành chunks (chunk_size=1000, overlap=100)
    - Tạo embeddings và lưu vào ChromaDB tại ./db
    """
    try:
        logger.info("Nhận request ingest documents")
        service = get_rag_service()
        
        result = service.ingest_documents()
        
        logger.info(f"Ingest completed: {result.get('status')}")
        
        return IngestResponse(**result)
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        raise HTTPException(
            status_code=404,
            detail=f"Thư mục data không tồn tại: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Lỗi khi ingest: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xử lý: {str(e)}"
        )


@app.post("/chat", tags=["RAG"], response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Chat endpoint - Nhận query và trả về answer với sources
    
    - Tìm kiếm các đoạn văn bản liên quan nhất từ ChromaDB
    - Sử dụng Gemini để tổng hợp câu trả lời
    - Trả về answer kèm sources (file name, page number)
    
    Request body:
    {
        "query": "Câu hỏi của user"
    }
    
    Response:
    {
        "answer": "Câu trả lời từ RAG system",
        "sources": [
            {
                "file_name": "document.pdf",
                "page_number": 5,
                "content_preview": "..."
            }
        ],
        "query": "Câu hỏi gốc"
    }
    """
    try:
        logger.info(f"Nhận query: {request.query}")
        service = get_rag_service()
        
        result = service.chat(request.query)
        
        # Kiểm tra có lỗi không
        if "error" in result:
            return ChatResponse(
                answer=result.get("answer", ""),
                sources=result.get("sources", []),
                query=request.query,
                error=result.get("error")
            )
        
        return ChatResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            query=result.get("query", request.query),
            error=None
        )
        
    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Lỗi khi xử lý chat: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xử lý: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("PORT", "8000"))
    logger.info(f"Starting RAG System API on port {port}...")
    
    uvicorn.run(
        "rag_main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
