"""Blueprint registration for the application."""
from flask import Flask

def register_blueprints(app: Flask) -> None:
    """Register all blueprints with the Flask application.
    
    Args:
        app: The Flask application instance
    """
    from app.main import bp as main_bp
    from app.auth import bp as auth_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth') 