from flask import Flask, request, jsonify
from models import db, Discussion
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

def index_discussion_to_elasticsearch(discussion):
    """Index a discussion document into Elasticsearch."""
    try:
        es.index(index='discussions', id=discussion.id, body={
            'text': discussion.text,
            'image': discussion.image,
            'hashtags': discussion.hashtags,
            'created_on': discussion.created_on.isoformat(),
            'user_id': discussion.user_id
        })
    except Exception as e:
        # Handle Elasticsearch indexing error
        print(f"Failed to index discussion {discussion.id} to Elasticsearch: {str(e)}")

def delete_discussion_from_elasticsearch(discussion_id):
    """Delete a discussion document from Elasticsearch."""
    try:
        es.delete(index='discussions', id=discussion_id)
    except Exception as e:
        # Handle Elasticsearch deletion error
        print(f"Failed to delete discussion {discussion_id} from Elasticsearch: {str(e)}")

@app.route('/discussions', methods=['POST'])
@token_required
def create_discussion(user_id):
    """
    Create a new discussion by the authenticated user.

    Request:
    - JSON body: { "text": "<text>", "image": "<image_url>", "hashtags": "<hashtags>" }

    Parameters:
    - user_id (path): ID of the authenticated user (extracted from the token).

    Response:
    - 201 Created: { "message": "Discussion created successfully" }
    """
    data = request.get_json()
    new_discussion = Discussion(
        text=data['text'],
        image=data['image'],
        hashtags=data['hashtags'],
        user_id=user_id,
        created_on=datetime.datetime.now()
    )
    db.session.add(new_discussion)
    db.session.commit()

    # Index the discussion in Elasticsearch
    index_discussion_to_elasticsearch(new_discussion)

    return jsonify({'message': 'Discussion created successfully'}), 201

@app.route('/discussions/<discussion_id>', methods=['PUT'])
@token_required
def update_discussion(user_id, discussion_id):
    """
    Update an existing discussion by the authenticated user.

    Request:
    - JSON body: { "text": "<text>", "image": "<image_url>", "hashtags": "<hashtags>" }

    Parameters:
    - discussion_id (path): ID of the discussion to be updated.
    - user_id (path): ID of the authenticated user (extracted from the token).

    Response:
    - 200 OK: { "message": "Discussion updated successfully" }
    - 403 Forbidden: { "message": "Permission denied!" }
    """
    discussion = Discussion.query.get(discussion_id)
    if discussion.user_id != user_id:
        return jsonify({'message': 'Permission denied!'}), 403
    
    data = request.get_json()
    discussion.text = data['text']
    discussion.image = data['image']
    discussion.hashtags = data['hashtags']
    db.session.commit()

    # Update discussion in Elasticsearch
    index_discussion_to_elasticsearch(discussion)

    return jsonify({'message': 'Discussion updated successfully'})

@app.route('/discussions/<discussion_id>', methods=['DELETE'])
@token_required
def delete_discussion(user_id, discussion_id):
    """
    Delete a discussion by the authenticated user.

    Parameters:
    - discussion_id (path): ID of the discussion to be deleted.
    - user_id (path): ID of the authenticated user (extracted from the token).

    Response:
    - 200 OK: { "message": "Discussion deleted successfully" }
    - 403 Forbidden: { "message": "Permission denied!" }
    """
    discussion = Discussion.query.get(discussion_id)
    if discussion.user_id != user_id:
        return jsonify({'message': 'Permission denied!'}), 403
    
    db.session.delete(discussion)
    db.session.commit()

    # Delete discussion from Elasticsearch
    delete_discussion_from_elasticsearch(discussion_id)

    return jsonify({'message': 'Discussion deleted successfully'})

@app.route('/user/discussions', methods=['GET'])
@token_required
def list_user_discussions(user_id):
    """
    List all discussions created by the authenticated user, ordered by the most recent.
    Supports pagination through query parameters.

    Query Parameters:
    - page (int): Page number (default is 1).
    - per_page (int): Number of discussions per page (default is 10).

    Parameters:
    - user_id (path): ID of the authenticated user (extracted from the token).

    Response:
    - 200 OK: { "discussions": [ { "id": "<discussion_id>", "text": "<text>", "image": "<image_url>", "hashtags": "<hashtags>", "created_on": "<timestamp>" }, ... ], "page": <page>, "per_page": <per_page>, "total": <total> }
    """
    try:
        # Get pagination parameters from query string
        page = request.args.get('page', default=1, type=int)
        per_page = request.args.get('per_page', default=10, type=int)

        # Query discussions by the current user, ordered by most recent
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
        response = es.search(index='discussions', body=query)

        # Extract results
        discussions_list = [{
            'id': hit['_id'],
            'text': hit['_source']['text'],
            'image': hit['_source']['image'],
            'hashtags': hit['_source']['hashtags'],
            'created_on': hit['_source']['created_on']
        } for hit in response['hits']['hits']]

        # Prepare response
        response_data = {
            'discussions': discussions_list,
            'page': page,
            'per_page': per_page,
            'total': response['hits']['total']['value']
        }

        return jsonify(response_data), 200
    except Exception as e:
        return jsonify({'message': 'An error occurred while retrieving discussions.', 'error': str(e)}), 500