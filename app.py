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
import sys
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
            
            # Check if table has Embedding column và kiểm tra type
            cursor.execute(f"""
                SELECT 
                    COUNT(*) AS HasEmbeddingColumn,
                    TYPE_NAME(system_type_id) AS ColumnType
                FROM sys.columns
                WHERE object_id = OBJECT_ID('dbo.[{table_name}]')
                AND name = 'Embedding'
            """)
            embedding_check = cursor.fetchone()
            has_embedding_column = embedding_check[0] > 0 if embedding_check else False
            embedding_type = embedding_check[1] if embedding_check and embedding_check[1] else None
            
            # Kiểm tra SQL Server version có hỗ trợ VECTOR không
            cursor.execute("SELECT CAST(SERVERPROPERTY('ProductVersion') AS VARCHAR(50))")
            sql_version = cursor.fetchone()[0]
            version_major = int(sql_version.split('.')[0]) if sql_version else 0
            supports_vector = version_major >= 16  # SQL Server 2025+
            
            # Kiểm tra Embedding column có phải VECTOR type không
            is_vector_type = embedding_type and embedding_type.lower() == 'vector'
            can_use_vector_distance = supports_vector and is_vector_type
            
            logger.info(f"SQL Server version: {sql_version} (major: {version_major}), supports VECTOR: {supports_vector}")
            if has_embedding_column:
                logger.info(f"Embedding column type: {embedding_type}, is VECTOR: {is_vector_type}")
                logger.info(f"Can use VECTOR_DISTANCE: {can_use_vector_distance}")
            
            # Nếu không thể dùng VECTOR_DISTANCE, fallback về VectorJson
            if has_embedding_column and not can_use_vector_distance:
                logger.info(f"⚠️ Cannot use VECTOR_DISTANCE (version={version_major}, type={embedding_type}). Falling back to VectorJson method.")
                has_embedding_column = False  # Force fallback to VectorJson
            
            # Check total records
            cursor.execute(f"SELECT COUNT(*) AS TotalRecords FROM dbo.[{table_name}]")
            total_records = cursor.fetchone()[0]
            logger.info(f"Table '{table_name}' has {total_records} total records")
            
            if not has_embedding_column or not can_use_vector_distance:
                # #region agent log
                import json
                try:
                    with open(r'c:\MyData\projects\THITHI\THIHI_AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"H2","location":"app.py:search_vector","message":"Using VectorJson fallback","data":{"has_embedding_column":has_embedding_column,"can_use_vector_distance":can_use_vector_distance,"embedding_type":embedding_type},"timestamp":int(__import__('time').time()*1000)})+'\n')
                except: pass
                # #endregion
                
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
                
                # Use VectorJson fallback - tính cosine similarity trong Python
                # #region agent log
                import json as json_log
                try:
                    with open(r'c:\MyData\projects\THITHI\THIHI_AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json_log.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"H2","location":"app.py:search_vector","message":"Starting VectorJson search","data":{"query_embedding_len":len(query_embedding),"top_n":top_n,"similarity_threshold":similarity_threshold},"timestamp":int(__import__('time').time()*1000)})+'\n')
                except: pass
                # #endregion
                
                cursor.execute(f"""
                    SELECT TOP ({top_n * 4}) ID, Content, VectorJson
                    FROM dbo.[{table_name}]
                    WHERE VectorJson IS NOT NULL
                """)
                
                all_results = []
                dimension_mismatches = 0
                processed_count = 0
                for row in cursor.fetchall():
                    processed_count += 1
                    try:
                        stored_vector = json.loads(row[2]) if row[2] else []
                        if not stored_vector:
                            continue
                        if len(stored_vector) != len(query_embedding):
                            dimension_mismatches += 1
                            logger.debug(f"Dimension mismatch: stored={len(stored_vector)}, query={len(query_embedding)}")
                            continue
                        similarity = cosine_similarity(query_embedding, stored_vector)
                        # #region agent log
                        try:
                            with open(r'c:\MyData\projects\THITHI\THIHI_AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                                f.write(json_log.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"H2","location":"app.py:search_vector","message":"Calculated similarity","data":{"id":row[0],"similarity":similarity,"above_threshold":similarity >= similarity_threshold},"timestamp":int(__import__('time').time()*1000)})+'\n')
                        except: pass
                        # #endregion
                        if similarity >= similarity_threshold:
                            all_results.append({
                                "id": row[0],
                                "content": row[1] or "",
                                "similarity": float(similarity)
                            })
                    except Exception as e:
                        logger.warn(f"Error parsing vector for ID {row[0]}: {e}")
                        continue
                
                # #region agent log
                try:
                    with open(r'c:\MyData\projects\THITHI\THIHI_AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json_log.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"H2","location":"app.py:search_vector","message":"VectorJson search complete","data":{"processed_count":processed_count,"dimension_mismatches":dimension_mismatches,"results_count":len(all_results)},"timestamp":int(__import__('time').time()*1000)})+'\n')
                except: pass
                # #endregion
                
                if dimension_mismatches > 0:
                    logger.warn(f"Found {dimension_mismatches} records with dimension mismatch (stored={len(stored_vector) if stored_vector else 'unknown'}, query={len(query_embedding)})")
                
                # Sort by similarity and take top N
                all_results.sort(key=lambda x: x["similarity"], reverse=True)
                results = all_results[:top_n]
                logger.info(f"Found {len(results)} results after filtering (threshold={similarity_threshold}, checked {len(all_results)} candidates)")
                
            else:
                # #region agent log
                import json as json_log
                try:
                    with open(r'c:\MyData\projects\THITHI\THIHI_AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
                        f.write(json_log.dumps({"sessionId":"debug-session","runId":"run1","hypothesisId":"H3","location":"app.py:search_vector","message":"Using VECTOR_DISTANCE","data":{"embedding_type":embedding_type,"sql_version":sql_version,"version_major":version_major},"timestamp":int(__import__('time').time()*1000)})+'\n')
                except: pass
                # #endregion
                
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
                # Format vector string đúng cách cho SQL Server 2025
                # SQL Server yêu cầu format: [value1,value2,value3,...] 
                # Dùng scientific notation cho số nhỏ/lớn, decimal cho số bình thường
                vector_string = "[" + ",".join(f"{v:.8e}" if abs(v) < 0.0001 or abs(v) > 1000 else f"{v:.8f}" for v in query_embedding) + "]"
                
                # Detect content column name
                cursor.execute(f"""
                    SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{table_name}'
                    AND COLUMN_NAME IN ('Content', 'content', 'Description', 'description', 'Name', 'name')
                """)
                content_col_result = cursor.fetchone()
                content_column = content_col_result[0] if content_col_result else 'Content'
                logger.info(f"Using content column: {content_column}")
                
                # SQL Server 2025 VECTOR_DISTANCE
                # Thử nhiều cách format vector string
                # Cách 1: Dùng DECLARE với format đơn giản (không scientific notation)
                vector_simple = "[" + ",".join(str(v) for v in query_embedding) + "]"
                vector_escaped = vector_simple.replace("'", "''")
                
                # Thử query với format đơn giản trước
                try:
                    try:
                        search_sql = f"""
                            DECLARE @queryVector NVARCHAR(MAX) = '{vector_escaped}';
                            DECLARE @queryVectorTyped VECTOR({EMBEDDING_DIMENSION}) = CAST(@queryVector AS VECTOR({EMBEDDING_DIMENSION}));
                            SELECT TOP ({top_n})
                                ID,
                                [{content_column}] AS Content,
                                (1.0 - VECTOR_DISTANCE(Embedding, @queryVectorTyped, 'COSINE')) AS Similarity
                            FROM dbo.[{table_name}]
                            WHERE Embedding IS NOT NULL
                            ORDER BY VECTOR_DISTANCE(Embedding, @queryVectorTyped, 'COSINE') ASC
                        """
                        cursor.execute(search_sql)
                    except Exception as e1:
                        logger.warning(f"First VECTOR_DISTANCE attempt failed: {e1}")
                        # Thử cách 2: Dùng CAST trực tiếp trong VECTOR_DISTANCE
                        try:
                            search_sql = f"""
                                DECLARE @queryVectorStr NVARCHAR(MAX) = '{vector_escaped}';
                                SELECT TOP ({top_n})
                                    ID,
                                    [{content_column}] AS Content,
                                    (1.0 - VECTOR_DISTANCE(Embedding, CAST(@queryVectorStr AS VECTOR({EMBEDDING_DIMENSION})), 'COSINE')) AS Similarity
                                FROM dbo.[{table_name}]
                                WHERE Embedding IS NOT NULL
                                ORDER BY VECTOR_DISTANCE(Embedding, CAST(@queryVectorStr AS VECTOR({EMBEDDING_DIMENSION})), 'COSINE') ASC
                            """
                            cursor.execute(search_sql)
                        except Exception as e2:
                            logger.warning(f"Second VECTOR_DISTANCE attempt failed: {e2}")
                            # Thử cách 3: Format đơn giản hơn (không scientific notation)
                            try:
                                vector_simple = "[" + ",".join(f"{v:.6f}" for v in query_embedding) + "]"
                                vector_escaped_simple = vector_simple.replace("'", "''")
                                
                                search_sql = f"""
                                    DECLARE @queryVector NVARCHAR(MAX) = '{vector_escaped_simple}';
                                    DECLARE @queryVectorTyped VECTOR({EMBEDDING_DIMENSION}) = CAST(@queryVector AS VECTOR({EMBEDDING_DIMENSION}));
                                    SELECT TOP ({top_n})
                                        ID,
                                        [{content_column}] AS Content,
                                        (1.0 - VECTOR_DISTANCE(Embedding, @queryVectorTyped, 'COSINE')) AS Similarity
                                    FROM dbo.[{table_name}]
                                    WHERE Embedding IS NOT NULL
                                    ORDER BY VECTOR_DISTANCE(Embedding, @queryVectorTyped, 'COSINE') ASC
                                """
                                cursor.execute(search_sql)
                            except Exception as e3:
                                logger.error(f"All VECTOR_DISTANCE attempts failed. Last error: {e3}")
                                logger.error("Falling back to VectorJson method...")
                                # Fallback: Dùng VectorJson nếu có
                                raise e3
                    
                    # Fetch results sau khi execute thành công
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
        
        # Trả về error message chi tiết hơn
        error_message = f"Lỗi khi tìm kiếm: {str(e)}"
        
        # Kiểm tra các lỗi phổ biến
        if "model" in str(e).lower() or "encode" in str(e).lower():
            error_message += " (Lỗi với embedding model)"
        elif "sql" in str(e).lower() or "connection" in str(e).lower():
            error_message += " (Lỗi kết nối SQL Server)"
        elif "table" in str(e).lower():
            error_message += " (Lỗi với bảng database)"
        
        return jsonify({
            "error": error_message,
            "error_type": type(e).__name__,
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
    debug_mode = os.getenv("DEBUG", "true").lower() == "true"
    
    logger.info("=" * 60)
    logger.info("Starting Python Vectorize API")
    logger.info("=" * 60)
    logger.info(f"Port: {port}")
    logger.info(f"Debug mode: {debug_mode}")
    logger.info(f"Model loaded: {model is not None}")
    
    if model is None:
        logger.warning("⚠️ WARNING: Model is not loaded! API may not work correctly.")
        logger.warning("   Check logs above for model loading errors.")
        logger.warning("   Run: python debug_api.py to diagnose")
    else:
        logger.info(f"✅ Model ready: all-mpnet-base-v2 ({EMBEDDING_DIMENSION} dimensions)")
    
    logger.info("=" * 60)
    logger.info(f"API will be available at: http://0.0.0.0:{port}")
    logger.info("=" * 60)
    
    try:
        app.run(host='0.0.0.0', port=port, debug=debug_mode)
    except Exception as e:
        logger.error(f"❌ Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
