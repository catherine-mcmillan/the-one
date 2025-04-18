import os
from flask import Flask
from app.config import get_config
from app.extensions import init_extensions, db, login_manager
from app.routes import register_blueprints
from config import Config
from app.models.user import User

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

    # Initialize all extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)

    # Create database tables
    with app.app_context():
        # Ensure database directory exists
        db_dir = os.path.dirname(app.config['SQLITE_DB'])
        if not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            os.chmod(db_dir, 0o777)
        
        # Create tables
        db.create_all()

    return app