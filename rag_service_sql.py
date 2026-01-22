"""
RAG Service với SQL Server 2025 Vector Support
- Load PDF từ thư mục
- Chia nhỏ text thành chunks
- Tạo embeddings và lưu vào SQL Server với VECTOR type
- Tìm kiếm semantic bằng VECTOR_DISTANCE và generate answer với Gemini
"""

import os
from typing import List, Dict, Any, Optional
from pathlib import Path
import pyodbc
import json

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.schema import Document

import logging

logger = logging.getLogger(__name__)


class RAGServiceSQL:
    """RAG Service sử dụng SQL Server 2025 Vector"""
    
    def __init__(
        self,
        connection_string: str,
        data_dir: str = "./data",
        table_name: str = "rag_documents",
        api_key: Optional[str] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 100,
        embedding_dimension: int = 768,
        use_sql_embeddings: bool = False,
        embedding_model_name: str = "local_onnx_embeddings"
    ):
        """
        Khởi tạo RAG Service với SQL Server
        
        Args:
            connection_string: SQL Server connection string
            data_dir: Thư mục chứa file PDF
            table_name: Tên bảng để lưu documents
            api_key: Google Gemini API key (cho LLM, không dùng cho embedding nếu use_sql_embeddings=True)
            chunk_size: Kích thước mỗi chunk (ký tự)
            chunk_overlap: Số ký tự overlap giữa các chunks
            embedding_dimension: Dimension của embedding vector (768 cho all-mpnet-base-v2)
            use_sql_embeddings: Nếu True, dùng AI_GENERATE_EMBEDDINGS của SQL Server. Nếu False, dùng Python API
            embedding_model_name: Tên EXTERNAL MODEL trong SQL Server (nếu use_sql_embeddings=True)
        """
        self.connection_string = connection_string
        self.data_dir = Path(data_dir)
        self.table_name = table_name
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.embedding_dimension = embedding_dimension
        self.use_sql_embeddings = use_sql_embeddings
        self.embedding_model_name = embedding_model_name
        
        # Tạo thư mục nếu chưa tồn tại
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
        # Khởi tạo LLM (chỉ dùng cho generation, không dùng cho embedding)
        # Hỗ trợ cả GOOGLE_API_KEY và GEMINI_API_KEY (Firebase Functions)
        if not api_key:
            api_key = os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        
        if not api_key:
            raise ValueError("Google Gemini API key is required for LLM. Set GOOGLE_API_KEY hoặc GEMINI_API_KEY in .env file hoặc environment variables.")
        
        self.api_key = api_key
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=api_key,
            temperature=0.7
        )
        
        # Python API URL cho embedding (nếu không dùng SQL embeddings)
        self.python_api_url = os.getenv("PYTHON_API_URL", "http://localhost:5005/vectorize")
        
        logger.info(f"RAG Service SQL initialized. Use SQL embeddings: {use_sql_embeddings}")
    
    def _get_connection(self):
        """Lấy SQL Server connection"""
        return pyodbc.connect(self.connection_string)
    
    def _ensure_table_exists(self):
        """Đảm bảo bảng tồn tại với VECTOR column"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Kiểm tra SQL Server version
            cursor.execute("SELECT CAST(SERVERPROPERTY('ProductVersion') AS VARCHAR(50))")
            version = cursor.fetchone()[0]
            version_major = int(version.split('.')[0])
            
            has_vector_support = version_major >= 16  # SQL Server 2025+
            
            # Tạo bảng
            if has_vector_support:
                create_table_sql = f"""
                IF OBJECT_ID('dbo.[{self.table_name}]', 'U') IS NULL
                BEGIN
                    CREATE TABLE dbo.[{self.table_name}] (
                        ID INT IDENTITY(1,1) PRIMARY KEY,
                        Content NVARCHAR(MAX) NOT NULL,
                        VectorJson NVARCHAR(MAX) NULL,
                        Embedding VECTOR({self.embedding_dimension}) NULL,
                        FileName NVARCHAR(500) NULL,
                        PageNumber INT NULL,
                        ChunkIndex INT NULL,
                        CreatedAt DATETIME2 DEFAULT GETDATE()
                    );
                    
                    -- Tạo index trên Embedding để tăng tốc độ search
                    -- CREATE VECTOR INDEX idx_embedding ON dbo.[{self.table_name}] (Embedding) 
                    --   WITH (INDEX_TYPE = HNSW, DISTANCE_FUNCTION = COSINE);
                END
                ELSE
                BEGIN
                    -- Đảm bảo các cột cần thiết tồn tại
                    IF COL_LENGTH('dbo.[{self.table_name}]', 'Embedding') IS NULL
                        ALTER TABLE dbo.[{self.table_name}] ADD Embedding VECTOR({self.embedding_dimension}) NULL;
                    
                    IF COL_LENGTH('dbo.[{self.table_name}]', 'FileName') IS NULL
                        ALTER TABLE dbo.[{self.table_name}] ADD FileName NVARCHAR(500) NULL;
                    
                    IF COL_LENGTH('dbo.[{self.table_name}]', 'PageNumber') IS NULL
                        ALTER TABLE dbo.[{self.table_name}] ADD PageNumber INT NULL;
                    
                    IF COL_LENGTH('dbo.[{self.table_name}]', 'ChunkIndex') IS NULL
                        ALTER TABLE dbo.[{self.table_name}] ADD ChunkIndex INT NULL;
                END
                """
            else:
                # SQL Server cũ hơn - chỉ dùng VectorJson
                create_table_sql = f"""
                IF OBJECT_ID('dbo.[{self.table_name}]', 'U') IS NULL
                BEGIN
                    CREATE TABLE dbo.[{self.table_name}] (
                        ID INT IDENTITY(1,1) PRIMARY KEY,
                        Content NVARCHAR(MAX) NOT NULL,
                        VectorJson NVARCHAR(MAX) NULL,
                        FileName NVARCHAR(500) NULL,
                        PageNumber INT NULL,
                        ChunkIndex INT NULL,
                        CreatedAt DATETIME2 DEFAULT GETDATE()
                    );
                END
                """
            
            cursor.execute(create_table_sql)
            conn.commit()
            logger.info(f"Table {self.table_name} đã được tạo/kiểm tra")
    
    def _generate_embeddings_sql(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings sử dụng SQL Server AI_GENERATE_EMBEDDINGS"""
        if not texts:
            return []
        
        embeddings = []
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Process từng text
            for text in texts:
                try:
                    # Sử dụng AI_GENERATE_EMBEDDINGS
                    sql = f"""
                    SELECT CONVERT(NVARCHAR(MAX), AI_GENERATE_EMBEDDINGS(@text USE MODEL {self.embedding_model_name}))
                    """
                    cursor.execute(sql, (text,))
                    result = cursor.fetchone()
                    
                    if result and result[0]:
                        # Parse JSON string thành list
                        embedding_json = result[0]
                        embedding = json.loads(embedding_json)
                        embeddings.append(embedding)
                    else:
                        logger.warning(f"Không thể generate embedding cho text: {text[:50]}...")
                        embeddings.append([])
                        
                except Exception as e:
                    logger.error(f"Lỗi khi generate embedding: {e}")
                    embeddings.append([])
        
        return embeddings
    
    def _generate_embeddings_python(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings sử dụng Python API"""
        import requests
        
        try:
            response = requests.post(
                self.python_api_url,
                json={"texts": texts},
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get("vectors", [])
            
        except Exception as e:
            logger.error(f"Lỗi khi gọi Python API: {e}")
            return [[] for _ in texts]
    
    def ingest_documents(self) -> Dict[str, Any]:
        """
        Quét toàn bộ PDF trong data_dir, chia nhỏ và lưu vào SQL Server
        
        Returns:
            Dict chứa thông tin về quá trình ingest
        """
        logger.info(f"Bắt đầu ingest documents từ {self.data_dir}")
        
        # Đảm bảo bảng tồn tại
        self._ensure_table_exists()
        
        # Kiểm tra thư mục data
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Thư mục {self.data_dir} không tồn tại")
        
        # Load PDF files
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
        
        # Tạo metadata cho mỗi chunk
        texts = []
        metadata_list = []
        
        for chunk in chunks:
            texts.append(chunk.page_content)
            
            source = chunk.metadata.get("source", "")
            page = chunk.metadata.get("page", 0)
            file_name = Path(source).name if source else "unknown"
            
            metadata_list.append({
                "file_name": file_name,
                "page_number": page,
                "chunk_index": len(texts) - 1
            })
        
        # Generate embeddings
        logger.info(f"Đang generate embeddings cho {len(texts)} chunks...")
        if self.use_sql_embeddings:
            embeddings = self._generate_embeddings_sql(texts)
        else:
            embeddings = self._generate_embeddings_python(texts)
        
        logger.info(f"Đã generate {len(embeddings)} embeddings")
        
        # Lưu vào SQL Server
        logger.info(f"Đang lưu {len(chunks)} chunks vào SQL Server...")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Kiểm tra xem có VECTOR column không
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM sys.columns 
                WHERE object_id = OBJECT_ID('dbo.[{self.table_name}]') 
                AND name = 'Embedding'
            """)
            has_vector_column = cursor.fetchone()[0] > 0
            
            inserted_count = 0
            
            for i, (text, embedding, metadata) in enumerate(zip(texts, embeddings, metadata_list)):
                if not text.strip():
                    continue
                
                # Serialize embedding
                embedding_json = json.dumps(embedding) if embedding else None
                
                # Format vector string cho SQL Server
                if has_vector_column and embedding:
                    vector_string = "[" + ",".join(str(v) for v in embedding) + "]"
                else:
                    vector_string = None
                
                try:
                    if has_vector_column and vector_string:
                        # Insert với VECTOR column
                        sql = f"""
                        INSERT INTO dbo.[{self.table_name}] 
                        (Content, VectorJson, Embedding, FileName, PageNumber, ChunkIndex)
                        VALUES (?, ?, CAST(? AS VECTOR({self.embedding_dimension})), ?, ?, ?)
                        """
                        cursor.execute(sql, (
                            text,
                            embedding_json,
                            vector_string,
                            metadata["file_name"],
                            metadata["page_number"],
                            metadata["chunk_index"]
                        ))
                    else:
                        # Insert chỉ với VectorJson
                        sql = f"""
                        INSERT INTO dbo.[{self.table_name}] 
                        (Content, VectorJson, FileName, PageNumber, ChunkIndex)
                        VALUES (?, ?, ?, ?, ?)
                        """
                        cursor.execute(sql, (
                            text,
                            embedding_json,
                            metadata["file_name"],
                            metadata["page_number"],
                            metadata["chunk_index"]
                        ))
                    
                    inserted_count += 1
                    
                    if (i + 1) % 50 == 0:
                        logger.info(f"Đã insert {i + 1}/{len(texts)} chunks")
                        conn.commit()
                        
                except Exception as e:
                    logger.error(f"Lỗi khi insert chunk {i}: {e}")
                    continue
            
            conn.commit()
            logger.info(f"Đã insert {inserted_count} chunks vào SQL Server")
        
        file_names = set(m["file_name"] for m in metadata_list)
        
        return {
            "status": "success",
            "message": f"Đã ingest thành công {inserted_count} chunks từ {len(file_names)} files",
            "total_documents": len(documents),
            "total_chunks": inserted_count,
            "total_files": len(file_names),
            "files": list(file_names)
        }
    
    def search_suggestions(
        self, 
        query: str, 
        top_k: int = 10, 
        similarity_threshold: float = 0.5,
        min_suggestions: int = 2
    ) -> Dict[str, Any]:
        """
        Tìm kiếm và trả về danh sách suggestions (gợi ý) khi có nhiều kết quả khớp
        
        Args:
            query: Câu hỏi của user
            top_k: Số lượng kết quả tối đa để lấy
            similarity_threshold: Ngưỡng similarity tối thiểu (0.0 - 1.0)
            min_suggestions: Số lượng suggestions tối thiểu để hiển thị
            
        Returns:
            Dict chứa suggestions và metadata
        """
        logger.info(f"Tìm kiếm suggestions cho query: {query}")
        
        # Bước 1: Generate embedding cho query
        if self.use_sql_embeddings:
            query_embeddings = self._generate_embeddings_sql([query])
            query_vector = query_embeddings[0] if query_embeddings else []
        else:
            query_embeddings = self._generate_embeddings_python([query])
            query_vector = query_embeddings[0] if query_embeddings else []
        
        if not query_vector:
            return {
                "error": "Không thể generate embedding cho query",
                "suggestions": [],
                "total_found": 0
            }
        
        # Bước 2: Tìm kiếm trong SQL Server
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Kiểm tra có VECTOR column không
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM sys.columns 
                WHERE object_id = OBJECT_ID('dbo.[{self.table_name}]') 
                AND name = 'Embedding'
            """)
            has_vector_column = cursor.fetchone()[0] > 0
            
            # Format query vector
            vector_string = "[" + ",".join(str(v) for v in query_vector) + "]"
            
            all_results = []
            
            if has_vector_column:
                # Sử dụng VECTOR_DISTANCE - lấy nhiều kết quả hơn để filter
                sql = f"""
                SELECT TOP ({top_k * 2})
                    ID,
                    Content,
                    FileName,
                    PageNumber,
                    ChunkIndex,
                    (1.0 - VECTOR_DISTANCE(Embedding, CAST(? AS VECTOR({self.embedding_dimension})), COSINE)) AS Similarity
                FROM dbo.[{self.table_name}]
                WHERE Embedding IS NOT NULL
                ORDER BY VECTOR_DISTANCE(Embedding, CAST(? AS VECTOR({self.embedding_dimension})), COSINE) ASC
                """
                cursor.execute(sql, (vector_string, vector_string))
                
                for row in cursor.fetchall():
                    similarity = float(row[5]) if row[5] else 0.0
                    if similarity >= similarity_threshold:
                        all_results.append({
                            "id": row[0],
                            "content": row[1],
                            "file_name": row[2] or "unknown",
                            "page_number": row[3] or 0,
                            "chunk_index": row[4] or 0,
                            "similarity": similarity
                        })
            else:
                # Fallback: Tính cosine similarity trong Python
                cursor.execute(f"""
                    SELECT ID, Content, VectorJson, FileName, PageNumber, ChunkIndex
                    FROM dbo.[{self.table_name}]
                    WHERE VectorJson IS NOT NULL
                """)
                
                for row in cursor.fetchall():
                    try:
                        vector = json.loads(row[2]) if row[2] else []
                        if vector:
                            similarity = self._cosine_similarity(query_vector, vector)
                            if similarity >= similarity_threshold:
                                all_results.append({
                                    "id": row[0],
                                    "content": row[1],
                                    "file_name": row[3] or "unknown",
                                    "page_number": row[4] or 0,
                                    "chunk_index": row[5] or 0,
                                    "similarity": similarity
                                })
                    except:
                        continue
                
                # Sort theo similarity
                all_results.sort(key=lambda x: x["similarity"], reverse=True)
                all_results = all_results[:top_k]
        
        # Tạo suggestions
        suggestions = []
        for i, result in enumerate(all_results, 1):
            content_preview = result["content"][:300] + "..." if len(result["content"]) > 300 else result["content"]
            suggestions.append({
                "index": i,
                "id": result["id"],
                "content": result["content"],
                "content_preview": content_preview,
                "file_name": result["file_name"],
                "page_number": result["page_number"] + 1,
                "similarity": round(result["similarity"], 4),
                "similarity_percent": round(result["similarity"] * 100, 2)
            })
        
        # Kiểm tra xem có đủ suggestions không
        has_multiple_suggestions = len(suggestions) >= min_suggestions
        
        return {
            "query": query,
            "suggestions": suggestions,
            "total_found": len(suggestions),
            "has_multiple_suggestions": has_multiple_suggestions,
            "similarity_threshold": similarity_threshold,
            "message": f"Tìm thấy {len(suggestions)} kết quả khớp" if suggestions else "Không tìm thấy kết quả nào"
        }
    
    def chat(
        self, 
        query: str, 
        top_k: int = 4, 
        similarity_threshold: float = 0.5,
        return_suggestions: bool = True,
        selected_suggestion_ids: Optional[List[int]] = None,
        table_name: Optional[str] = None,
        search_multiple_tables: bool = False,
        table_names: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Nhận query từ user, tìm kiếm và generate answer
        
        Args:
            query: Câu hỏi của user
            top_k: Số lượng chunks liên quan nhất để lấy
            similarity_threshold: Ngưỡng similarity tối thiểu (0.0 - 1.0)
            return_suggestions: Nếu True, trả về suggestions khi có nhiều kết quả khớp
            selected_suggestion_ids: Danh sách ID của suggestions được chọn (nếu có)
            table_name: Tên bảng cụ thể để tìm (nếu None, dùng self.table_name)
            search_multiple_tables: Nếu True, tìm trong nhiều bảng
            table_names: Danh sách tên bảng để tìm (nếu search_multiple_tables=True)
            
        Returns:
            Dict chứa answer, sources, và suggestions (nếu có)
        """
        # Xác định bảng để tìm
        if table_name:
            search_table = table_name
        elif search_multiple_tables and table_names:
            # Tìm trong nhiều bảng, gộp kết quả
            return self._chat_multiple_tables(
                query=query,
                table_names=table_names,
                top_k=top_k,
                similarity_threshold=similarity_threshold,
                return_suggestions=return_suggestions,
                selected_suggestion_ids=selected_suggestion_ids
            )
        else:
            search_table = self.table_name
        
        logger.info(f"Nhận query: {query}, tìm trong bảng: {search_table}")
        
        # Bước 1: Generate embedding cho query
        if self.use_sql_embeddings:
            query_embeddings = self._generate_embeddings_sql([query])
            query_vector = query_embeddings[0] if query_embeddings else []
        else:
            query_embeddings = self._generate_embeddings_python([query])
            query_vector = query_embeddings[0] if query_embeddings else []
        
        if not query_vector:
            return {
                "error": "Không thể generate embedding cho query",
                "answer": None,
                "sources": [],
                "suggestions": []
            }
        
        # Bước 2: Tìm kiếm trong SQL Server
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Kiểm tra bảng có tồn tại không
            try:
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{search_table}'
                """)
                table_exists = cursor.fetchone()[0] > 0
            except Exception as e:
                logger.error(f"Lỗi khi kiểm tra bảng: {e}")
                table_exists = False
            
            if not table_exists:
                return {
                    "error": f"Bảng '{search_table}' không tồn tại trong database",
                    "answer": f"Tôi không tìm thấy bảng '{search_table}' trong database. Vui lòng kiểm tra lại tên bảng.",
                    "sources": [],
                    "query": query,
                    "suggestions": None,
                    "no_results": True
                }
            
            # Kiểm tra có VECTOR column không
            try:
                cursor.execute(f"""
                    SELECT COUNT(*) 
                    FROM sys.columns 
                    WHERE object_id = OBJECT_ID('dbo.[{search_table}]') 
                    AND name = 'Embedding'
                """)
                has_vector_column = cursor.fetchone()[0] > 0
            except Exception as e:
                logger.warning(f"Lỗi khi kiểm tra VECTOR column: {e}")
                has_vector_column = False
            
            # Format query vector
            vector_string = "[" + ",".join(str(v) for v in query_vector) + "]"
            
            # Nếu có selected_suggestion_ids, chỉ lấy những kết quả đó
            if selected_suggestion_ids and len(selected_suggestion_ids) > 0 and has_vector_column:
                    # Lấy kết quả theo IDs đã chọn
                    placeholders = ",".join("?" for _ in selected_suggestion_ids)
                    sql = f"""
                    SELECT 
                        ID,
                        Content,
                        FileName,
                        PageNumber,
                        ChunkIndex,
                        (1.0 - VECTOR_DISTANCE(Embedding, CAST(? AS VECTOR({self.embedding_dimension})), COSINE)) AS Similarity
                    FROM dbo.[{search_table}]
                    WHERE Embedding IS NOT NULL AND ID IN ({placeholders})
                    ORDER BY VECTOR_DISTANCE(Embedding, CAST(? AS VECTOR({self.embedding_dimension})), COSINE) ASC
                    """
                    cursor.execute(sql, (vector_string, *selected_suggestion_ids, vector_string))
            elif has_vector_column:
                # Sử dụng VECTOR_DISTANCE - lấy nhiều hơn để check suggestions
                sql = f"""
                SELECT TOP ({top_k * 2})
                    ID,
                    Content,
                    FileName,
                    PageNumber,
                    ChunkIndex,
                    (1.0 - VECTOR_DISTANCE(Embedding, CAST(? AS VECTOR({self.embedding_dimension})), COSINE)) AS Similarity
                FROM dbo.[{search_table}]
                WHERE Embedding IS NOT NULL
                ORDER BY VECTOR_DISTANCE(Embedding, CAST(? AS VECTOR({self.embedding_dimension})), COSINE) ASC
                """
                cursor.execute(sql, (vector_string, vector_string))
            else:
                # Fallback: Tính cosine similarity trong Python
                # Lấy tất cả vectors và tính similarity
                cursor.execute(f"""
                    SELECT ID, Content, VectorJson, FileName, PageNumber, ChunkIndex
                    FROM dbo.[{search_table}]
                    WHERE VectorJson IS NOT NULL
                """)
                
                all_fetched_results = []
                for row in cursor.fetchall():
                    try:
                        vector = json.loads(row[2]) if row[2] else []
                        if vector:
                            similarity = self._cosine_similarity(query_vector, vector)
                            all_fetched_results.append({
                                "id": row[0],
                                "content": row[1],
                                "file_name": row[3] or "unknown",
                                "page_number": row[4] or 0,
                                "chunk_index": row[5] or 0,
                                "similarity": similarity
                            })
                    except:
                        continue
                
                # Filter theo similarity threshold và sort
                filtered_results = [r for r in all_fetched_results if r["similarity"] >= similarity_threshold]
                filtered_results.sort(key=lambda x: x["similarity"], reverse=True)
                
                # Nếu có selected_suggestion_ids, chỉ lấy những kết quả đó
                if selected_suggestion_ids and len(selected_suggestion_ids) > 0:
                    results = [r for r in filtered_results if r["id"] in selected_suggestion_ids]
                else:
                    results = filtered_results[:top_k]
                
                # Kiểm tra xem có nhiều kết quả khớp không (để trả về suggestions)
                has_multiple_matches = len(filtered_results) >= 3
                suggestions_data = None
                
                if return_suggestions and has_multiple_matches and not selected_suggestion_ids:
                    # Tạo suggestions từ các kết quả tìm được
                    suggestions_list = []
                    for i, result in enumerate(filtered_results[:10], 1):  # Tối đa 10 suggestions
                        content_preview = result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"]
                        suggestions_list.append({
                            "index": i,
                            "id": result["id"],
                            "content_preview": content_preview,
                            "file_name": result["file_name"],
                            "page_number": result["page_number"] + 1,
                            "similarity": round(result["similarity"], 4),
                            "similarity_percent": round(result["similarity"] * 100, 2)
                        })
                    
                    suggestions_data = {
                        "has_suggestions": True,
                        "total_available": len(filtered_results),
                        "suggestions": suggestions_list,
                        "message": f"Tìm thấy {len(filtered_results)} kết quả khớp. Bạn có thể chọn các kết quả cụ thể để xem chi tiết."
                    }
                
                # Generate answer với context
                if not results:
                    return {
                        "answer": "Tôi không tìm thấy thông tin liên quan đến câu hỏi của bạn trong tài liệu.",
                        "sources": [],
                        "query": query,
                        "suggestions": suggestions_data,
                        "no_results": True
                    }
                
                context = "\n\n".join([f"[{r['file_name']}, trang {r['page_number']+1}]: {r['content']}" 
                                      for r in results])
                
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
                
                chain = PROMPT | self.llm
                answer = chain.invoke({"context": context, "question": query})
                
                sources = [{
                    "id": r["id"],
                    "file_name": r["file_name"],
                    "page_number": r["page_number"] + 1,
                    "content_preview": r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"],
                    "similarity": round(r["similarity"], 4)
                } for r in results]
                
                return {
                    "answer": answer.content if hasattr(answer, 'content') else str(answer),
                    "sources": sources,
                    "query": query,
                    "suggestions": suggestions_data,
                    "total_sources": len(sources)
                }
            
            # Nếu có VECTOR column, dùng kết quả từ SQL
            all_fetched_results = []
            try:
                for row in cursor.fetchall():
                    if len(row) < 6:
                        continue
                    similarity = float(row[5]) if row[5] is not None else 0.0
                    all_fetched_results.append({
                        "id": row[0],
                        "content": row[1] or "",
                        "file_name": row[2] or "unknown",
                        "page_number": row[3] or 0,
                        "chunk_index": row[4] or 0,
                        "similarity": similarity
                    })
            except Exception as e:
                logger.error(f"Lỗi khi xử lý kết quả từ SQL: {e}")
                all_fetched_results = []
            
            # Filter theo similarity threshold và lấy top_k
            filtered_results = [r for r in all_fetched_results if r["similarity"] >= similarity_threshold]
            filtered_results.sort(key=lambda x: x["similarity"], reverse=True)
            results = filtered_results[:top_k]
            
            # Kiểm tra xem có nhiều kết quả khớp không (để trả về suggestions)
            has_multiple_matches = len(filtered_results) >= 3  # Có ít nhất 3 kết quả khớp
            suggestions_data = None
            
            if return_suggestions and has_multiple_matches and not selected_suggestion_ids:
                # Tạo suggestions từ các kết quả tìm được
                suggestions_list = []
                for i, result in enumerate(filtered_results[:10], 1):  # Tối đa 10 suggestions
                    content_preview = result["content"][:200] + "..." if len(result["content"]) > 200 else result["content"]
                    suggestions_list.append({
                        "index": i,
                        "id": result["id"],
                        "content_preview": content_preview,
                        "file_name": result["file_name"],
                        "page_number": result["page_number"] + 1,
                        "similarity": round(result["similarity"], 4),
                        "similarity_percent": round(result["similarity"] * 100, 2)
                    })
                
                suggestions_data = {
                    "has_suggestions": True,
                    "total_available": len(filtered_results),
                    "suggestions": suggestions_list,
                    "message": f"Tìm thấy {len(filtered_results)} kết quả khớp. Bạn có thể chọn các kết quả cụ thể để xem chi tiết."
                }
        
        # Bước 3: Generate answer với context
        if not results:
            return {
                "answer": "Tôi không tìm thấy thông tin liên quan đến câu hỏi của bạn trong tài liệu.",
                "sources": [],
                "query": query,
                "suggestions": suggestions_data,
                "no_results": True
            }
        
        context = "\n\n".join([f"[{r['file_name']}, trang {r['page_number']+1}]: {r['content']}" 
                              for r in results])
        
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
        
        chain = PROMPT | self.llm
        answer = chain.invoke({"context": context, "question": query})
        
        sources = [{
            "id": r["id"],
            "file_name": r["file_name"],
            "page_number": r["page_number"] + 1,
            "content_preview": r["content"][:200] + "..." if len(r["content"]) > 200 else r["content"],
            "similarity": round(r["similarity"], 4)
        } for r in results]
        
        return {
            "answer": answer.content if hasattr(answer, 'content') else str(answer),
            "sources": sources,
            "query": query,
            "suggestions": suggestions_data,
            "total_sources": len(sources)
        }
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Tính cosine similarity giữa 2 vectors"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    def is_ready(self) -> bool:
        """Kiểm tra xem RAG service đã sẵn sàng chưa"""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"SELECT COUNT(*) FROM dbo.[{self.table_name}]")
                count = cursor.fetchone()[0]
                return count > 0
        except:
            return False
