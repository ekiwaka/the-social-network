from flask import Flask, request, jsonify
from models import db, Discussion
import os

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'mysql+pymysql://user:password@mysql/social_media')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

@app.route('/discussions', methods=['POST'])
def create_discussion():
    data = request.get_json()
    new_discussion = Discussion(
        text=data['text'],
        image=data['image'],
        hashtags=data['hashtags']
    )
    db.session.add(new_discussion)
    db.session.commit()
    return jsonify({'message': 'Discussion created successfully'}), 201

@app.route('/discussions/<discussion_id>', methods=['PUT'])
def update_discussion(discussion_id):
    data = request.get_json()
    discussion = Discussion.query.get(discussion_id)
    if not discussion:
        return jsonify({'message': 'Discussion not found'}), 404
    discussion.text = data.get('text', discussion.text)
    discussion.image = data.get('image', discussion.image)
    discussion.hashtags = data.get('hashtags', discussion.hashtags)
    db.session.commit()
    return jsonify({'message': 'Discussion updated successfully'})

@app.route('/discussions/<discussion_id>', methods=['DELETE'])
def delete_discussion(discussion_id):
    discussion = Discussion.query.get(discussion_id)
    if not discussion:
        return jsonify({'message': 'Discussion not found'}), 404
    db.session.delete(discussion)
    db.session.commit()
    return jsonify({'message': 'Discussion deleted successfully'})

@app.route('/discussions', methods=['GET'])
def list_discussions():
    discussions = Discussion.query.all()
    return jsonify([{'id': discussion.id, 'text': discussion.text, 'image': discussion.image, 'hashtags': discussion.hashtags} for discussion in discussions])

@app.route('/discussions/search', methods=['GET'])
def search_discussions():
    text = request.args.get('text')
    discussions = Discussion.query.filter(Discussion.text.like(f'%{text}%')).all()
    return jsonify([{'id': discussion.id, 'text': discussion.text, 'image': discussion.image, 'hashtags': discussion.hashtags} for discussion in discussions])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)

