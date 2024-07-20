from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch
import os
import jwt
from functools import wraps

app = Flask(__name__)

es = Elasticsearch(os.getenv('ELASTICSEARCH_URL'))
SECRET_KEY = os.getenv('SECRET_KEY', 'mysecret')

def token_required(f):
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