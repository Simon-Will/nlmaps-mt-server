import logging
import threading
import time
import traceback

from flask import current_app, jsonify, request

from joeynmt_server.app import create_app
from joeynmt_server.models import EvaluationResult
from joeynmt_server.trainer import validate as validate_on_data


@current_app.route('/validate', methods=['POST'])
def validate():
    data = request.json
    if 'model' in data:
        config_basename = data['model']
    else:
        return jsonify({'error': 'No model specified.'}), 400

    dataset = data.get('dataset', 'dev')

    def validate_in_thread():
        app = create_app()
        with app.app_context():
            try:
                validate_on_data(config_basename, dataset)
            except:
                logging.error('Training failed.')
                logging.error(traceback.format_exc())

    thread = threading.Thread(target=validate_in_thread)
    thread.start()

    time.sleep(0.1)
    response = {'validating': thread.is_alive()}
    status = 200 if response['validating'] else 500
    return jsonify(response), status


@current_app.route('/validations', methods=['GET'])
def validations():
    label = request.args.get('label')
    model = request.args.get('model')

    query = EvaluationResult.query
    if label:
        query = query.filter_by(label=label)
    if model:
        query = query.filter_by(model=model)

    results = [result.json_ready_dict() for result in query]
    return jsonify(results)
