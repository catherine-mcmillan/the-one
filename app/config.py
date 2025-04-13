import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Base configuration class"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key-not-secure'
    FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY')
    FIRECRAWL_BASE_URL = os.environ.get('FIRECRAWL_BASE_URL') or 'https://api.firecrawl.dev'
    
    # Free tier limit is 100 requests per day
    FIRECRAWL_DAILY_LIMIT = int(os.environ.get('FIRECRAWL_DAILY_LIMIT') or 100)
    
    # Cache configuration
    CACHE_TYPE = os.environ.get('CACHE_TYPE') or 'simple'
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT') or 86400)  # 24 hours
    
    # Redis cache settings (if used)
    CACHE_REDIS_HOST = os.environ.get('REDIS_HOST') or 'localhost'
    CACHE_REDIS_PORT = int(os.environ.get('REDIS_PORT') or 6379)
    
    # Session settings
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Database settings
    SQLITE_DB = os.environ.get('SQLITE_DB') or 'app.db'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or f'sqlite:///{SQLITE_DB}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL') or 'INFO'

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    
    # Lower cache timeout for development
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Use a test database
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Mock API key for testing
    FIRECRAWL_API_KEY = 'test-api-key'

class ProductionConfig(Config):
    """Production configuration"""
    # Ensure these are set in production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY')
    
    # Use Redis cache in production
    CACHE_TYPE = 'redis'
    
    # Use more secure session
    SESSION_TYPE = 'redis'
    
    # Configure according to your plan
    if os.environ.get('FIRECRAWL_PLAN') == 'PRO':
        FIRECRAWL_DAILY_LIMIT = 1000
    elif os.environ.get('FIRECRAWL_PLAN') == 'BUSINESS':
        FIRECRAWL_DAILY_LIMIT = 10000
    else:
        # Free tier
        FIRECRAWL_DAILY_LIMIT = 100

# Configure based on environment
config_map = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

def get_config():
    """Get the configuration based on the environment"""
    env = os.environ.get('FLASK_ENV') or 'default'
    return config_map.get(env, config_map['default'])