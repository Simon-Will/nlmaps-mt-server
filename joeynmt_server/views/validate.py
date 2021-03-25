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
    config_basename = data.get('model')

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

    if label:
        results = EvaluationResult.query.filter_by(label=label).all()
    else:
        results = EvaluationResult.query.all()

    results = [result.json_ready_dict() for result in results]
    return jsonify(results)
