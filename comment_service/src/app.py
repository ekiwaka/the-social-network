from flask import Flask, request, jsonify
from models import db, Comment
import os
from functools import wraps
import jwt
import datetime
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

def index_comment_to_elasticsearch(comment):
    """Index a comment document into Elasticsearch."""
    try:
        es.index(index='comments', id=comment.id, body={
            'text': comment.text,
            'discussion_id': comment.discussion_id,
            'user_id': comment.user_id,
            'created_on': comment.created_on.isoformat()
        })
    except Exception as e:
        # Handle Elasticsearch indexing error
        print(f"Failed to index comment {comment.id} to Elasticsearch: {str(e)}")

def delete_comment_from_elasticsearch(comment_id):
    """Delete a comment document from Elasticsearch."""
    try:
        es.delete(index='comments', id=comment_id)
    except Exception as e:
        # Handle Elasticsearch deletion error
        print(f"Failed to delete comment {comment_id} from Elasticsearch: {str(e)}")

@app.route('/comments', methods=['POST'])
@token_required
def create_comment(user_id):
    """
    Create a new comment by the authenticated user.

    Request:
    - JSON body: { "text": "<text>", "discussion_id": "<discussion_id>" }

    Parameters:
    - user_id (path): ID of the authenticated user (extracted from the token).

    Response:
    - 201 Created: { "message": "Comment created successfully" }
    """
    data = request.get_json()
    new_comment = Comment(text=data['text'], discussion_id=data['discussion_id'], user_id=user_id, created_on=datetime.datetime.now())
    db.session.add(new_comment)
    db.session.commit()

    # Index the comment in Elasticsearch
    index_comment_to_elasticsearch(new_comment)

    return jsonify({'message': 'Comment created successfully'}), 201

@app.route('/comments/<comment_id>', methods=['PUT'])
@token_required
def update_comment(user_id, comment_id):
    """
    Update an existing comment by the authenticated user.

    Request:
    - JSON body: { "text": "<text>" }

    Parameters:
    - comment_id (path): ID of the comment to be updated.
    - user_id (path): ID of the authenticated user (extracted from the token).

    Response:
    - 200 OK: { "message": "Comment updated successfully" }
    - 403 Forbidden: { "message": "Permission denied!" }
    """
    comment = Comment.query.get(comment_id)
    if comment.user_id != user_id:
        return jsonify({'message': 'Permission denied!'}), 403
    data = request.get_json()
    comment.text = data['text']
    db.session.commit()

    # Update comment in Elasticsearch (optional)
    index_comment_to_elasticsearch(comment)

    return jsonify({'message': 'Comment updated successfully'})

@app.route('/comments/<comment_id>', methods=['DELETE'])
@token_required
def delete_comment(user_id, comment_id):
    """
    Delete a comment by the authenticated user.

    Parameters:
    - comment_id (path): ID of the comment to be deleted.
    - user_id (path): ID of the authenticated user (extracted from the token).

    Response:
    - 200 OK: { "message": "Comment deleted successfully" }
    - 403 Forbidden: { "message": "Permission denied!" }
    """
    comment = Comment.query.get(comment_id)
    if comment.user_id != user_id:
        return jsonify({'message': 'Permission denied!'}), 403
    db.session.delete(comment)
    db.session.commit()

    # Delete comment from Elasticsearch
    delete_comment_from_elasticsearch(comment_id)

    return jsonify({'message': 'Comment deleted successfully'})

@app.route('/user/comments', methods=['GET'])
@token_required
def list_user_comments(user_id):
    """
    List all comments created by the authenticated user, ordered by the most recent.
    Supports pagination through query parameters.

    Query Parameters:
    - page (int): Page number (default is 1).
    - per_page (int): Number of comments per page (default is 10).

    Parameters:
    - user_id (path): ID of the authenticated user (extracted from the token).

    Response:
    - 200 OK: { "comments": [ { "id": "<comment_id>", "text": "<text>", "discussion_id": "<discussion_id>", "created_on": "<timestamp>" }, ... ], "page": <page>, "per_page": <per_page>, "total": <total> }
    """
    try:
        # Get pagination parameters from query string
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=10, type=int)

        # Search for comments by the current user
        query = {
            "query": {
                "bool": {
                    "must": [
                        {"match": {"user_id": user_id}}
                    ]
                }
            },
            "sort": [
                {"created_on": {"order": "desc"}}
            ],
            "from": (page - 1) * per_page,
            "size": per_page
        }

        # Execute search query
        response = es.search(index='comments', body=query)

        # Extract results
        comments_list = [{
            'id': hit['_id'],
            'text': hit['_source']['text'],
            'discussion_id': hit['_source']['discussion_id'],
            'created_on': hit['_source']['created_on']
        } for hit in response['hits']['hits']]

        # Prepare response
        response_data = {
            'comments': comments_list,
            'page': page,
            'per_page': per_page,
            'total': response['hits']['total']['value']
        }

        return jsonify(response_data), 200
    except Exception as e:
        # Handle any unexpected errors
        return jsonify({'message': 'An error occurred while retrieving comments.', 'error': str(e)}), 500