from flask import Flask, request, jsonify
from models import db, Like
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://user:password@mysql/social_media')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/likes', methods=['POST'])
def create_like():
    data = request.get_json()
    new_like = Like(
        discussion_id=data['discussion_id'],
        user_id=data['user_id']
    )
    db.session.add(new_like)
    db.session.commit()
    return jsonify({'message': 'Like created successfully'}), 201

@app.route('/likes/<like_id>', methods=['DELETE'])
def delete_like(like_id):
    like = Like.query.get(like_id)
    if not like:
        return jsonify({'message': 'Like not found'}), 404
    db.session.delete(like)
    db.session.commit()
    return jsonify({'message': 'Like deleted successfully'})

@app.route('/likes', methods=['GET'])
def list_likes():
    likes = Like.query.all()
    return jsonify([{'id': like.id, 'discussion_id': like.discussion_id, 'user_id': like.user_id} for like in likes])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)

