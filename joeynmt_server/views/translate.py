from flask import current_app, jsonify, request
from joeynmt.helpers import get_latest_checkpoint

from joeynmt_server.joey_model import JoeyModel
from joeynmt_server.models import Feedback, Parse

MODELS = {}


def get_model(config_basename):
    joey_dir = current_app.config.get('JOEY_DIR')
    config_file = joey_dir / 'configs' / config_basename
    use_cuda = current_app.config.get('USE_CUDA_TRANSLATE')

    if config_basename in MODELS:
        model = MODELS[config_basename]

        # Only use the model if the checkpoint that was loaded still is the
        # latest available checkpoint. Otherwise load it again.
        if model.is_still_latest():
            return model

    model = JoeyModel.from_config_file(config_file, joey_dir,
                                       use_cuda=use_cuda)
    MODELS[config_basename] = model
    return model


@current_app.route('/translate', methods=['POST'])
def translate():
    data = request.json
    config_basename = data.get('model')
    nl = data.get('nl')

    model = get_model(config_basename)

    if isinstance(nl, str):
        lin = model.translate_single(nl)
        Parse.ensure(nl=nl, model=config_basename, lin=lin)
    elif isinstance(nl, list):
        lin = model.translate(nl)
        for single_nl, single_lin in zip(nl, lin):
            Parse.ensure(nl=single_nl, model=config_basename,
                         lin=single_lin)

    response = {'lin': lin}
    return jsonify(response)


@current_app.route('translate_all_feedback', methods=['POST'])
def translate_all():
    data = request.json
    config_basename = data.get('model')

    model = get_model(config_basename)

    nl = [fb.nl for fb in Feedback.query.all()]

    if isinstance(nl, list):
        lin = model.translate(nl)
        for single_nl, single_lin in zip(nl, lin):
            Parse.ensure(nl=single_nl, model=config_basename,
                         lin=single_lin)

    response = {'lin': lin}
    return jsonify(response)
