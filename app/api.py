from flask import request, jsonify, render_template
from app.services.api_service import ApiService
from flask import Blueprint

api_bp = Blueprint('api', __name__)

api_service = ApiService()

@api_bp.route('/', methods=['GET'])
def index():
    """Возвращает HTML-файл фронтенда."""
    return render_template('index.html')

@api_bp.route('/searching', methods=['POST'])
def search():
    """Обрабатывает запрос поиска."""
    data = request.get_json()

    query = data.get("query")
    top_k = data.get("top_k", 5)
    keywords = data.get("keywords")

    if not query:
        return jsonify({"error": "Query is required"}), 400

    results = api_service.search_query(query, top_k, keywords)
    return jsonify(results)


@api_bp.route('/indexing', methods=['POST'])
def indexing():
    """Обрабатывает запрос на индексацию документов."""
    data = request.get_json()

    document_name = data.get("document_name")
    if not document_name:
        return jsonify({"error": "No document name provided"}), 400

    documents = data.get("documents")
    if not documents:
        return jsonify({"error": "No documents to index"}), 400

    result = api_service.index_documents(document_name, documents)
    return jsonify(result)

