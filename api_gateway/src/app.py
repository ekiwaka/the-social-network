from flask import Flask, request, jsonify
import requests
import os

app = Flask(__name__)

USER_SERVICE_URL = os.getenv('USER_SERVICE_URL', 'http://user_service:5000')
DISCUSSION_SERVICE_URL = os.getenv('DISCUSSION_SERVICE_URL', 'http://discussion_service:5000')
COMMENT_SERVICE_URL = os.getenv('COMMENT_SERVICE_URL', 'http://comment_service:5000')
LIKE_SERVICE_URL = os.getenv('LIKE_SERVICE_URL', 'http://like_service:5000')
SEARCH_SERVICE_URL = os.getenv('SEARCH_SERVICE_URL', 'http://search_service:5000')

# User routes
@app.route('/users', methods=['POST'])
def create_user():
    response = requests.post(f'{USER_SERVICE_URL}/users', json=request.get_json())
    return jsonify(response.json()), response.status_code

@app.route('/users/<user_id>', methods=['PUT'])
def update_user(user_id):
    response = requests.put(f'{USER_SERVICE_URL}/users/{user_id}', json=request.get_json())
    return jsonify(response.json()), response.status_code

@app.route('/users/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    response = requests.delete(f'{USER_SERVICE_URL}/users/{user_id}')
    return jsonify(response.json()), response.status_code

@app.route('/users', methods=['GET'])
def list_users():
    response = requests.get(f'{USER_SERVICE_URL}/users')
    return jsonify(response.json()), response.status_code

@app.route('/users/search', methods=['GET'])
def search_users():
    response = requests.get(f'{USER_SERVICE_URL}/users/search', params=request.args)
    return jsonify(response.json()), response.status_code

# Discussion routes
@app.route('/discussions', methods=['POST'])
def create_discussion():
    response = requests.post(f'{DISCUSSION_SERVICE_URL}/discussions', json=request.get_json())
    return jsonify(response.json()), response.status_code

@app.route('/discussions/<discussion_id>', methods=['PUT'])
def update_discussion(discussion_id):
    response = requests.put(f'{DISCUSSION_SERVICE_URL}/discussions/{discussion_id}', json=request.get_json())
    return jsonify(response.json()), response.status_code

@app.route('/discussions/<discussion_id>', methods=['DELETE'])
def delete_discussion(discussion_id):
    response = requests.delete(f'{DISCUSSION_SERVICE_URL}/discussions/{discussion_id}')
    return jsonify(response.json()), response.status_code

@app.route('/discussions', methods=['GET'])
def list_discussions():
    response = requests.get(f'{DISCUSSION_SERVICE_URL}/discussions')
    return jsonify(response.json()), response.status_code

@app.route('/discussions/search', methods=['GET'])
def search_discussions():
    response = requests.get(f'{DISCUSSION_SERVICE_URL}/discussions/search', params=request.args)
    return jsonify(response.json()), response.status_code

# Comment routes
@app.route('/comments', methods=['POST'])
def create_comment():
    response = requests.post(f'{COMMENT_SERVICE_URL}/comments', json=request.get_json())
    return jsonify(response.json()), response.status_code

@app.route('/comments/<comment_id>', methods=['PUT'])
def update_comment(comment_id):
    response = requests.put(f'{COMMENT_SERVICE_URL}/comments/{comment_id}', json=request.get_json())
    return jsonify(response.json()), response.status_code

@app.route('/comments/<comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    response = requests.delete(f'{COMMENT_SERVICE_URL}/comments/{comment_id}')
    return jsonify(response.json()), response.status_code

@app.route('/comments', methods=['GET'])
def list_comments():
    response = requests.get(f'{COMMENT_SERVICE_URL}/comments')
    return jsonify(response.json()), response.status_code

# Like routes
@app.route('/likes', methods=['POST'])
def create_like():
    response = requests.post(f'{LIKE_SERVICE_URL}/likes', json=request.get_json())
    return jsonify(response.json()), response.status_code

@app.route('/likes/<like_id>', methods=['DELETE'])
def delete_like(like_id):
    response = requests.delete(f'{LIKE_SERVICE_URL}/likes/{like_id}')
    return jsonify(response.json()), response.status_code

@app.route('/likes', methods=['GET'])
def list_likes():
    response = requests.get(f'{LIKE_SERVICE_URL}/likes')
    return jsonify(response.json()), response.status_code

# Search route
@app.route('/search', methods=['GET'])
def search_posts():
    response = requests.get(f'{SEARCH_SERVICE_URL}/search', params=request.args)
    return jsonify(response.json()), response.status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
