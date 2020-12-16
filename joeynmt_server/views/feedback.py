from flask import current_app, jsonify, request

from joeynmt_server.models import Feedback, Parse
from joeynmt_server.app import db


@current_app.route('/save_feedback', methods=['POST'])
def save_user_feedback():
    data = request.json
    fb = Feedback(**data)
    db.session.add(fb)
    db.session.commit()
    response = {'id': fb.id}
    return jsonify(response)


@current_app.route('/query_feedback', methods=['POST'])
def get_user_feedback():
    filters = request.json
    query = db.session.query(Feedback, Parse).filter(Feedback.nl == Parse.nl)
    if 'user_id' in filters:
        query.filter(Feedback.user_id == filters['user_id'])
    if 'model' in filters:
        query.filter(Parse.model == filters['model'])

    joined_feedback = []
    for piece, parse in query:
        joined = {
            'id': piece.id, 'nl': piece.nl, 'correct_lin': piece.correct_lin,
            'original_model': piece.model, 'original_lin': piece.system_lin,
            'parent_ids': piece.parent_id,
            'model': parse.model, 'model_lin': parse.lin
        }
        joined_feedback.append(joined)

    return jsonify(joined_feedback)

