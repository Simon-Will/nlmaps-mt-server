from flask import current_app, jsonify, request

from joeynmt_server.joey_model import JoeyModel
from joeynmt_server.models import Parse

MODELS = {}


@current_app.route('/translate', methods=['POST'])
def translate():
    data = request.json
    config_basename = data.get('model')
    nl = data.get('nl')

    joey_dir = current_app.config.get('JOEY_DIR')
    config_file = joey_dir / 'configs' / config_basename
    use_cuda = current_app.config.get('USE_CUDA_TRANSLATE')

    if config_basename in MODELS:
        model = MODELS[config_basename]
    else:
        model = JoeyModel.from_config_file(config_file, joey_dir,
                                           use_cuda=use_cuda)
        MODELS[config_basename] = model

    lin = model.translate_single(nl)
    Parse.get_or_create(nl=nl, model=config_basename, lin=lin)

    response = {'lin': lin}
    return jsonify(response)
