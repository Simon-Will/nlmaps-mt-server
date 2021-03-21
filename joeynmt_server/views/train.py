import logging
import threading
import time
import traceback

from flask import current_app, jsonify, request

from joeynmt_server.app import create_app
from joeynmt_server.models import Lock
from joeynmt_server.trainer import train_n_rounds, validate
from joeynmt_server.utils.helper import get_utc_now


@current_app.route('/train', methods=['POST'])
def train():
    data = request.json
    config_basename = data.get('model')
    rounds = data.get('rounds', 10)

    def train_in_thread():
        app = create_app()
        with app.app_context():
            try:
                train_n_rounds(config_basename, rounds)
            except:
                logging.error('Training failed.')
                logging.error(traceback.format_exc())

    thread = threading.Thread(target=train_in_thread)
    thread.start()

    time.sleep(0.1)
    response = {'training': thread.is_alive()}
    status = 200 if response['training'] else 500
    return jsonify(response), status


@current_app.route('/train_status', methods=['GET'])
def check_train_status():
    lock = Lock.query.filter_by(name='train').first()
    if lock:
        considered_expired_timespan = 60 * 60 * 6
        now = get_utc_now(aware=False)
        if (now - lock.created).total_seconds() < considered_expired_timespan:
            still_training = True
        else:
            still_training = False
    else:
        still_training = False

    return jsonify({'still_training': still_training})


@current_app.route('/validate', methods=['POST'])
def validate():
    data = request.json
    config_basename = data.get('model')

    def validate_in_thread():
        app = create_app()
        with app.app_context():
            try:
                validate(config_basename)
            except:
                logging.error('Training failed.')
                logging.error(traceback.format_exc())

    thread = threading.Thread(target=validate_in_thread)
    thread.start()

    time.sleep(0.1)
    response = {'validating': thread.is_alive()}
    status = 200 if response['validating'] else 500
    return jsonify(response), status

