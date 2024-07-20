from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

USER_SERVICE_URL = 'http://user_service:5001'
DISCUSSION_SERVICE_URL = 'http://discussion_service:5002'
COMMENT_SERVICE_URL = 'http://comment_service:5003'
LIKE_SERVICE_URL = 'http://like_service:5004'
SEARCH_SERVICE_URL = 'http://search_service:5005'

def forward_request(service_url):
    response = requests.request(
        method=request.method,
        url=f"{service_url}{request.path}",
        headers={key: value for key, value in request.headers if key != 'Host'},
        params=request.args,
        data=request.get_data(),
        cookies=request.cookies,
        allow_redirects=False
    )
    return (response.content, response.status_code, response.headers.items())

@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(path):
    if path.startswith('users') or path.startswith('login'):
        return forward_request(USER_SERVICE_URL)
    elif path.startswith('discussions'):
        return forward_request(DISCUSSION_SERVICE_URL)
    elif path.startswith('comments'):
        return forward_request(COMMENT_SERVICE_URL)
    elif path.startswith('likes'):
        return forward_request(LIKE_SERVICE_URL)
    elif path.startswith('search'):
        return forward_request(SEARCH_SERVICE_URL)
    return jsonify({'message': 'Service not found'}), 404