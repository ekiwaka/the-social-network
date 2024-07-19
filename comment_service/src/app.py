from flask import Flask, request, jsonify
from models import db, Comment
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://user:password@mysql/social_media')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/comments', methods=['POST'])
def create_comment():
    data = request.get_json()
    new_comment = Comment(
        text=data['text'],
        discussion_id=data['discussion_id'],
        user_id=data['user_id']
    )
    db.session.add(new_comment)
    db.session.commit()
    return jsonify({'message': 'Comment created successfully'}), 201

@app.route('/comments/<comment_id>', methods=['PUT'])
def update_comment(comment_id):
    data = request.get_json()
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({'message': 'Comment not found'}), 404
    comment.text = data.get('text', comment.text)
    db.session.commit()
    return jsonify({'message': 'Comment updated successfully'})

@app.route('/comments/<comment_id>', methods=['DELETE'])
def delete_comment(comment_id):
    comment = Comment.query.get(comment_id)
    if not comment:
        return jsonify({'message': 'Comment not found'}), 404
    db.session.delete(comment)
    db.session.commit()
    return jsonify({'message': 'Comment deleted successfully'})

@app.route('/comments', methods=['GET'])
def list_comments():
    comments = Comment.query.all()
    return jsonify([{'id': comment.id, 'text': comment.text, 'discussion_id': comment.discussion_id, 'user_id': comment.user_id} for comment in comments])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)

