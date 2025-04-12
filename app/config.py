import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'you-will-never-guess'
    FIRECRAWL_API_KEY = os.environ.get('FIRECRAWL_API_KEY') or ''
    FIRECRAWL_BASE_URL = 'https://api.firecrawl.dev'
    