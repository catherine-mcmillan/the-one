import os
from datetime import timedelta

class TestConfig:
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite://'  # Use in-memory database for testing
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret-key'
    
    # Firecrawl API settings
    FIRECRAWL_API_KEY = 'test-api-key'
    FIRECRAWL_BASE_URL = 'https://api.firecrawl.com'
    FIRECRAWL_DAILY_LIMIT = 100
    
    # Cache settings
    CACHE_TYPE = 'simple'
    CACHE_DEFAULT_TIMEOUT = 300  # 5 minutes for testing
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    
    # Development mode settings
    DEV_MODE = True
    MAX_RESULTS_DEV = 2
    USE_SMALLER_MODEL = True