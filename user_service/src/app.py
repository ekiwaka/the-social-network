from flask import Flask, request, jsonify
from models import db, User, Follow
import os
import jwt
import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
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

def index_follow_to_elasticsearch(follower_id, followee_id):
    """Index a follow relationship into Elasticsearch."""
    try:
        es.index(index='follows', id=f"{follower_id}_{followee_id}", body={
            'follower_id': follower_id,
            'followee_id': followee_id
        })
    except Exception as e:
        # Handle Elasticsearch indexing error
        print(f"Failed to index follow relationship {follower_id}_{followee_id} to Elasticsearch: {str(e)}")

def delete_follow_from_elasticsearch(follower_id, followee_id):
    """Delete a follow relationship from Elasticsearch."""
    try:
        es.delete(index='follows', id=f"{follower_id}_{followee_id}")
    except Exception as e:
        # Handle Elasticsearch deletion error
        print(f"Failed to delete follow relationship {follower_id}_{followee_id} from Elasticsearch: {str(e)}")


@app.route('/login', methods=['POST'])
def login():
    """
    Authenticate a user and generate a JWT token.

    Request:
    - JSON body: { "email": "<user_email>", "password": "<user_password>" }

    Response:
    - 200 OK: { "token": "<jwt_token>" }
    - 401 Unauthorized: { "message": "Invalid credentials!" }
    """
    data = request.get_json()
    user = User.query.filter_by(email=data['email']).first()
    if not user or not check_password_hash(user.password, data['password']):
        return jsonify({'message': 'Invalid credentials!'}), 401
    token = jwt.encode({'user_id': user.id, 'exp': datetime.datetime.now() + datetime.timedelta(hours=24)}, app.config['SECRET_KEY'], algorithm="HS256")
    return jsonify({'token': token})

@app.route('/users', methods=['POST'])
def create_user():
    """
    Create a new user.

    Request:
    - JSON body: { "name": "<user_name>", "mobile_no": "<user_mobile_number>", "email": "<user_email>", "password": "<user_password>" }

    Response:
    - 201 Created: { "message": "User created successfully" }
    - 409 Conflict: { "message": "User with this email or mobile number already exists" }
    """
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
    index_user_to_elasticsearch(new_user)

    return jsonify({'message': 'User created successfully'}), 201

@app.route('/users/<user_id>', methods=['PUT'])
@token_required
def update_user(current_user, user_id):
    """
    Update user details.

    Parameters:
    - user_id (path): ID of the user to update.

    Request:
    - JSON body: { "name": "<user_name>", "mobile_no": "<user_mobile_number>", "email": "<user_email>", "password": "<user_password>" }

    Response:
    - 200 OK: { "message": "User updated successfully" }
    - 403 Forbidden: { "message": "Permission denied!" }
    """
    if current_user.id != int(user_id):
        return jsonify({'message': 'Permission denied!'}), 403
    data = request.get_json()
    current_user.name = data['name']
    current_user.mobile_no = data['mobile_no']
    current_user.email = data['email']
    if 'password' in data:
        current_user.password = generate_password_hash(data['password'])
    db.session.commit()
    index_user_to_elasticsearch(current_user)

    return jsonify({'message': 'User updated successfully'})

