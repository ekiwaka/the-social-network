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
    discussion = Discussion.query.get(discussion_id)
    if discussion.user_id != user_id:
        return jsonify({'message': 'Permission denied!'}), 403
    
    db.session.delete(discussion)
    db.session.commit()

    # Delete discussion from Elasticsearch
    delete_discussion_from_elasticsearch(discussion_id)

    return jsonify({'message': 'Discussion deleted successfully'})

@app.route('/discussions', methods=['GET'])
@token_required
def list_discussions():
    discussions = Discussion.query.all()
    return jsonify([{'id': d.id, 'text': d.text, 'image': d.image, 'hashtags': d.hashtags, 'created_on': d.created_on} for d in discussions])

@app.route('/discussions/search', methods=['GET'])
@token_required
def search_discussions():
    text = request.args.get('text')
    discussions = Discussion.query.filter(Discussion.text.like(f'%{text}%')).all()
    return jsonify([{'id': d.id, 'text': d.text, 'image': d.image, 'hashtags': d.hashtags, 'created_on': d.created_on} for d in discussions])
