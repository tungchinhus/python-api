"""
Python API Server để vectorize text và search trong SQL Server
Endpoints:
- POST /vectorize: Vectorize text thành embeddings
- POST /api/search/vector: Tìm kiếm trong SQL Server với vector similarity
- GET /api/search/health: Health check cho search endpoint
- GET /health: Health check cho vectorize endpoint
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
from sentence_transformers import SentenceTransformer
import logging
import pyodbc
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Cho phép CORS từ .NET backend

# Load model embedding (sẽ download lần đầu nếu chưa có)
# Model này hỗ trợ tiếng Việt tốt và tạo embeddings 768 chiều
try:
    logger.info("Đang load model embedding...")
    model = SentenceTransformer('all-mpnet-base-v2')
    logger.info("Model đã load thành công! (768 dimensions)")
except Exception as e:
    logger.error(f"Lỗi khi load model: {e}")
    model = None

# SQL Server connection configuration
EMBEDDING_DIMENSION = 768  # all-mpnet-base-v2 produces 768-dimensional vectors

def get_sql_connection():
    """Get SQL Server connection"""
    connection_string = os.getenv("SQL_CONNECTION_STRING")
    if not connection_string:
        # Build from individual settings
        server = os.getenv("SQL_SERVER", "localhost")
        database = os.getenv("SQL_DATABASE", "THITHI_AI")
        trusted_connection = os.getenv("SQL_TRUSTED_CONNECTION", "yes")
        
        if trusted_connection.lower() == "yes":
            connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;"
        else:
            username = os.getenv("SQL_USERNAME")
            password = os.getenv("SQL_PASSWORD")
            connection_string = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
    
    return pyodbc.connect(connection_string)

def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    if len(vec1) != len(vec2):
        return 0.0
    
    dot_product = sum(a * b for a, b in zip(vec1, vec2))
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5
    
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0
    
    return dot_product / (magnitude1 * magnitude2)

@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        "status": "OK",
        "service": "Python Vectorize API",
        "model_loaded": model is not None
    })

@app.route('/vectorize', methods=['POST'])
def vectorize():
    """
    Vectorize text thành embeddings
    
    Request body:
    {
        "texts": ["Máy Bơm - Model X - Công suất 5HP", "Máy Nén - Model Y"]
    }
    
    Response:
    {
        "vectors": [[0.1, 0.2, ...], [0.3, 0.4, ...]]
    }
    """
    try:
        # Kiểm tra model đã load chưa
        if model is None:
            return jsonify({
                "error": "Model chưa được load. Vui lòng kiểm tra logs."
            }), 500
        
        # Parse request body
        data = request.get_json()
        if not data or 'texts' not in data:
            return jsonify({
                "error": "Request body phải chứa 'texts' (array of strings)"
            }), 400
        
        texts = data['texts']
        if not isinstance(texts, list) or len(texts) == 0:
            return jsonify({
                "error": "'texts' phải là một array không rỗng"
            }), 400
        
        logger.info(f"Nhận {len(texts)} texts để vectorize")
        
        # Vectorize tất cả texts
        embeddings = model.encode(texts, convert_to_numpy=True)
        
        # Convert numpy array thành list of lists
        vectors = embeddings.tolist()
        
        logger.info(f"Đã vectorize thành công {len(vectors)} vectors, dimension: {len(vectors[0]) if vectors else 0}")
        
        return jsonify({
            "vectors": vectors,
            "count": len(vectors),
            "dimension": len(vectors[0]) if vectors else 0
        })
        
    except Exception as e:
        logger.error(f"Lỗi khi vectorize: {e}", exc_info=True)
        return jsonify({
            "error": f"Lỗi khi xử lý: {str(e)}"
        }), 500

@app.route('/api/search/vector', methods=['POST'])
def search_vector():
    """
    Tìm kiếm trong SQL Server với vector similarity
    
    Request body:
    {
        "query": "Máy bơm công suất 5HP",
        "tableName": "TSMay",
        "topN": 10,
        "similarityThreshold": 0.3
    }
    
    Response:
    {
        "query": "Máy bơm công suất 5HP",
        "tableName": "TSMay",
        "totalResults": 5,
        "results": [
            {
                "id": 1,
                "content": "...",
                "similarity": 0.85
            }
        ]
    }
    """
    try:
        logger.info(f"📥 Received POST /api/search/vector request")
        if model is None:
            return jsonify({
                "error": "Model chưa được load. Vui lòng kiểm tra logs."
            }), 500
        
        # Parse request body
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({
                "error": "Request body phải chứa 'query' (string)"
            }), 400
        
        query = data.get('query', '')
        table_name = data.get('tableName', 'TSMay')
        top_n = data.get('topN', 10)
        similarity_threshold = data.get('similarityThreshold', 0.3)
        
        if not query or not isinstance(query, str):
            return jsonify({
                "error": "'query' phải là một string không rỗng"
            }), 400
        
        logger.info(f"🔍 Vector search request: query='{query[:50]}...', table={table_name}, topN={top_n}")
        
        # Generate embedding for query
        query_embedding = model.encode([query], convert_to_numpy=True)[0].tolist()
        logger.info(f"✅ Query embedding generated: {len(query_embedding)} dimensions")
        
        # Connect to SQL Server
        try:
            conn = get_sql_connection()
            cursor = conn.cursor()
        except Exception as sql_error:
            logger.error(f"❌ SQL connection error: {sql_error}")
            return jsonify({
                "error": f"Không thể kết nối đến SQL Server: {str(sql_error)}"
            }), 500
        
        try:
            # Check if table exists
            cursor.execute(f"""
                SELECT COUNT(*) AS TableExists
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{table_name}'
            """)
            table_exists = cursor.fetchone()[0] > 0
            
            if not table_exists:
                logger.error(f"Table '{table_name}' does not exist")
                return jsonify({
                    "error": f"Bảng '{table_name}' không tồn tại trong database."
                }), 400
            
            # Check if table has Embedding column
            cursor.execute(f"""
                SELECT COUNT(*) AS HasEmbeddingColumn
                FROM sys.columns
                WHERE object_id = OBJECT_ID('dbo.[{table_name}]')
                AND name = 'Embedding'
            """)
            has_embedding_column = cursor.fetchone()[0] > 0
            
            # Check total records
            cursor.execute(f"SELECT COUNT(*) AS TotalRecords FROM dbo.[{table_name}]")
            total_records = cursor.fetchone()[0]
            logger.info(f"Table '{table_name}' has {total_records} total records")
            
            if not has_embedding_column:
                # Check for VectorJson column
                cursor.execute(f"""
                    SELECT COUNT(*) AS HasVectorJsonColumn
                    FROM sys.columns
                    WHERE object_id = OBJECT_ID('dbo.[{table_name}]')
                    AND name = 'VectorJson'
                """)
                has_vector_json = cursor.fetchone()[0] > 0
                
                if not has_vector_json:
                    logger.error(f"Table '{table_name}' has no Embedding or VectorJson column")
                    return jsonify({
                        "error": f"Bảng '{table_name}' không có cột Embedding hoặc VectorJson. Vui lòng kiểm tra lại.",
                        "totalRecords": total_records
                    }), 400
                
                # Check records with VectorJson
                cursor.execute(f"""
                    SELECT COUNT(*) AS Count
                    FROM dbo.[{table_name}]
                    WHERE VectorJson IS NOT NULL
                """)
                records_with_vectorjson = cursor.fetchone()[0]
                logger.info(f"Found {records_with_vectorjson} records with VectorJson")
                
                if records_with_vectorjson == 0:
                    logger.warn(f"No records with VectorJson in table '{table_name}'")
                    return jsonify({
                        "query": query,
                        "tableName": table_name,
                        "totalResults": 0,
                        "results": [],
                        "warning": f"Bảng '{table_name}' có {total_records} bản ghi nhưng không có VectorJson. Cần re-ingest dữ liệu với embeddings."
                    }), 200
                
                # Use VectorJson fallback
                cursor.execute(f"""
                    SELECT TOP ({top_n * 4}) ID, Content, VectorJson
                    FROM dbo.[{table_name}]
                    WHERE VectorJson IS NOT NULL
                """)
                
                all_results = []
                dimension_mismatches = 0
                for row in cursor.fetchall():
                    try:
                        stored_vector = json.loads(row[2]) if row[2] else []
                        if not stored_vector:
                            continue
                        if len(stored_vector) != len(query_embedding):
                            dimension_mismatches += 1
                            logger.debug(f"Dimension mismatch: stored={len(stored_vector)}, query={len(query_embedding)}")
                            continue
                        similarity = cosine_similarity(query_embedding, stored_vector)
                        if similarity >= similarity_threshold:
                            all_results.append({
                                "id": row[0],
                                "content": row[1] or "",
                                "similarity": float(similarity)
                            })
                    except Exception as e:
                        logger.warn(f"Error parsing vector for ID {row[0]}: {e}")
                        continue
                
                if dimension_mismatches > 0:
                    logger.warn(f"Found {dimension_mismatches} records with dimension mismatch (stored={len(stored_vector) if stored_vector else 'unknown'}, query={len(query_embedding)})")
                
                # Sort by similarity and take top N
                all_results.sort(key=lambda x: x["similarity"], reverse=True)
                results = all_results[:top_n]
                logger.info(f"Found {len(results)} results after filtering (threshold={similarity_threshold}, checked {len(all_results)} candidates)")
                
            else:
                # Check records with Embedding
                cursor.execute(f"""
                    SELECT COUNT(*) AS Count
                    FROM dbo.[{table_name}]
                    WHERE Embedding IS NOT NULL
                """)
                records_with_embedding = cursor.fetchone()[0]
                logger.info(f"Found {records_with_embedding} records with Embedding column")
                
                if records_with_embedding == 0:
                    logger.warn(f"No records with Embedding in table '{table_name}'")
                    return jsonify({
                        "query": query,
                        "tableName": table_name,
                        "totalResults": 0,
                        "results": [],
                        "warning": f"Bảng '{table_name}' có {total_records} bản ghi nhưng không có Embedding. Cần re-ingest dữ liệu với embeddings."
                    }), 200
                
                # Use VECTOR_DISTANCE
                vector_string = "[" + ",".join(str(v) for v in query_embedding) + "]"
                
                # Detect content column name
                cursor.execute(f"""
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{table_name}'
                    AND COLUMN_NAME IN ('Content', 'content', 'Description', 'description', 'Name', 'name')
                """)
                content_col_result = cursor.fetchone()
                content_column = content_col_result[0] if content_col_result else 'Content'
                logger.info(f"Using content column: {content_column}")
                
                # SQL Server doesn't support parameterized queries with VECTOR type
                # Embed vector string directly (safe - not user input, generated from AI)
                search_sql = f"""
                    SELECT TOP ({top_n})
                        ID,
                        [{content_column}] AS Content,
                        (1.0 - VECTOR_DISTANCE(Embedding, CAST('{vector_string}' AS VECTOR({EMBEDDING_DIMENSION})), 'COSINE')) AS Similarity
                    FROM dbo.[{table_name}]
                    WHERE Embedding IS NOT NULL
                    ORDER BY VECTOR_DISTANCE(Embedding, CAST('{vector_string}' AS VECTOR({EMBEDDING_DIMENSION})), 'COSINE') ASC
                """
                
                try:
                    cursor.execute(search_sql)
                    raw_results = cursor.fetchall()
                    logger.info(f"SQL query returned {len(raw_results)} raw results")
                    
                    results = []
                    for row in raw_results:
                        similarity = float(row[2]) if row[2] else 0.0
                        logger.debug(f"Result ID={row[0]}, similarity={similarity:.4f}, threshold={similarity_threshold}")
                        if similarity >= similarity_threshold:
                            results.append({
                                "id": int(row[0]),
                                "content": str(row[1]) if row[1] else "",
                                "similarity": similarity
                            })
                    logger.info(f"Filtered to {len(results)} results above threshold {similarity_threshold}")
                except Exception as sql_error:
                    logger.error(f"SQL query error: {sql_error}")
                    raise
            
            logger.info(f"✅ Found {len(results)} results (threshold={similarity_threshold})")
            
            return jsonify({
                "query": query,
                "tableName": table_name,
                "totalResults": len(results),
                "results": results
            })
            
        finally:
            conn.close()
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"❌ Error in vector search: {e}")
        logger.error(f"❌ Traceback: {error_trace}")
        return jsonify({
            "error": f"Lỗi khi tìm kiếm: {str(e)}",
            "details": error_trace if os.getenv("DEBUG", "false").lower() == "true" else None
        }), 500

@app.route('/api/search/health', methods=['GET'])
def search_health():
    """Health check for search endpoint"""
    return jsonify({
        "status": "OK",
        "service": "Vector Search API",
        "model_loaded": model is not None,
        "embedding_dimension": EMBEDDING_DIMENSION if model else None
    })

if __name__ == '__main__':
    # Chạy server trên port 5005 (tránh trùng với .NET backend 5000)
    port = int(os.getenv("PORT", "5005"))
    logger.info(f"Starting Python Vectorize API on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
