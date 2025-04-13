from app.config import Config

class TestConfig(Config):
    TESTING = True
    WTF_CSRF_ENABLED = False
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'  # Use in-memory SQLite for testing
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret-key'
    FIRECRAWL_API_KEY = 'fc-c9b26ff85a964f1aaf8ae70aab2ba002'
    FIRECRAWL_BASE_URL = 'https://api.firecrawl.dev'