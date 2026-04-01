from flask import request, jsonify, render_template
from app.services.api_service import ApiService
from flask import Blueprint
from app.config import Config
from app.validation import parse_json_body, validate_search_request, validate_indexing_request

api_bp = Blueprint('api', __name__)

api_service = None


def get_api_service():
    global api_service
    if api_service is None:
        api_service = ApiService()
    return api_service

@api_bp.route('/', methods=['GET'])
def index():
    """Возвращает HTML-файл фронтенда."""
    return render_template('index.html')

@api_bp.route('/searching', methods=['POST'])
def search():
    """Обрабатывает запрос поиска."""
    data = parse_json_body(request)
    query, top_k, keywords = validate_search_request(
        data,
        top_k_default=Config.TOP_K_DEFAULT,
        top_k_max=Config.TOP_K_MAX,
    )

    results = get_api_service().search_query(query, top_k, keywords)
    return jsonify(results)


@api_bp.route('/indexing', methods=['POST'])
def indexing():
    """Обрабатывает запрос на индексацию документов."""
    data = parse_json_body(request)
    document_name, documents = validate_indexing_request(data)

    result = get_api_service().index_documents(document_name, documents)
    return jsonify(result)
