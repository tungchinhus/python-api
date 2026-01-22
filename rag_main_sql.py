"""
FastAPI Application cho RAG System với SQL Server 2025 Vector
Endpoints:
- POST /ingest: Quét PDF và lưu vào SQL Server với VECTOR type
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

from rag_service_sql import RAGServiceSQL

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
    title="RAG System API (SQL Server Vector)",
    description="Retrieval-Augmented Generation System với Gemini, SQL Server 2025 Vector",
    version="1.0.0"
)

# Cấu hình CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Khởi tạo RAG Service
rag_service: Optional[RAGServiceSQL] = None


def get_rag_service() -> RAGServiceSQL:
    """Lấy hoặc khởi tạo RAG Service"""
    global rag_service
    
    if rag_service is None:
        # Connection string từ .env
        connection_string = os.getenv("SQL_CONNECTION_STRING")
        if not connection_string:
            # Hoặc build từ các biến riêng lẻ
            server = os.getenv("SQL_SERVER", "localhost")
            database = os.getenv("SQL_DATABASE", "THITHI_AI")
            trusted_connection = os.getenv("SQL_TRUSTED_CONNECTION", "yes")
            
            if trusted_connection.lower() == "yes":
                connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;"
            else:
                username = os.getenv("SQL_USERNAME")
                password = os.getenv("SQL_PASSWORD")
                connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
        
        # Hỗ trợ cả GOOGLE_API_KEY và GEMINI_API_KEY (Firebase Functions)
        api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ValueError("GOOGLE_API_KEY hoặc GEMINI_API_KEY không được tìm thấy. Hãy set trong .env file hoặc environment variables.")
        
        # Cấu hình embedding
        use_sql_embeddings = os.getenv("USE_SQL_EMBEDDINGS", "false").lower() == "true"
        embedding_model_name = os.getenv("EMBEDDING_MODEL_NAME", "local_onnx_embeddings")
        embedding_dimension = int(os.getenv("EMBEDDING_DIMENSION", "768"))
        
        rag_service = RAGServiceSQL(
            connection_string=connection_string,
            data_dir=os.getenv("DATA_DIR", "./data"),
            table_name=os.getenv("RAG_TABLE_NAME", "rag_documents"),
            api_key=api_key,
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            chunk_overlap=int(os.getenv("CHUNK_OVERLAP", "100")),
            embedding_dimension=embedding_dimension,
            use_sql_embeddings=use_sql_embeddings,
            embedding_model_name=embedding_model_name
        )
    
    return rag_service


# Pydantic Models
class ChatRequest(BaseModel):
    """Request model cho /chat endpoint"""
    query: str = Field(..., description="Câu hỏi của user", min_length=1, max_length=1000)
    top_k: Optional[int] = Field(4, description="Số lượng kết quả tối đa", ge=1, le=20)
    similarity_threshold: Optional[float] = Field(0.5, description="Ngưỡng similarity tối thiểu", ge=0.0, le=1.0)
    return_suggestions: Optional[bool] = Field(True, description="Trả về suggestions khi có nhiều kết quả")
    selected_suggestion_ids: Optional[List[int]] = Field(None, description="Danh sách ID của suggestions được chọn")
    table_name: Optional[str] = Field(None, description="Tên bảng cụ thể để tìm (nếu None, dùng RAG_TABLE_NAME)")
    search_multiple_tables: Optional[bool] = Field(False, description="Tìm trong nhiều bảng")
    table_names: Optional[List[str]] = Field(None, description="Danh sách tên bảng để tìm (nếu search_multiple_tables=True)")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Máy bơm có công suất bao nhiêu?",
                "top_k": 4,
                "similarity_threshold": 0.5,
                "return_suggestions": True
            }
        }


class SuggestionItem(BaseModel):
    """Model cho một suggestion item"""
    index: int
    id: int
    content_preview: str
    file_name: str
    page_number: int
    similarity: float
    similarity_percent: float


class SuggestionsData(BaseModel):
    """Model cho suggestions data"""
    has_suggestions: bool
    total_available: int
    suggestions: List[SuggestionItem]
    message: str


class ChatResponse(BaseModel):
    """Response model cho /chat endpoint"""
    answer: str = Field(..., description="Câu trả lời từ RAG system")
    sources: List[Dict[str, Any]] = Field(..., description="Danh sách sources (file name, page number)")
    query: str = Field(..., description="Câu hỏi gốc")
    error: Optional[str] = Field(None, description="Lỗi nếu có")
    suggestions: Optional[SuggestionsData] = Field(None, description="Suggestions nếu có nhiều kết quả khớp")
    total_sources: Optional[int] = Field(None, description="Tổng số sources")
    no_results: Optional[bool] = Field(False, description="Không tìm thấy kết quả")


class SuggestionsRequest(BaseModel):
    """Request model cho /chat/suggestions endpoint"""
    query: str = Field(..., description="Câu hỏi của user", min_length=1, max_length=1000)
    top_k: Optional[int] = Field(10, description="Số lượng suggestions tối đa", ge=1, le=20)
    similarity_threshold: Optional[float] = Field(0.5, description="Ngưỡng similarity tối thiểu", ge=0.0, le=1.0)
    min_suggestions: Optional[int] = Field(2, description="Số lượng suggestions tối thiểu để hiển thị", ge=1)


class SuggestionsResponse(BaseModel):
    """Response model cho /chat/suggestions endpoint"""
    query: str
    suggestions: List[SuggestionItem]
    total_found: int
    has_multiple_suggestions: bool
    similarity_threshold: float
    message: str
    error: Optional[str] = None


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
    table_name: str
    use_sql_embeddings: bool


# API Endpoints
@app.get("/", tags=["General"])
async def root():
    """Root endpoint"""
    return {
        "message": "RAG System API (SQL Server Vector)",
        "version": "1.0.0",
        "endpoints": {
            "ingest": "POST /ingest - Ingest PDF files into SQL Server",
            "chat": "POST /chat - Chat with RAG system (with suggestions support)",
            "chat_suggestions": "POST /chat/suggestions - Get suggestions for query",
            "health": "GET /health - Health check"
        }
    }


@app.get("/health", tags=["General"], response_model=HealthResponse)
async def health():
    """Health check endpoint"""
    try:
        service = get_rag_service()
        rag_ready = service.is_ready()
        
        return HealthResponse(
            status="OK",
            service="RAG System (SQL Server)",
            rag_ready=rag_ready,
            data_dir=str(service.data_dir),
            table_name=service.table_name,
            use_sql_embeddings=service.use_sql_embeddings
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthResponse(
            status="ERROR",
            service="RAG System (SQL Server)",
            rag_ready=False,
            data_dir=os.getenv("DATA_DIR", "./data"),
            table_name=os.getenv("RAG_TABLE_NAME", "rag_documents"),
            use_sql_embeddings=False
        )


@app.post("/chat/suggestions", tags=["RAG"], response_model=SuggestionsResponse)
async def get_suggestions(request: SuggestionsRequest):
    """
    Suggestions endpoint - Trả về danh sách suggestions khi có nhiều kết quả khớp
    Cho phép user chọn suggestions cụ thể trước khi generate answer
    """
    try:
        logger.info(f"Nhận request suggestions: {request.query}")
        service = get_rag_service()
        
        result = service.search_suggestions(
            query=request.query,
            top_k=request.top_k or 10,
            similarity_threshold=request.similarity_threshold or 0.5,
            min_suggestions=request.min_suggestions or 2
        )
        
        if "error" in result:
            return SuggestionsResponse(
                query=request.query,
                suggestions=[],
                total_found=0,
                has_multiple_suggestions=False,
                similarity_threshold=request.similarity_threshold or 0.5,
                message=result.get("error", ""),
                error=result.get("error")
            )
        
        suggestions = [
            SuggestionItem(**s) for s in result.get("suggestions", [])
        ]
        
        return SuggestionsResponse(
            query=result.get("query", request.query),
            suggestions=suggestions,
            total_found=result.get("total_found", 0),
            has_multiple_suggestions=result.get("has_multiple_suggestions", False),
            similarity_threshold=result.get("similarity_threshold", 0.5),
            message=result.get("message", ""),
            error=None
        )
        
    except ValueError as e:
        logger.error(f"Value error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Lỗi khi xử lý suggestions: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Lỗi khi xử lý: {str(e)}"
        )


@app.post("/ingest", tags=["RAG"], response_model=IngestResponse)
async def ingest_documents():
    """
    Ingest endpoint - Quét toàn bộ PDF trong thư mục data và lưu vào SQL Server với VECTOR type
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
    Sử dụng SQL Server VECTOR_DISTANCE để tìm kiếm semantic
    Hỗ trợ suggestions khi có nhiều kết quả khớp
    """
    try:
        logger.info(f"Nhận query: {request.query}, top_k={request.top_k}, threshold={request.similarity_threshold}")
        service = get_rag_service()
        
        result = service.chat(
            query=request.query,
            top_k=request.top_k or 4,
            similarity_threshold=request.similarity_threshold or 0.5,
            return_suggestions=request.return_suggestions if request.return_suggestions is not None else True,
            selected_suggestion_ids=request.selected_suggestion_ids,
            table_name=request.table_name,
            search_multiple_tables=request.search_multiple_tables or False,
            table_names=request.table_names
        )
        
        if "error" in result:
            return ChatResponse(
                answer=result.get("answer", ""),
                sources=result.get("sources", []),
                query=request.query,
                error=result.get("error"),
                suggestions=None,
                total_sources=0,
                no_results=False
            )
        
        # Convert suggestions dict to SuggestionsData if exists
        suggestions_data = None
        if result.get("suggestions"):
            suggestions_dict = result["suggestions"]
            suggestions_data = SuggestionsData(
                has_suggestions=suggestions_dict.get("has_suggestions", False),
                total_available=suggestions_dict.get("total_available", 0),
                suggestions=[
                    SuggestionItem(**s) for s in suggestions_dict.get("suggestions", [])
                ],
                message=suggestions_dict.get("message", "")
            )
        
        return ChatResponse(
            answer=result.get("answer", ""),
            sources=result.get("sources", []),
            query=result.get("query", request.query),
            error=None,
            suggestions=suggestions_data,
            total_sources=result.get("total_sources", len(result.get("sources", []))),
            no_results=result.get("no_results", False)
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
    logger.info(f"Starting RAG System API (SQL Server Vector) on port {port}...")
    
    uvicorn.run(
        "rag_main_sql:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
