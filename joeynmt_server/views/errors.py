import traceback

from flask import current_app, jsonify, render_template, request


@current_app.errorhandler(403)
def page_forbidden(e):
    current_app.logger.warning('Error 403. URL {}. {}'
                               .format(request.url, e))
    return jsonify({'error': 'Forbidden'}), 403


@current_app.errorhandler(404)
def page_not_found(e):
    current_app.logger.warning('Error 404. URL {}. {}'
                               .format(request.url, e))
    return jsonify({'error': 'Not Found'}), 404


@current_app.errorhandler(Exception)
def internal_server_error(e):
    trace = traceback.format_exc()
    current_app.logger.error(
        'Error 500. URL {}. {}'
        .format(request.url, trace)
    )
    return jsonify({'error': 'Internal Server Error'}), 500
