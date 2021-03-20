import os
import sys

from flask import Flask
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
migrate = Migrate()


def create_app() -> Flask:
    app = Flask(__name__)
    config_app(app)
    init_sqlalchemy(app)
    init_migrate(app)
    init_views(app)
    import_models()

    return app


def config_app(app: Flask) -> Flask:
    app.logger.info('Start loading config.')
    app.logger.info('Flask App configured.')

    app.logger.info('Loading default configuration.')
    app.config.from_object('joeynmt_server.config.default')
    env = os.environ.get('FLASK_ENV')
    if env:
        try:
            app.logger.info('Loading {} configuration.'.format(env))
            app.config.from_object('joeynmt_server.config.' + env.lower())
        except ImportError:
            app.logger.error('Could not load {} configuration.'.format(env))
            sys.exit(1)

    app.logger.info('Config loaded.')
    app.logger.debug(f'{app.config}')


def init_sqlalchemy(app: Flask) -> None:
    app.logger.info('Start initializing Flask-SQLAlchemy.')
    db.init_app(app=app)
    app.logger.info('Flask-SQLAlchemy initialized.')


def init_migrate(app: Flask) -> None:
    app.logger.info("Start initializing Flask-Migrate.")
    migrate.init_app(app=app, db=db)
    app.logger.info("Flask-Migrate initialized.")


def init_views(app: Flask) -> None:
    app.logger.info('Start initializing views.')

    with app.app_context():
        from joeynmt_server import views

        imported = [v for v in views.__dict__ if not v.startswith('_')]

        app.logger.info('Views initialized.')


def import_models() -> None:
    import joeynmt_server.models
