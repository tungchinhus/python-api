"""
Script để đọc file Excel và lưu vào SQL Server 2025 với vector embeddings
- Tự động phát hiện cột ngữ nghĩa (text) và cột số (numeric)
- Tạo vector embeddings cho dữ liệu ngữ nghĩa
- Lưu cả dữ liệu gốc và vector vào SQL Server
"""

import os
import sys
import pandas as pd
import pyodbc
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Cấu hình logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Cấu hình mặc định
EMBEDDING_DIMENSION = 768  # all-mpnet-base-v2 produces 768-dimensional vectors
DATA_DIR = r"C:\MyData\projects\THITHI\Data"
PYTHON_API_URL = os.getenv("PYTHON_API_URL", "http://localhost:5005/vectorize")


class ExcelToSQLVectorImporter:
    """Import Excel files vào SQL Server với vector embeddings"""
    
    def __init__(
        self,
        connection_string: Optional[str] = None,
        data_dir: str = DATA_DIR,
        embedding_dimension: int = EMBEDDING_DIMENSION,
        python_api_url: str = PYTHON_API_URL
    ):
        """
        Khởi tạo importer
        
        Args:
            connection_string: SQL Server connection string
            data_dir: Thư mục chứa file Excel
            embedding_dimension: Kích thước vector embedding
            python_api_url: URL của Python API để vectorize
        """
        self.data_dir = Path(data_dir)
        self.embedding_dimension = embedding_dimension
        self.python_api_url = python_api_url
        
        # Kết nối SQL Server
        if not connection_string:
            connection_string = self._build_connection_string()
        
        self.connection_string = connection_string
        
        logger.info(f"Khởi tạo ExcelToSQLVectorImporter")
        logger.info(f"Data directory: {self.data_dir}")
        logger.info(f"Embedding dimension: {self.embedding_dimension}")
    
    def _build_connection_string(self) -> str:
        """Xây dựng connection string từ environment variables"""
        connection_string = os.getenv("SQL_CONNECTION_STRING")
        if connection_string:
            return connection_string
        
        server = os.getenv("SQL_SERVER", "localhost")
        database = os.getenv("SQL_DATABASE", "THITHI_AI")
        trusted_connection = os.getenv("SQL_TRUSTED_CONNECTION", "yes")
        
        if trusted_connection.lower() == "yes":
            return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};Trusted_Connection=yes;TrustServerCertificate=yes;"
        else:
            username = os.getenv("SQL_USERNAME")
            password = os.getenv("SQL_PASSWORD")
            return f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={server};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
    
    def _get_connection(self):
        """Lấy SQL Server connection"""
        return pyodbc.connect(self.connection_string)
    
    def _detect_column_types(self, df: pd.DataFrame) -> Tuple[List[str], List[str], List[str]]:
        """
        Tự động phát hiện cột text (ngữ nghĩa), cột số (numeric) và cột datetime
        
        Returns:
            Tuple (text_columns, numeric_columns, datetime_columns)
        """
        text_columns = []
        numeric_columns = []
        datetime_columns = []
        
        for col in df.columns:
            # Chuyển tên cột thành string (xử lý trường hợp là số hoặc NaN)
            col_str = str(col) if pd.notna(col) else f"Column_{len(text_columns + numeric_columns + datetime_columns)}"
            
            # Bỏ qua cột ID hoặc index
            if col_str.lower() in ['id', 'index', 'stt', 'no', 'unnamed', 'nan']:
                continue
            
            # Kiểm tra kiểu dữ liệu
            dtype = df[col].dtype
            
            # Kiểm tra datetime trước (có thể là datetime64 hoặc object chứa date)
            if pd.api.types.is_datetime64_any_dtype(dtype):
                datetime_columns.append(col)
                continue
            
            # Nếu là object (string), kiểm tra xem có phải datetime hoặc text ngữ nghĩa
            if dtype == 'object':
                # Lấy mẫu để kiểm tra
                sample = df[col].dropna().head(20)
                if len(sample) > 0:
                    # Thử parse thành datetime
                    is_datetime = False
                    datetime_count = 0
                    
                    for val in sample:
                        if pd.notna(val):
                            # Thử parse thành datetime
                            try:
                                pd.to_datetime(val, errors='raise')
                                datetime_count += 1
                            except:
                                pass
                    
                    # Nếu > 50% giá trị có thể parse thành datetime -> là cột datetime
                    if datetime_count > len(sample) * 0.5:
                        datetime_columns.append(col)
                        is_datetime = True
                    
                    # Nếu không phải datetime và có text dài hơn 5 ký tự hoặc chứa chữ cái -> text ngữ nghĩa
                    if not is_datetime:
                        has_text = any(
                            isinstance(val, str) and len(str(val)) > 5 and any(c.isalpha() for c in str(val))
                            for val in sample
                        )
                        if has_text:
                            text_columns.append(col)
            
            # Nếu là số -> numeric
            elif pd.api.types.is_numeric_dtype(dtype):
                numeric_columns.append(col)
        
        logger.info(f"Phát hiện {len(text_columns)} cột text: {text_columns}")
        logger.info(f"Phát hiện {len(numeric_columns)} cột số: {numeric_columns}")
        logger.info(f"Phát hiện {len(datetime_columns)} cột datetime: {datetime_columns}")
        
        return text_columns, numeric_columns, datetime_columns
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings sử dụng Python API
        
        Args:
            texts: Danh sách text cần vectorize
            
        Returns:
            List of embedding vectors
        """
        if not texts:
            return []
        
        try:
            # Gọi Python API để vectorize
            response = requests.post(
                self.python_api_url,
                json={"texts": texts},
                timeout=300  # 5 phút timeout cho batch lớn
            )
            response.raise_for_status()
            
            result = response.json()
            vectors = result.get("vectors", [])
            
            logger.info(f"Đã generate {len(vectors)} embeddings")
            return vectors
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Lỗi khi gọi Python API: {e}")
            logger.error("Đảm bảo Python API đang chạy tại: " + self.python_api_url)
            raise
        except Exception as e:
            logger.error(f"Lỗi khi generate embeddings: {e}")
            raise
    
    def _create_combined_text(self, row: pd.Series, text_columns: List[str]) -> str:
        """
        Kết hợp các cột text thành một chuỗi để vectorize
        
        Args:
            row: Một dòng dữ liệu
            text_columns: Danh sách cột text
            
        Returns:
            Chuỗi text đã kết hợp
        """
        texts = []
        for col in text_columns:
            value = row[col]
            if pd.notna(value) and str(value).strip():
                texts.append(f"{col}: {str(value).strip()}")
        
        return " | ".join(texts) if texts else ""
    
    def _ensure_table_exists(self, table_name: str, text_columns: List[str], numeric_columns: List[str], datetime_columns: List[str]):
        """
        Tạo bảng SQL Server nếu chưa tồn tại
        
        Args:
            table_name: Tên bảng
            text_columns: Danh sách cột text
            numeric_columns: Danh sách cột số
            datetime_columns: Danh sách cột datetime
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Kiểm tra SQL Server version
            cursor.execute("SELECT CAST(SERVERPROPERTY('ProductVersion') AS VARCHAR(50))")
            version = cursor.fetchone()[0]
            version_major = int(version.split('.')[0])
            
            has_vector_support = version_major >= 16  # SQL Server 2025+
            
            # Kiểm tra bảng đã tồn tại chưa
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{table_name}'
            """)
            table_exists = cursor.fetchone()[0] > 0
            
            if not table_exists:
                # Tạo bảng mới
                columns_sql = ["ID INT IDENTITY(1,1) PRIMARY KEY"]
                
                # Thêm các cột text
                for col in text_columns:
                    # Escape tên cột nếu có ký tự đặc biệt
                    col_safe = f"[{col}]"
                    columns_sql.append(f"{col_safe} NVARCHAR(MAX) NULL")
                
                # Thêm các cột số
                for col in numeric_columns:
                    col_safe = f"[{col}]"
                    # Phát hiện kiểu số
                    columns_sql.append(f"{col_safe} FLOAT NULL")
                
                # Thêm các cột datetime
                for col in datetime_columns:
                    col_safe = f"[{col}]"
                    columns_sql.append(f"{col_safe} DATETIME2 NULL")
                
                # Thêm cột vector
                if has_vector_support:
                    columns_sql.append(f"CombinedText NVARCHAR(MAX) NULL")
                    columns_sql.append(f"VectorJson NVARCHAR(MAX) NULL")
                    columns_sql.append(f"Embedding VECTOR({self.embedding_dimension}) NULL")
                else:
                    columns_sql.append(f"CombinedText NVARCHAR(MAX) NULL")
                    columns_sql.append(f"VectorJson NVARCHAR(MAX) NULL")
                
                # Thêm metadata
                columns_sql.append("SourceFile NVARCHAR(500) NULL")
                columns_sql.append("RowIndex INT NULL")
                columns_sql.append("CreatedAt DATETIME2 DEFAULT GETDATE()")
                
                create_sql = f"""
                CREATE TABLE dbo.[{table_name}] (
                    {', '.join(columns_sql)}
                );
                """
                
                cursor.execute(create_sql)
                conn.commit()
                logger.info(f"Đã tạo bảng {table_name}")
            else:
                # Kiểm tra và thêm các cột còn thiếu
                cursor.execute(f"""
                    SELECT COLUMN_NAME 
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_SCHEMA = 'dbo' AND TABLE_NAME = '{table_name}'
                """)
                existing_columns = {row[0] for row in cursor.fetchall()}
                
                # Thêm các cột còn thiếu
                all_columns = text_columns + numeric_columns + datetime_columns
                for col in all_columns:
                    col_safe = f"[{col}]"
                    if col not in existing_columns:
                        if col in text_columns:
                            cursor.execute(f"ALTER TABLE dbo.[{table_name}] ADD {col_safe} NVARCHAR(MAX) NULL")
                        elif col in datetime_columns:
                            cursor.execute(f"ALTER TABLE dbo.[{table_name}] ADD {col_safe} DATETIME2 NULL")
                        else:
                            cursor.execute(f"ALTER TABLE dbo.[{table_name}] ADD {col_safe} FLOAT NULL")
                        logger.info(f"Đã thêm cột {col} vào bảng {table_name}")
                
                # Đảm bảo các cột vector tồn tại
                if has_vector_support:
                    if 'Embedding' not in existing_columns:
                        cursor.execute(f"ALTER TABLE dbo.[{table_name}] ADD Embedding VECTOR({self.embedding_dimension}) NULL")
                        logger.info(f"Đã thêm cột Embedding")
                    if 'VectorJson' not in existing_columns:
                        cursor.execute(f"ALTER TABLE dbo.[{table_name}] ADD VectorJson NVARCHAR(MAX) NULL")
                        logger.info(f"Đã thêm cột VectorJson")
                    if 'CombinedText' not in existing_columns:
                        cursor.execute(f"ALTER TABLE dbo.[{table_name}] ADD CombinedText NVARCHAR(MAX) NULL")
                        logger.info(f"Đã thêm cột CombinedText")
                else:
                    if 'VectorJson' not in existing_columns:
                        cursor.execute(f"ALTER TABLE dbo.[{table_name}] ADD VectorJson NVARCHAR(MAX) NULL")
                        logger.info(f"Đã thêm cột VectorJson")
                    if 'CombinedText' not in existing_columns:
                        cursor.execute(f"ALTER TABLE dbo.[{table_name}] ADD CombinedText NVARCHAR(MAX) NULL")
                        logger.info(f"Đã thêm cột CombinedText")
                
                if 'SourceFile' not in existing_columns:
                    cursor.execute(f"ALTER TABLE dbo.[{table_name}] ADD SourceFile NVARCHAR(500) NULL")
                    logger.info(f"Đã thêm cột SourceFile")
                if 'RowIndex' not in existing_columns:
                    cursor.execute(f"ALTER TABLE dbo.[{table_name}] ADD RowIndex INT NULL")
                    logger.info(f"Đã thêm cột RowIndex")
                if 'CreatedAt' not in existing_columns:
                    cursor.execute(f"ALTER TABLE dbo.[{table_name}] ADD CreatedAt DATETIME2 DEFAULT GETDATE()")
                    logger.info(f"Đã thêm cột CreatedAt")
                
                conn.commit()
                logger.info(f"Đã kiểm tra và cập nhật bảng {table_name}")
    
    def import_excel_file(
        self,
        excel_file: Path,
        table_name: Optional[str] = None,
        sheet_name: Optional[str] = None,
        batch_size: int = 50,
        header_row: int = 0
    ) -> Dict[str, Any]:
        """
        Import một file Excel vào SQL Server
        
        Args:
            excel_file: Đường dẫn file Excel
            table_name: Tên bảng (mặc định: tên file không extension)
            sheet_name: Tên sheet (mặc định: sheet đầu tiên)
            batch_size: Số dòng xử lý mỗi batch
            
        Returns:
            Dict chứa thông tin kết quả import
        """
        logger.info(f"Bắt đầu import file: {excel_file}")
        
        if not excel_file.exists():
            raise FileNotFoundError(f"File không tồn tại: {excel_file}")
        
        # Đọc Excel
        try:
            if sheet_name:
                df = pd.read_excel(excel_file, sheet_name=sheet_name, header=header_row)
            else:
                df = pd.read_excel(excel_file, sheet_name=0, header=header_row)  # Sheet đầu tiên
            
            # Loại bỏ các dòng và cột toàn NULL
            original_rows = len(df)
            original_cols = len(df.columns)
            
            # Loại bỏ các dòng toàn NULL
            df = df.dropna(how="all")
            
            # Loại bỏ các dòng có quá ít dữ liệu (ví dụ: chỉ có 1-2 cột có giá trị)
            # Tính số cột có giá trị cho mỗi dòng
            non_null_counts = df.notna().sum(axis=1)
            # Giữ lại các dòng có ít nhất 3 cột có giá trị (hoặc 10% số cột)
            min_columns_threshold = max(3, int(len(df.columns) * 0.1))
            df = df[non_null_counts >= min_columns_threshold]
            
            # Loại bỏ các cột toàn NULL
            df = df.loc[:, df.notna().any()]
            
            # Loại bỏ các dòng trống ở cuối (nếu có nhiều dòng NULL liên tiếp ở cuối)
            # Tìm dòng cuối cùng có dữ liệu
            last_valid_row = None
            for idx in reversed(df.index):
                if df.loc[idx].notna().sum() >= min_columns_threshold:
                    last_valid_row = idx
                    break
            
            if last_valid_row is not None:
                # Chỉ giữ lại từ đầu đến dòng cuối có dữ liệu
                df = df.loc[:last_valid_row]
            
            # Chuẩn hóa tên cột: chuyển tất cả thành string và xử lý tên cột không hợp lệ
            new_columns = []
            col_counter = {}
            for i, col in enumerate(df.columns):
                # Chuyển thành string
                col_str = str(col) if pd.notna(col) else f"Column_{i}"
                
                # Xử lý tên cột rỗng hoặc "Unnamed"
                if not col_str or col_str.lower().startswith('unnamed') or col_str.lower() == 'nan':
                    col_str = f"Column_{i}"
                
                # Tránh trùng lặp tên cột
                if col_str in new_columns:
                    if col_str not in col_counter:
                        col_counter[col_str] = 1
                    col_counter[col_str] += 1
                    col_str = f"{col_str}_{col_counter[col_str]}"
                
                new_columns.append(col_str)
            
            df.columns = new_columns
            
            logger.info(f"Đã đọc {len(df)} dòng (gốc {original_rows}) và {len(df.columns)} cột (gốc {original_cols}) từ file Excel")
            logger.info(f"Các cột sau khi làm sạch: {list(df.columns)[:20]}...")  # Chỉ hiển thị 20 cột đầu
        except Exception as e:
            logger.error(f"Lỗi khi đọc Excel: {e}")
            raise
        
        if df.empty:
            return {
                "status": "warning",
                "message": "File Excel rỗng",
                "file": str(excel_file),
                "rows_imported": 0
            }
        
        # Tự động phát hiện cột text, số và datetime
        text_columns, numeric_columns, datetime_columns = self._detect_column_types(df)
        
        if not text_columns:
            logger.warning("Không phát hiện cột text nào. Sẽ không tạo vector embeddings.")
        
        # Tên bảng
        if not table_name:
            table_name = excel_file.stem.replace(" ", "_").replace("-", "_")
        
        # Tạo bảng
        self._ensure_table_exists(table_name, text_columns, numeric_columns, datetime_columns)
        
        # Tạo combined text cho mỗi dòng
        if text_columns:
            logger.info("Đang tạo combined text cho vectorization...")
            combined_texts = []
            for idx, row in df.iterrows():
                combined_text = self._create_combined_text(row, text_columns)
                combined_texts.append(combined_text)
        else:
            combined_texts = [""] * len(df)
        
        # Generate embeddings theo batch
        embeddings = []
        if text_columns:
            logger.info(f"Đang generate embeddings cho {len(combined_texts)} dòng (batch_size={batch_size})...")
            for i in range(0, len(combined_texts), batch_size):
                batch_texts = combined_texts[i:i+batch_size]
                # Lọc bỏ text rỗng nhưng giữ lại index
                batch_texts_with_index = [(j, t) for j, t in enumerate(batch_texts)]
                batch_texts_filtered = [t for _, t in batch_texts_with_index if t.strip()]
                
                if batch_texts_filtered:
                    batch_embeddings = self._generate_embeddings(batch_texts_filtered)
                    
                    # Map lại embeddings cho batch (có thể có text rỗng)
                    batch_embeddings_list = []
                    embedding_idx = 0
                    for local_idx, (original_idx, text) in enumerate(batch_texts_with_index):
                        if text.strip() and embedding_idx < len(batch_embeddings):
                            batch_embeddings_list.append(batch_embeddings[embedding_idx])
                            embedding_idx += 1
                        else:
                            batch_embeddings_list.append([])
                    
                    # Đảm bảo số lượng embeddings = số lượng dòng trong batch
                    while len(batch_embeddings_list) < len(batch_texts):
                        batch_embeddings_list.append([])
                    
                    embeddings.extend(batch_embeddings_list)
                else:
                    # Tất cả text trong batch đều rỗng
                    embeddings.extend([[]] * len(batch_texts))
                
                logger.info(f"Đã xử lý {min(i+batch_size, len(combined_texts))}/{len(combined_texts)} dòng")
        else:
            embeddings = [[]] * len(df)
        
        # Đảm bảo số lượng embeddings = số dòng
        while len(embeddings) < len(df):
            embeddings.append([])
        
        logger.info(f"Đã generate {len(embeddings)} embeddings (cần {len(df)} embeddings)")
        
        # Lưu vào SQL Server
        logger.info(f"Đang lưu {len(df)} dòng vào SQL Server...")
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Kiểm tra có VECTOR column không
            cursor.execute(f"""
                SELECT COUNT(*) 
                FROM sys.columns 
                WHERE object_id = OBJECT_ID('dbo.[{table_name}]') 
                AND name = 'Embedding'
            """)
            has_vector_column = cursor.fetchone()[0] > 0
            
            inserted_count = 0
            
            for idx, row in df.iterrows():
                try:
                    # Kiểm tra dòng có đủ dữ liệu không (ít nhất 10% cột có giá trị)
                    all_data_columns = text_columns + numeric_columns + datetime_columns
                    non_null_count = sum(1 for col in all_data_columns if col in row and pd.notna(row[col]))
                    min_required = max(1, int(len(all_data_columns) * 0.1))  # Ít nhất 10% cột có dữ liệu
                    
                    if non_null_count < min_required:
                        # Bỏ qua dòng có quá ít dữ liệu
                        continue
                    
                    # Xây dựng SQL INSERT
                    all_columns = text_columns + numeric_columns + datetime_columns
                    col_names = [f"[{col}]" for col in all_columns]
                    col_names.extend(["CombinedText", "VectorJson", "SourceFile", "RowIndex"])
                    
                    if has_vector_column:
                        col_names.append("Embedding")
                    
                    placeholders = ["?"] * len(col_names)
                    
                    # Giá trị
                    values = []
                    for col in text_columns:
                        val = row[col] if col in row and pd.notna(row[col]) else None
                        values.append(str(val) if val is not None else None)
                    
                    for col in numeric_columns:
                        val = row[col] if col in row and pd.notna(row[col]) else None
                        values.append(float(val) if val is not None else None)
                    
                    for col in datetime_columns:
                        val = row[col] if col in row and pd.notna(row[col]) else None
                        # Chuyển đổi datetime thành datetime object
                        if val is not None:
                            try:
                                if isinstance(val, str):
                                    val = pd.to_datetime(val)
                                elif not isinstance(val, pd.Timestamp):
                                    val = pd.to_datetime(val)
                                values.append(val.to_pydatetime() if hasattr(val, 'to_pydatetime') else val)
                            except:
                                values.append(None)
                        else:
                            values.append(None)
                    
                    # Combined text và embedding
                    combined_text = combined_texts[idx] if idx < len(combined_texts) else ""
                    
                    # Lấy embedding an toàn
                    embedding = []
                    if idx < len(embeddings):
                        embedding = embeddings[idx] if embeddings[idx] else []
                    embedding_json = json.dumps(embedding) if embedding else None
                    
                    values.extend([
                        combined_text if combined_text else None,
                        embedding_json,
                        excel_file.name,
                        int(idx)
                    ])
                    
                    # Thực thi INSERT
                    if has_vector_column and embedding and len(embedding) == self.embedding_dimension:
                        # Format vector string cho SQL Server
                        # SQL Server 2025 yêu cầu format: CAST('[1.0,2.0,3.0]' AS VECTOR(768))
                        # Nhưng pyodbc không hỗ trợ tốt parameterized query cho VECTOR
                        # Nên ta embed trực tiếp vào SQL (an toàn vì embedding không phải user input)
                        vector_string = "[" + ",".join(str(float(v)) for v in embedding) + "]"
                        
                        sql = f"""
                        INSERT INTO dbo.[{table_name}] 
                        ({', '.join(col_names)})
                        VALUES ({', '.join(placeholders[:-1])}, CAST('{vector_string}' AS VECTOR({self.embedding_dimension})))
                        """
                    elif has_vector_column:
                        # NULL embedding hoặc embedding không hợp lệ
                        sql = f"""
                        INSERT INTO dbo.[{table_name}] 
                        ({', '.join(col_names)})
                        VALUES ({', '.join(placeholders)})
                        """
                    else:
                        sql = f"""
                        INSERT INTO dbo.[{table_name}] 
                        ({', '.join(col_names)})
                        VALUES ({', '.join(placeholders)})
                        """
                    
                    cursor.execute(sql, tuple(values))
                    inserted_count += 1
                    
                    if (inserted_count % 50 == 0):
                        conn.commit()
                        logger.info(f"Đã insert {inserted_count}/{len(df)} dòng")
                
                except Exception as e:
                    logger.error(f"Lỗi khi insert dòng {idx}: {e}")
                    continue
            
            conn.commit()
            logger.info(f"Đã insert {inserted_count} dòng vào bảng {table_name}")
        
        return {
            "status": "success",
            "message": f"Đã import thành công {inserted_count} dòng",
            "file": str(excel_file),
            "table_name": table_name,
            "rows_imported": inserted_count,
            "total_rows": len(df),
            "text_columns": text_columns,
            "numeric_columns": numeric_columns,
            "datetime_columns": datetime_columns,
            "has_embeddings": len(text_columns) > 0
        }
    
    def import_all_excel_files(
        self,
        table_name_prefix: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Import tất cả file Excel trong thư mục data
        
        Args:
            table_name_prefix: Tiền tố cho tên bảng (mặc định: không có)
            
        Returns:
            Dict chứa kết quả import tất cả files
        """
        if not self.data_dir.exists():
            raise FileNotFoundError(f"Thư mục không tồn tại: {self.data_dir}")
        
        # Tìm tất cả file Excel
        excel_files = list(self.data_dir.glob("*.xlsx")) + list(self.data_dir.glob("*.xls"))
        # Bỏ qua các file tạm do Excel tạo (~$...) để tránh lỗi permission
        excel_files = [f for f in excel_files if not f.name.startswith("~$")]
        
        if not excel_files:
            return {
                "status": "warning",
                "message": "Không tìm thấy file Excel nào",
                "data_dir": str(self.data_dir),
                "files_processed": 0
            }
        
        logger.info(f"Tìm thấy {len(excel_files)} file Excel")
        
        results = []
        for excel_file in excel_files:
            try:
                table_name = excel_file.stem.replace(" ", "_").replace("-", "_")
                if table_name_prefix:
                    table_name = f"{table_name_prefix}_{table_name}"
                
                result = self.import_excel_file(excel_file, table_name=table_name)
                results.append(result)
            except Exception as e:
                logger.error(f"Lỗi khi import {excel_file}: {e}")
                results.append({
                    "status": "error",
                    "file": str(excel_file),
                    "error": str(e)
                })
        
        success_count = sum(1 for r in results if r.get("status") == "success")
        
        return {
            "status": "completed",
            "message": f"Đã xử lý {len(excel_files)} files, thành công {success_count} files",
            "data_dir": str(self.data_dir),
            "files_processed": len(excel_files),
            "files_success": success_count,
            "results": results
        }


