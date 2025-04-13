from datetime import datetime
from app.extensions import db
from dataclasses import dataclass
from typing import List, Optional

class SearchCache(db.Model):
    """Model for caching search results"""
    id = db.Column(db.Integer, primary_key=True)
    query_hash = db.Column(db.String(64), unique=True, nullable=False, index=True)
    website = db.Column(db.String(256), nullable=False)
    search_query = db.Column(db.String(512), nullable=False)
    ranking_type = db.Column(db.String(32), nullable=False)
    results = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)

    def __repr__(self):
        return f'<SearchCache {self.website}:{self.search_query}>'

class UserSearchHistory(db.Model):
    """Model for storing user search history"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    website = db.Column(db.String(256), nullable=False)
    search_query = db.Column(db.String(512), nullable=False)
    ranking_type = db.Column(db.String(32), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<UserSearchHistory {self.website}:{self.search_query}>'

@dataclass
class SearchResult:
    """Data class for search results"""
    title: str
    url: str
    rating: Optional[float] = None
    image_url: Optional[str] = None
    summary: Optional[str] = None
    pros: List[str] = None
    cons: List[str] = None
    tips: List[str] = None
    
    def __post_init__(self):
        if self.pros is None:
            self.pros = []
        if self.cons is None:
            self.cons = []
        if self.tips is None:
            self.tips = []

    def to_dict(self):
        """Convert the search result to a dictionary"""
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

    @classmethod
    def from_dict(cls, data):
        """Create a SearchResult instance from a dictionary"""
        return cls(
            title=data.get('title'),
            url=data.get('url'),
            rating=data.get('rating'),
            image_url=data.get('image_url'),
            summary=data.get('summary'),
            pros=data.get('pros', []),
            cons=data.get('cons', []),
            tips=data.get('tips', [])
        )