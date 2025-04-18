from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate

# Initialize SQLAlchemy without binding to a specific Flask app
db = SQLAlchemy()
migrate = Migrate()


def create_app(config_class=None):
    """Create and configure the Flask application"""
    app = Flask(__name__)

    # Load configuration
    if config_class:
        app.config.from_object(config_class)
    else:
        # Import here to avoid circular imports
        from config import get_config

        app.config.from_object(get_config())

    # Initialize extensions with the app
    db.init_app(app)
    migrate.init_app(app, db)

    # Register blueprints
    from app.routes.stashpoints import bp as stashpoints_bp

    app.register_blueprint(stashpoints_bp, url_prefix="/api/v1/stashpoints")

    @app.route("/healthcheck")
    def healthcheck():
        return {"status": "healthy"}

    return app