def main():
    """Hàm main để chạy script"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Import Excel files vào SQL Server với vector embeddings")
    parser.add_argument("--file", type=str, help="Đường dẫn file Excel cụ thể (nếu không có thì import tất cả)")
    parser.add_argument("--table", type=str, help="Tên bảng (mặc định: tên file)")
    parser.add_argument("--sheet", type=str, help="Tên sheet (mặc định: sheet đầu tiên)")
    parser.add_argument("--data-dir", type=str, default=DATA_DIR, help=f"Thư mục chứa Excel (mặc định: {DATA_DIR})")
    parser.add_argument("--batch-size", type=int, default=50, help="Số dòng xử lý mỗi batch (mặc định: 50)")
    parser.add_argument("--header-row", type=int, default=0, help="Dòng header (0 = dòng đầu tiên trong sheet, 2 = dòng số 3 trong Excel, ...)")
    
    args = parser.parse_args()
    
    # Tạo importer
    importer = ExcelToSQLVectorImporter(data_dir=args.data_dir)
    
    try:
        if args.file:
            # Import file cụ thể
            excel_file = Path(args.file)
            result = importer.import_excel_file(
                excel_file,
                table_name=args.table,
                sheet_name=args.sheet,
                batch_size=args.batch_size,
                header_row=args.header_row
            )
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            # Import tất cả files
            result = importer.import_all_excel_files()
            print(json.dumps(result, indent=2, ensure_ascii=False))
    
    except Exception as e:
        logger.error(f"Lỗi: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
