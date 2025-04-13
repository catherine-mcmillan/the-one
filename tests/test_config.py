import pytest
import os
from app.config import Config, DevelopmentConfig, TestingConfig, ProductionConfig, get_config

def test_base_config():
    """Test base configuration."""
    config = Config()
    assert config.SECRET_KEY is not None
    assert isinstance(config.SECRET_KEY, str)
    assert len(config.SECRET_KEY) > 0
    assert config.FIRECRAWL_BASE_URL == 'https://api.firecrawl.dev'
    assert config.FIRECRAWL_DAILY_LIMIT == 100
    assert config.CACHE_TYPE == 'simple'
    assert config.CACHE_DEFAULT_TIMEOUT == 86400
    assert config.CACHE_REDIS_HOST == 'localhost'
    assert config.CACHE_REDIS_PORT == 6379
    assert config.SESSION_TYPE == 'filesystem'
    assert config.SQLALCHEMY_DATABASE_URI == 'sqlite:///app.db'
    assert not config.SQLALCHEMY_TRACK_MODIFICATIONS
    assert config.LOG_LEVEL == 'INFO'

def test_development_config():
    """Test development configuration."""
    config = DevelopmentConfig()
    assert config.DEBUG
    assert config.LOG_LEVEL == 'DEBUG'
    assert config.CACHE_DEFAULT_TIMEOUT == 300

def test_testing_config():
    """Test testing configuration."""
    config = TestingConfig()
    assert config.TESTING
    assert config.DEBUG
    assert config.SQLALCHEMY_DATABASE_URI == 'sqlite:///:memory:'
    assert not config.WTF_CSRF_ENABLED
    assert config.FIRECRAWL_API_KEY == 'test-api-key'

def test_production_config():
    """Test production configuration."""
    # Test with environment variables
    os.environ['SECRET_KEY'] = 'production-secret-key'
    os.environ['FIRECRAWL_API_KEY'] = 'production-api-key'
    os.environ['FIRECRAWL_PLAN'] = 'PRO'
    
    config = ProductionConfig()
    assert config.SECRET_KEY == 'production-secret-key'
    assert config.FIRECRAWL_API_KEY == 'production-api-key'
    assert config.FIRECRAWL_PLAN == 'PRO'
    assert config.CACHE_TYPE == 'redis'
    assert config.SESSION_TYPE == 'redis'
    assert config.FIRECRAWL_DAILY_LIMIT == 1000
    
    # Test with business plan
    os.environ['FIRECRAWL_PLAN'] = 'BUSINESS'
    config = ProductionConfig()
    assert config.FIRECRAWL_DAILY_LIMIT == 10000
    
    # Test with free plan
    os.environ['FIRECRAWL_PLAN'] = 'FREE'
    config = ProductionConfig()
    assert config.FIRECRAWL_DAILY_LIMIT == 100
    
    # Clean up environment variables
    del os.environ['SECRET_KEY']
    del os.environ['FIRECRAWL_API_KEY']
    del os.environ['FIRECRAWL_PLAN']

def test_get_config():
    """Test get_config function."""
    # Test default configuration
    config = get_config()
    assert isinstance(config, DevelopmentConfig)
    
    # Test development configuration
    os.environ['FLASK_ENV'] = 'development'
    assert isinstance(get_config(), DevelopmentConfig)
    
    # Test testing configuration
    os.environ['FLASK_ENV'] = 'testing'
    assert isinstance(get_config(), TestingConfig)
    
    # Test production configuration
    os.environ['FLASK_ENV'] = 'production'
    assert isinstance(get_config(), ProductionConfig)
    
    # Test invalid configuration
    os.environ['FLASK_ENV'] = 'invalid'
    assert isinstance(get_config(), DevelopmentConfig)
    
    # Clean up environment variable
    del os.environ['FLASK_ENV'] 