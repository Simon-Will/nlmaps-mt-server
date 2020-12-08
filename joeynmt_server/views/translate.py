from flask import current_app, jsonify, request

from joeynmt_server.joey_model import JoeyModel

MODELS = {}


@current_app.route('/translate', methods=['POST'])
def translate():
    data = request.json
    config_file = data.get('model')
    nl_query = data.get('nl_query')

    # TODO: Check config_file, nl_query and joey_dir

    if config_file in MODELS:
        model = MODELS[config_file]
    else:
        joey_dir = current_app.config.get('JOEY_DIR')
        model = JoeyModel.from_config_file(config_file, joey_dir)
        MODELS[config_file] = model

    lin = model.translate_single(nl_query)
    response = {'lin': lin}

    return jsonify(response)
