from flask import current_app, jsonify, request
from sqlalchemy import or_

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
    query = db.session.query(Feedback, Parse).outerjoin(
        Parse, Feedback.nl == Parse.nl)
    if 'user_id' in filters:
        query = query.filter(Feedback.user_id == filters['user_id'])
    if 'model' in filters:
        by_id = {}
        for piece, parse in query:
            if parse and parse.model == filters['model']:
                by_id[piece.id] = (piece, parse)
            elif piece.id not in by_id:
                by_id[piece.id] = (piece, None)
        query = by_id.values()

    joined_feedback = []
    for piece, parse in query:
        model = parse.model if parse else None
        model_lin = parse.lin if parse else None
        joined = {
            'id': piece.id, 'nl': piece.nl, 'correct_lin': piece.correct_lin,
            'original_model': piece.model, 'original_lin': piece.system_lin,
            'parent_id': piece.parent_id,
            'model': model, 'model_lin': model_lin
        }
        joined_feedback.append(joined)

    return jsonify(joined_feedback)
