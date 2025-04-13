from flask_login import LoginManager
from app.extensions import db

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

def init_login_manager(app):
    """Initialize login manager with the app."""
    login_manager.init_app(app)
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID."""
        if user_id is None:
            return None
        from app.models.user import User
        return User.query.get(int(user_id)) 