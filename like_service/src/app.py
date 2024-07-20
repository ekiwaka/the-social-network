from flask import Flask, request, jsonify
from sqlalchemy.exc import SQLAlchemyError
from models import db, Like
import os
from functools import wraps
import jwt
from elasticsearch import Elasticsearch

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

db.init_app(app)

es = Elasticsearch(os.getenv('ELASTICSEARCH_URL'), verify_certs=False)

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
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
        except Exception:
            return jsonify({'message': 'Token is invalid!'}), 403
        return f(data['user_id'], *args, **kwargs)
    return decorated

def index_like_to_elasticsearch(like):
    """Index a like document into Elasticsearch."""
    try:
        es.index(index='likes', id=like.id, body={
            'user_id': like.user_id,
            'target_id': like.target_id,
            'target_type': like.target_type
        })
    except Exception as e:
        # Handle Elasticsearch indexing error
        print(f"Failed to index like {like.id} to Elasticsearch: {str(e)}")

def delete_like_from_elasticsearch(like_id):
    """Delete a like document from Elasticsearch."""
    try:
        es.delete(index='likes', id=like_id)
    except Exception as e:
        # Handle Elasticsearch deletion error
        print(f"Failed to delete like {like_id} from Elasticsearch: {str(e)}")

@app.route('/likes', methods=['POST'])
@token_required
def create_like(user_id):
    """
    Create a like for a discussion or comment by the authenticated user.

    Request:
    - JSON body: { "target_id": "<target_id>", "target_type": "<discussion|comment>" }

    Parameters:
    - user_id (path): ID of the authenticated user (extracted from the token).

    Response:
    - 201 Created: { "message": "Like created successfully" }
    """
    try:
        data = request.get_json()
        target_id = data['target_id']
        target_type = data['target_type']

        # Validate target_type
        if target_type not in ['discussion', 'comment']:
            return jsonify({'message': 'Invalid target_type!'}), 400

        new_like = Like(user_id=user_id, target_id=target_id, target_type=target_type)
        db.session.add(new_like)
        db.session.commit()

        # Index the like in Elasticsearch
        index_like_to_elasticsearch(new_like)

        return jsonify({'message': 'Like created successfully'}), 201
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'message': 'Database error', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'message': 'Internal server error', 'error': str(e)}), 500

@app.route('/likes/<like_id>', methods=['DELETE'])
@token_required
def delete_like(user_id, like_id):
    """
    Delete a like by the authenticated user.

    Parameters:
    - like_id (path): ID of the like to delete.
    - user_id (path): ID of the authenticated user (extracted from the token).

    Response:
    - 200 OK: { "message": "Like deleted successfully" }
    - 403 Forbidden: { "message": "Permission denied!" }
    """
    try:
        like = Like.query.get(like_id)
        if like is None:
            return jsonify({'message': 'Like not found!'}), 404
        if like.user_id != user_id:
            return jsonify({'message': 'Permission denied!'}), 403

        db.session.delete(like)
        db.session.commit()

        # Delete like from Elasticsearch
        delete_like_from_elasticsearch(like_id)

        return jsonify({'message': 'Like deleted successfully'})
    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({'message': 'Database error', 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'message': 'Internal server error', 'error': str(e)}), 500


@app.route('/user/likes', methods=['GET'])
@token_required
def list_user_likes(user_id):
    """
    List all likes done by the authenticated user, ordered by the most recent.
    Supports pagination through query parameters.

    Query Parameters:
    - page (int): Page number (default is 1).
    - per_page (int): Number of likes per page (default is 10).

    Parameters:
    - user_id (path): ID of the authenticated user (extracted from the token).

    Response:
    - 200 OK: { "likes": [ { "id": "<like_id>", "target_id": "<target_id>", "target_type": "<discussion|comment>", "created_at": "<timestamp>" }, ... ], "page": <page>, "per_page": <per_page>, "total": <total> }
    """
    try:
        # Get pagination parameters from query string
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=10, type=int)

        # Search for likes by the current user
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"user_id": user_id}}
                    ]
                }
            },
            "sort": [
                {"created_at": {"order": "desc"}}
            ],
            "from": (page - 1) * per_page,
            "size": per_page
        }

        # Execute search query
        response = es.search(index='likes', body=query)

        # Extract results
        likes_list = [{
            'id': hit['_id'],
            'target_id': hit['_source']['target_id'],
            'target_type': hit['_source']['target_type'],
            'created_at': hit['_source']['created_at']
        } for hit in response['hits']['hits']]

        # Prepare response
        response_data = {
            'likes': likes_list,
            'page': page,
            'per_page': per_page,
            'total': response['hits']['total']['value']
        }

        return jsonify(response_data), 200
    except Exception as e:
        # Handle any unexpected errors
        return jsonify({'message': 'An error occurred while retrieving likes.', 'error': str(e)}), 500