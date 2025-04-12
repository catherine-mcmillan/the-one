import os
from dotenv import load_dotenv
import secrets

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or secrets.token_hex(16)
    FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY') or ''
    FIRECRAWL_BASE_URL = 'https://api.firecrawl.dev'
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = 1800  # 30 minutes