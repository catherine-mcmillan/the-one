from app.extensions import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import re
from email_validator import validate_email, EmailNotValidError
from app.models.search import UserSearchHistory

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(128))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    failed_login_attempts = db.Column(db.Integer, default=0)
    last_failed_login = db.Column(db.DateTime)
    is_admin = db.Column(db.Boolean, default=False)
    
    # Relationship with search history
    search_history = db.relationship('UserSearchHistory', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    @staticmethod
    def validate_username(username):
        """Validate username format"""
        if not 3 <= len(username) <= 64:
            return False, "Username must be between 3 and 64 characters."
        if not re.match(r'^[a-zA-Z0-9_.-]+$', username):
            return False, "Username can only contain letters, numbers, dots, dashes, and underscores."
        return True, "Username is valid."
    
    @staticmethod
    def validate_email(email):
        """Validate email format"""
        try:
            validate_email(email)
            return True, "Email is valid."
        except EmailNotValidError as e:
            return False, str(e)
    
    @staticmethod
    def validate_password(password):
        """Validate password strength"""
        if len(password) < 8:
            return False, "Password must be at least 8 characters long."
        if not re.search(r'[A-Z]', password):
            return False, "Password must contain at least one uppercase letter."
        if not re.search(r'[a-z]', password):
            return False, "Password must contain at least one lowercase letter."
        if not re.search(r'[0-9]', password):
            return False, "Password must contain at least one number."
        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            return False, "Password must contain at least one special character."
        return True, "Password meets requirements."
    
    def set_password(self, password):
        """Set password with validation"""
        if len(password) < 8:
            raise ValueError('Password must be at least 8 characters long')
        if not any(c.isupper() for c in password):
            raise ValueError('Password must contain at least one uppercase letter')
        if not any(c.islower() for c in password):
            raise ValueError('Password must contain at least one lowercase letter')
        if not any(c.isdigit() for c in password):
            raise ValueError('Password must contain at least one number')
        if not any(c in '!@#$%^&*()_+-=[]{}|;:,.<>?' for c in password):
            raise ValueError('Password must contain at least one special character')
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def record_failed_login(self):
        """Record failed login attempt"""
        self.failed_login_attempts = (self.failed_login_attempts or 0) + 1
        self.last_failed_login = datetime.utcnow()
        db.session.commit()
    
    def reset_failed_logins(self):
        """Reset failed login attempts"""
        self.failed_login_attempts = 0
        self.last_failed_login = None
        db.session.commit()
    
    @property
    def is_locked_out(self):
        """Check if user is locked out due to too many failed attempts"""
        if not self.last_failed_login or not self.failed_login_attempts:
            return False
        
        lockout_duration = datetime.utcnow() - self.last_failed_login
        return (self.failed_login_attempts >= 5 and 
                lockout_duration.total_seconds() < 300)  # 5 minutes lockout
    
    @property
    def total_searches(self):
        return self.search_history.count()
    
    @property
    def recent_searches(self):
        return self.search_history.order_by(UserSearchHistory.created_at.desc()).limit(5).all()
    
    def update_last_login(self):
        self.last_login = datetime.utcnow()
        self.reset_failed_logins()
        db.session.commit() 