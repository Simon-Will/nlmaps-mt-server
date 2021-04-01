import logging
import threading
import time
import traceback

from flask import current_app, jsonify, request
from sqlalchemy import or_
from sqlalchemy.orm import aliased

from joeynmt_server.app import create_app, db
from joeynmt_server.models import Feedback, Parse
from joeynmt_server.trainer import train_until_finished


@current_app.route('/save_feedback', methods=['POST'])
def save_feedback():
    data = request.json

    if 'train_model' in data:
        config_basename = data.pop('train_model')
    elif 'model' in data:
        config_basename = data['model']
    else:
        config_basename = None

    if 'split' in data:
        data['split'] = data['split'][:50]
        split_was_explicitly_set = True
    else:
        data['split'] = 'train'
        split_was_explicitly_set = False

    fb = Feedback(**data)
    db.session.add(fb)
    db.session.commit()

    if not split_was_explicitly_set:
        if fb.id % 5 == 0:
            fb.split = 'test'
        elif fb.id % 5 == 4:
            fb.split = 'dev'
        db.session.commit()

    def train_in_thread():
        app = create_app()
        with app.app_context():
            try:
                train_until_finished(config_basename)
            except:
                logging.error('Training failed.')
                logging.error(traceback.format_exc())

    response = fb.json_ready_dict()

    if (current_app.config.get('TRAIN_AFTER_FEEDBACK') and config_basename
            and fb.correct_lin and fb.split == 'train'):
        thread = threading.Thread(target=train_in_thread)
        thread.start()
        time.sleep(0.1)
        response['training'] = thread.is_alive()

    return jsonify(response)


@current_app.route('/list_feedback', methods=['POST'])
def list_feedback():
    filters = request.json
    feedback = Feedback.query
    if 'user_id' in filters:
        feedback = feedback.filter(Feedback.user_id == filters['user_id'])

    feedback = [fb.json_ready_dict() for fb in feedback]
    return jsonify(feedback)


@current_app.route('/query_feedback', methods=['POST'])
def query_feedback():
    filters = request.json
    fb_query = Feedback.query
    if 'user_id' in filters:
        fb_query = fb_query.filter_by(user_id=filters['user_id'])
        total_count = Feedback.query.filter_by(
            user_id=filters['user_id']).count()
    else:
        total_count = Feedback.query.count()

    if 'limit' in filters or 'offset' in filters:
        fb_query = fb_query.order_by(Feedback.id)
        if 'limit' in filters:
            fb_query = fb_query.limit(filters['limit'])
        if 'offset' in filters:
            fb_query = fb_query.offset(filters['offset'])

    limited_feedback = aliased(Feedback, fb_query.subquery())

    if 'model' in filters:
        parses_for_model = Parse.query.filter_by(model=filters['model'])
        parses = aliased(Parse, parses_for_model.subquery())
    else:
        parses = Parse

    query = db.session.query(limited_feedback, parses).outerjoin(
        parses, limited_feedback.nl == parses.nl)

    joined_feedback = []
    for piece, parse in query:
        model = parse.model if parse else None
        model_lin = parse.lin if parse else None
        joined = {
            'id': piece.id, 'created': piece.created.isoformat(timespec='seconds'),
            'nl': piece.nl, 'correct_lin': piece.correct_lin,
            'original_model': piece.model, 'original_lin': piece.system_lin,
            'parent_id': piece.parent_id,
            'model': model, 'model_lin': model_lin
        }
        joined_feedback.append(joined)

    data = {
        'total_count': total_count,
        'feedback': joined_feedback
    }

    return jsonify(data)


@current_app.route('/edit_feedback', methods=['POST'])
def edit_feedback():
    data = request.json
    if 'id' not in data:
        return jsonify({'error': 'No feedback id given'}), 400
    elif not isinstance(data['id'], int):
        return jsonify({'error': 'Feedback id is not an int'}), 400
    elif not {'editor_id', 'id', 'nl', 'system_lin', 'correct_lin',
              'model'}.issuperset(data.keys()):
        return jsonify({'error': 'Illegal keys given'}), 400

    id = data.pop('id')
    feedback = Feedback.query.get(id)
    if not feedback:
        return jsonify(
            {'error': 'Feedback not found: {}'.format(id)}
        ), 404

    editor_id = data.pop('editor_id', None)
    if editor_id and editor_id != feedback.user_id:
        return jsonify({'error': 'Forbidden'}), 403

    for key, value in data.items():
        if value is not None:
            setattr(feedback, key, value)

    db.session.commit()
    return jsonify(feedback.json_ready_dict())


@current_app.route('/delete_feedback', methods=['POST'])
def delete_feedback():
    data = request.json
    if data is None:
        return jsonify({'error': 'No JSON payload given'}), 400
    elif 'id' not in data:
        return jsonify({'error': 'No feedback id given'}), 400
    elif not isinstance(data['id'], int):
        return jsonify({'error': 'Feedback id is not an int'}), 400
    elif not {'editor_id', 'id'}.issuperset(data.keys()):
        return jsonify({'error': 'Illegal keys given'}), 400

    id = data.pop('id')
    feedback = Feedback.query.get(id)
    if not feedback:
        return jsonify(
            {'error': 'Feedback not found: {}'.format(id)}
        ), 404

    editor_id = data.pop('editor_id', None)
    if editor_id and editor_id != feedback.user_id:
        return jsonify({'error': 'Forbidden'}), 403

    db.session.delete(feedback)
    db.session.commit()

    return jsonify({'success': True})


@current_app.route('/get_feedback', methods=['POST'])
def get_feedback():
    data = request.json
    if 'id' not in data:
        return jsonify({'error': 'No feedback id given'}), 400
    elif not isinstance(data['id'], int):
        return jsonify({'error': 'Feedback id is not an int'}), 400
    elif not {'querier_id', 'id'}.issuperset(data.keys()):
        return jsonify({'error': 'Illegal keys given'}), 400

    id = data.pop('id')
    feedback = Feedback.query.get(id)
    if not feedback:
        return jsonify(
            {'error': 'Feedback not found: {}'.format(id)}
        ), 404

    querier_id = data.pop('querier_id', None)
    if querier_id and querier_id != feedback.user_id:
        return jsonify({'error': 'Forbidden'}), 403

    return jsonify(feedback.json_ready_dict())


@current_app.route('/feedback_users', methods=['POST'])
def feedback_users():
    user_ids = list({fb.user_id for fb in Feedback.query.all() if fb.user_id})
    return jsonify(user_ids)
