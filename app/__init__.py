import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_caching import Cache
from app.config import get_config
from app.extensions import init_extensions, db
from app.routes import register_blueprints
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
cache = Cache()

def create_app(config_class=Config):
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
    db.init_app(app)
    login_manager.init_app(app)
    
    # Configure cache
    app.config['CACHE_TYPE'] = 'simple'  # Use 'redis' in production
    app.config['CACHE_DEFAULT_TIMEOUT'] = 86400  # 24 hours
    cache.init_app(app)

    # Register blueprints
    register_blueprints(app)

    # Create database tables
    with app.app_context():
        db.create_all()

    return app