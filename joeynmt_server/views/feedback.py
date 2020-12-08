from flask import current_app, jsonify, request

from joeynmt_server.models import Feedback
from joeynmt_server.app import db


@current_app.route('/save_feedback', methods=['POST'])
def save_feedback():
    data = request.json
    fb = Feedback(**data)
    db.session.add(fb)
    db.session.commit()
    response = {'feedback_id': fb.id}
    return jsonify(response)
