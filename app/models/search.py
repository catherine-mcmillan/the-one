from datetime import datetime

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