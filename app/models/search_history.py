from datetime import datetime
from app import db
import json

class SearchCache(db.Model):
    """Model for caching search results to avoid duplicate API calls"""
    id = db.Column(db.Integer, primary_key=True)
    query = db.Column(db.String(500), nullable=False)
    website = db.Column(db.String(255), nullable=False)
    results = db.Column(db.Text, nullable=False)  # JSON stored as text
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
    
    @property
    def is_expired(self):
        return datetime.utcnow() > self.expires_at
    
    def get_results(self):
        return json.loads(self.results)
    
    @staticmethod
    def cache_key(website, query):
        return f"{website}:{query}"

class UserSearchHistory(db.Model):
    """Model for storing user's search history"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    search_query = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)  # Optional user notes about the search
    
    def __repr__(self):
        return f'<UserSearchHistory {self.search_query}>'
    
    def get_results(self):
        return json.loads(self.results)
    
    @property
    def formatted_date(self):
        return self.created_at.strftime('%Y-%m-%d %H:%M:%S') 