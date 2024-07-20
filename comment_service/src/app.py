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
    comment = Comment.query.get(comment_id)
    if comment.user_id != user_id:
        return jsonify({'message': 'Permission denied!'}), 403
    db.session.delete(comment)
    db.session.commit()

    # Delete comment from Elasticsearch
    delete_comment_from_elasticsearch(comment_id)

    return jsonify({'message': 'Comment deleted successfully'})

@app.route('/comments', methods=['GET'])
@token_required
def list_comments():
    comments = Comment.query.all()
    return jsonify([{'id': c.id, 'text': c.text, 'discussion_id': c.discussion_id, 'user_id': c.user_id, 'created_on': c.created_on} for c in comments])
