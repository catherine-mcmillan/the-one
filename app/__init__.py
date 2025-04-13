import os
from flask import Flask
from app.config import get_config
from app.extensions import init_extensions, db
from app.routes import register_blueprints

def create_app(config_class=None):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    
    # Load configuration
    if config_class is None:
        config_class = get_config()
    elif isinstance(config_class, str):
        # Handle string config names
        from app.config import config_map
        config_class = config_map.get(config_class, get_config())
    
    app.config.from_object(config_class)

    # Initialize extensions
    init_extensions(app)

    # Register blueprints
    register_blueprints(app)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app