from flask import Flask, request, jsonify
from elasticsearch import Elasticsearch
import os

app = Flask(__name__)
es = Elasticsearch([{'host': 'elasticsearch', 'port': 9200}])

@app.route('/search', methods=['GET'])
def search_posts():
    query = request.args.get('query')
    response = es.search(index='discussions', body={'query': {'match': {'hashtags': query}}})
    return jsonify(response['hits']['hits'])

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