@app.route('/users/<user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    """
    Delete a user and their follow relationships.

    Parameters:
    - user_id (path): ID of the user to delete.

    Response:
    - 200 OK: { "message": "User and associated follow relationships deleted successfully" }
    - 403 Forbidden: { "message": "Permission denied!" }
    - 404 Not Found: { "message": "User not found!" }
    """
    if current_user.id != int(user_id):
        return jsonify({'message': 'Permission denied!'}), 403

    user_to_delete = User.query.get(user_id)
    if not user_to_delete:
        return jsonify({'message': 'User not found!'}), 404

    # Remove all follow relationships where the user is either the follower or followee
    follows_as_follower = Follow.query.filter_by(follower_id=user_id).all()
    follows_as_followee = Follow.query.filter_by(followee_id=user_id).all()

    for follow in follows_as_follower:
        db.session.delete(follow)
        delete_follow_from_elasticsearch(follow.follower_id, follow.followee_id)
    
    for follow in follows_as_followee:
        db.session.delete(follow)
        delete_follow_from_elasticsearch(follow.follower_id, follow.followee_id)

    # Remove the user from the database
    db.session.delete(user_to_delete)
    db.session.commit()

    # Delete user from Elasticsearch
    delete_user_from_elasticsearch(user_id)

    return jsonify({'message': 'User and associated follow relationships deleted successfully'})

@app.route('/users/<user_id>/follow', methods=['POST'])
@token_required
def follow_user(current_user, user_id):
    """
    Follow a user.

    Parameters:
    - user_id (path): ID of the user to follow.

    Response:
    - 200 OK: { "message": "Successfully followed user!" }
    - 400 Bad Request: { "message": "You cannot follow yourself!" }
    - 400 Bad Request: { "message": "Already following this user!" }
    """
    if current_user.id == int(user_id):
        return jsonify({'message': 'You cannot follow yourself!'}), 400

    # Check if the follow relationship already exists
    existing_follow = Follow.query.filter_by(follower_id=current_user.id, followee_id=user_id).first()
    if existing_follow:
        return jsonify({'message': 'Already following this user!'}), 400

    # Create and add the follow relationship
    follow = Follow(follower_id=current_user.id, followee_id=user_id)
    db.session.add(follow)
    db.session.commit()

    # Index the follow relationship in Elasticsearch
    index_follow_to_elasticsearch(current_user.id, user_id)

    return jsonify({'message': 'Successfully followed user!'})

@app.route('/users/<user_id>/unfollow', methods=['POST'])
@token_required
def unfollow_user(current_user, user_id):
    """
    Unfollow a user.

    Parameters:
    - user_id (path): ID of the user to unfollow.

    Response:
    - 200 OK: { "message": "Successfully unfollowed user!" }
    - 400 Bad Request: { "message": "You cannot unfollow yourself!" }
    - 400 Bad Request: { "message": "You are not following this user!" }
    """
    if current_user.id == int(user_id):
        return jsonify({'message': 'You cannot unfollow yourself!'}), 400

    # Check if the follow relationship exists
    follow = Follow.query.filter_by(follower_id=current_user.id, followee_id=user_id).first()
    if not follow:
        return jsonify({'message': 'You are not following this user!'}), 400

    # Delete the follow relationship
    db.session.delete(follow)
    db.session.commit()

    # Remove the follow relationship from Elasticsearch
    delete_follow_from_elasticsearch(current_user.id, user_id)

    return jsonify({'message': 'Successfully unfollowed user!'})

@app.route('/users/followers', methods=['GET'])
@token_required
def list_followers(current_user):
    """
    List all followers of the current user.

    Query Parameters:
    - page (optional, default 1): Page number to retrieve.
    - per_page (optional, default 10): Number of items per page.

    Response:
    - 200 OK: {
        "page": 1,
        "per_page": 10,
        "total": 25,
        "followers": [
            {
                "id": 1,
                "name": "John Doe",
                "mobile_no": "1234567890",
                "email": "john.doe@example.com"
            }
            // More follower objects
        ]
    }
    - 500 Internal Server Error: { "message": "Error retrieving followers: <error_message>" }
    """
    # Pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    start = (page - 1) * per_page

    try:
        response = es.search(index='follows', body={
            "query": {
                "term": {
                    "followee_id": current_user.id
                }
            },
            "from": start,
            "size": per_page
        })

        followers = []
        for hit in response['hits']['hits']:
            follower_id = hit['_source']['follower_id']
            follower_response = es.get(index='users', id=follower_id)
            followers.append(follower_response['_source'])

        return jsonify({
            'page': page,
            'per_page': per_page,
            'total': response['hits']['total']['value'],
            'followers': followers
        })
    except Exception as e:
        return jsonify({'message': f'Error retrieving followers: {str(e)}'}), 500


@app.route('/users/following', methods=['GET'])
@token_required
def list_following(current_user):
    """
    List all users that the current user is following.

    Query Parameters:
    - page (optional, default 1): Page number to retrieve.
    - per_page (optional, default 10): Number of items per page.

    Response:
    - 200 OK: {
        "page": 1,
        "per_page": 10,
        "total": 15,
        "following": [
            {
                "id": 3,
                "name": "Alice Johnson",
                "mobile_no": "1122334455",
                "email": "alice.johnson@example.com"
            }
            // More followed users
        ]
    }
    - 500 Internal Server Error: { "message": "Error retrieving following users: <error_message>" }
    """
    # Pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    start = (page - 1) * per_page

    try:
        response = es.search(index='follows', body={
            "query": {
                "term": {
                    "follower_id": current_user.id
                }
            },
            "from": start,
            "size": per_page
        })

        following_users = []
        for hit in response['hits']['hits']:
            followee_id = hit['_source']['followee_id']
            followee_response = es.get(index='users', id=followee_id)
            following_users.append(followee_response['_source'])

        return jsonify({
            'page': page,
            'per_page': per_page,
            'total': response['hits']['total']['value'],
            'following': following_users
        })
    except Exception as e:
        return jsonify({'message': f'Error retrieving following users: {str(e)}'}), 500


@app.route('/users', methods=['GET'])
@token_required
def list_all_users(_):
    """
    List all users.

    Query Parameters:
    - page (optional, default 1): Page number to retrieve.
    - per_page (optional, default 10): Number of items per page.

    Response:
    - 200 OK: {
        "page": 1,
        "per_page": 10,
        "total": 50,
        "users": [
            {
                "id": ,
                "name": "",
                "mobile_no": "",
                "email": ""
            }
            // More user objects
        ]
    }
    - 500 Internal Server Error: { "message": "Error retrieving users: <error_message>" }
    """
    # Pagination parameters
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 10))
    start = (page - 1) * per_page

    try:
        response = es.search(index='users', body={
            "query": {
                "match_all": {}
            },
            "from": start,
            "size": per_page
        })

        users = [hit['_source'] for hit in response['hits']['hits']]

        return jsonify({
            'page': page,
            'per_page': per_page,
            'total': response['hits']['total']['value'],
            'users': users
        })
    except Exception as e:
        return jsonify({'message': f'Error retrieving users: {str(e)}'}), 500