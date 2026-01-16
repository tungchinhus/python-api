"""
Python API Server để vectorize text
Endpoint: POST /vectorize
Input: {"texts": ["text1", "text2", ...]}
Output: {"vectors": [[0.1, 0.2, ...], [0.3, 0.4, ...]]}
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
from sentence_transformers import SentenceTransformer
import logging

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)  # Cho phép CORS từ .NET backend

# Load model embedding (sẽ download lần đầu nếu chưa có)
# Model này hỗ trợ tiếng Việt tốt
try:
    logger.info("Đang load model embedding...")
    model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    logger.info("Model đã load thành công!")
except Exception as e:
    logger.error(f"Lỗi khi load model: {e}")
    model = None

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

if __name__ == '__main__':
    # Chạy server trên port 5005
    port = 5005
    logger.info(f"Starting Python Vectorize API on port {port}...")
    app.run(host='0.0.0.0', port=port, debug=True)
