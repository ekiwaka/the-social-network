from flask import Flask, request, jsonify
from models import db, Like
import os
from functools import wraps
import jwt
import datetime
from elasticsearch import Elasticsearch

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://user:password@mysql/social_media')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mysecret')

db.init_app(app)

es = Elasticsearch(os.getenv('ELASTICSEARCH_URL'), verify_certs=False)

def token_required(f):
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
            'discussion_id': like.discussion_id
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
    data = request.get_json()
    new_like = Like(user_id=user_id, discussion_id=data['discussion_id'])
    db.session.add(new_like)
    db.session.commit()

    # Index the like in Elasticsearch
    index_like_to_elasticsearch(new_like)

    return jsonify({'message': 'Like created successfully'}), 201

@app.route('/likes/<like_id>', methods=['DELETE'])
@token_required
def delete_like(user_id, like_id):
    like = Like.query.get(like_id)
    if like.user_id != user_id:
        return jsonify({'message': 'Permission denied!'}), 403
    
    db.session.delete(like)
    db.session.commit()

    # Delete like from Elasticsearch
    delete_like_from_elasticsearch(like_id)

    return jsonify({'message': 'Like deleted successfully'})

@app.route('/likes', methods=['GET'])
@token_required
def list_likes(user_id):
    likes = Like.query.all()
    return jsonify([{'id': l.id, 'user_id': l.user_id, 'discussion_id': l.discussion_id} for l in likes])
