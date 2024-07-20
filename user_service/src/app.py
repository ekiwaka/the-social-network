from flask import Flask, request, jsonify
from models import db, User
import os
import jwt
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
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
            current_user = User.query.filter_by(id=data['user_id']).first()
        except Exception:
            return jsonify({'message': 'Token is invalid!'}), 403
        return f(current_user, *args, **kwargs)
    return decorated

def index_user_to_elasticsearch(user):
    """Index a user document into Elasticsearch."""
    try:
        es.index(index='users', id=user.id, body={
            'name': user.name,
            'mobile_no': user.mobile_no,
            'email': user.email
        })
    except Exception as e:
        # Handle Elasticsearch indexing error
        print(f"Failed to index user {user.id} to Elasticsearch: {str(e)}")

def delete_user_from_elasticsearch(user_id):
    """Delete a user document from Elasticsearch."""
    try:
        es.delete(index='users', id=user_id)
    except Exception as e:
        # Handle Elasticsearch deletion error
        print(f"Failed to delete user {user_id} from Elasticsearch: {str(e)}")

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials!'}), 401
    token = jwt.encode({'user_id': user.id, 'exp': datetime.datetime.now() + datetime.timedelta(hours=24)}, app.config['SECRET_KEY'], algorithm="HS256")
    return jsonify({'token': token})

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    existing_user = User.query.filter(
        (User.email == data['email']) | (User.mobile_no == data['mobile_no'])
    ).first()

    if existing_user:
        return jsonify({'message': 'User with this email or mobile number already exists'}), 409

    hashed_password = generate_password_hash(data['password'])
    new_user = User(name=data['name'], mobile_no=data['mobile_no'], email=data['email'], password=hashed_password)
    db.session.add(new_user)
    db.session.commit()

    # Index the user in Elasticsearch
    index_user_to_elasticsearch(new_user)

    return jsonify({'message': 'User created successfully'}), 201

@app.route('/users/<user_id>', methods=['PUT'])
@token_required
def update_user(current_user, user_id):
    if current_user.id != int(user_id):
        return jsonify({'message': 'Permission denied!'}), 403
    data = request.get_json()
    current_user.name = data['name']
    current_user.mobile_no = data['mobile_no']
    current_user.email = data['email']
    if 'password' in data:
        current_user.password = generate_password_hash(data['password'])
    db.session.commit()

    # Update user in Elasticsearch (optional)
    index_user_to_elasticsearch(current_user)

    return jsonify({'message': 'User updated successfully'})

@app.route('/users/<user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    if current_user.id != int(user_id):
        return jsonify({'message': 'Permission denied!'}), 403
    db.session.delete(current_user)
    db.session.commit()

    # Delete user from Elasticsearch
    delete_user_from_elasticsearch(user_id)

    return jsonify({'message': 'User deleted successfully'})

@app.route('/users', methods=['GET'])
@token_required
def list_users():
    users = User.query.all()
    return jsonify([{'id': user.id, 'name': user.name, 'mobile_no': user.mobile_no, 'email': user.email} for user in users])

@app.route('/users/search', methods=['GET'])
@token_required
def search_users():
    name = request.args.get('name')
    users = User.query.filter(User.name.like(f'%{name}%')).all()
    return jsonify([{'id': user.id, 'name': user.name, 'mobile_no': user.mobile_no, 'email': user.email} for user in users])
