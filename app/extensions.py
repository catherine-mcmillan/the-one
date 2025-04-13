from flask_sqlalchemy import SQLAlchemy
from flask_caching import Cache
from flask_migrate import Migrate
from flask_login import LoginManager

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
cache = Cache(config={'CACHE_TYPE': 'simple'})
login_manager = LoginManager()

def init_extensions(app):
    """Initialize Flask extensions."""
    # Initialize SQLAlchemy first
    db.init_app(app)
    
    # Initialize cache
    cache.init_app(app)
    
    # Initialize migrate after db
    migrate.init_app(app, db)
    
    # Initialize login manager
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID."""
        if user_id is None:
            return None
        from app.models.user import User
        return User.query.get(int(user_id)) 