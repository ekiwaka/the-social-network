from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch
import os
import jwt
from functools import wraps

app = Flask(__name__)

es = Elasticsearch(os.getenv('ELASTICSEARCH_URL'))
SECRET_KEY = os.getenv('SECRET_KEY', 'mysecret')

def token_required(f):
    """
    Decorator to ensure that the request contains a valid JWT token.

    Parameters:
    - f: The function to be decorated.

    Returns:
    - A wrapper function that checks for a valid JWT token in the request headers.
    
    Response:
    - 403 Forbidden: If the token is missing or invalid.
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing!'}), 403

        try:
            jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        except Exception as e:
            return jsonify({'message': 'Token is invalid!', 'error': str(e)}), 403

        return f(*args, **kwargs)
    return decorated

@app.route('/search/users', methods=['GET'])
@token_required
def search_users():
    """
    Search for users based on a query parameter. Searches across name, mobile number, and email fields.

    Query Parameters:
    - query (str): The search query.

    Response:
    - 200 OK: Returns a list of users matching the search query.
    - 400 Bad Request: If the query parameter is missing.
    - 500 Internal Server Error: If there's an error executing the search query.
    """
    query = request.args.get('query')
    if not query:
        return jsonify({'message': 'Query parameter is required!'}), 400

    es_query = {
        "query": {
            "multi_match": {
                "query": query,
                "fields": ["name", "mobile_no", "email"]
            }
        }
    }
    
    try:
        res = es.search(index="users", body=es_query)
        users = [{'id': hit['_id'], 'name': hit['_source']['name'], 'mobile_no': hit['_source']['mobile_no'], 'email': hit['_source']['email']} for hit in res['hits']['hits']]
        return jsonify(users), 200
    except Exception as e:
        return jsonify({'message': 'Error executing search query', 'error': str(e)}), 500

@app.route('/search/discussions', methods=['GET'])
@token_required
def search_discussions():
    """
    Search for discussions based on a query parameter. Searches across text and hashtags fields.

    Query Parameters:
    - query (str): The search query.

    Response:
    - 200 OK: Returns a list of discussions matching the search query.
    - 400 Bad Request: If the query parameter is missing.
    - 500 Internal Server Error: If there's an error executing the search query.
    """
    query = request.args.get('query')
    if not query:
        return jsonify({'message': 'Query parameter is required!'}), 400

    es_query = {"query": {"multi_match": {"query": query, "fields": ["text", "hashtags"]}}}
    
    try:
        res = es.search(index="discussions", body=es_query)
        discussions = [{'id': hit['_id'], 'user_id': hit['_source']['user_id'], 'text': hit['_source']['text'], 'image': hit['_source']['image'], 'created_at': hit['_source']['created_at']} for hit in res['hits']['hits']]
        return jsonify(discussions), 200
    except Exception as e:
        return jsonify({'message': 'Error executing search query', 'error': str(e)}), 500

@app.route('/search/discussions_by_text', methods=['GET'])
@token_required
def search_discussions_by_text():
    """
    Search for discussions based on a text parameter. Searches only the text field.

    Query Parameters:
    - text (str): The text to search for.

    Response:
    - 200 OK: Returns a list of discussions matching the text.
    - 400 Bad Request: If the text parameter is missing.
    - 500 Internal Server Error: If there's an error executing the search query.
    """
    text = request.args.get('text')
    if not text:
        return jsonify({'message': 'Text parameter is required!'}), 400

    es_query = {"query": {"match": {"text": text}}}
    
    try:
        res = es.search(index="discussions", body=es_query)
        discussions = [{'id': hit['_id'], 'user_id': hit['_source']['user_id'], 'text': hit['_source']['text'], 'image': hit['_source']['image'], 'created_at': hit['_source']['created_at']} for hit in res['hits']['hits']]
        return jsonify(discussions), 200
    except Exception as e:
        return jsonify({'message': 'Error executing search query', 'error': str(e)}), 500

@app.route('/search/discussions_by_hashtag', methods=['GET'])
@token_required
def search_discussions_by_hashtag():
    """
    Search for discussions based on a hashtag parameter. Searches only the hashtags field.

    Query Parameters:
    - hashtag (str): The hashtag to search for.

    Response:
    - 200 OK: Returns a list of discussions matching the hashtag.
    - 400 Bad Request: If the hashtag parameter is missing.
    - 500 Internal Server Error: If there's an error executing the search query.
    """
    hashtag = request.args.get('hashtag')
    if not hashtag:
        return jsonify({'message': 'Hashtag parameter is required!'}), 400

    es_query = {"query": {"match": {"hashtags": hashtag}}}
    
    try:
        res = es.search(index="discussions", body=es_query)
        discussions = [{'id': hit['_id'], 'user_id': hit['_source']['user_id'], 'text': hit['_source']['text'], 'image': hit['_source']['image'], 'created_at': hit['_source']['created_at']} for hit in res['hits']['hits']]
        return jsonify(discussions), 200
    except Exception as e:
        return jsonify({'message': 'Error executing search query', 'error': str(e)}), 500