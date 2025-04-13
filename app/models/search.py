from datetime import datetime
from app.extensions import db

class UserSearchHistory(db.Model):
    """Model for storing user search history"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    website = db.Column(db.String(255), nullable=False)
    search_query = db.Column(db.String(255), nullable=False)
    ranking_type = db.Column(db.String(50), default='relevance')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<UserSearchHistory {self.search_query} on {self.website}>'

class SearchResult:
    """Model for search results"""
    
    def __init__(self, title, url, rating=None, image_url=None, summary=None, pros=None, cons=None, tips=None):
        self.title = title
        self.url = url
        self.rating = rating
        self.image_url = image_url
        self.summary = summary
        self.pros = pros or []
        self.cons = cons or []
        self.tips = tips or []
        
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'title': self.title,
            'url': self.url,
            'rating': self.rating,
            'image_url': self.image_url,
            'summary': self.summary,
            'pros': self.pros,
            'cons': self.cons,
            'tips': self.tips
        }