from flask import render_template, current_app
from app.errors import bp
from app.services.firecrawl_service import RateLimitExceeded, FirecrawlAPIManager
from datetime import datetime, timedelta

@bp.app_errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@bp.app_errorhandler(500)
def internal_error(error):
    return render_template('errors/500.html'), 500

@bp.app_errorhandler(RateLimitExceeded)
def rate_limit_error(error):
    api_manager = FirecrawlAPIManager()
    return render_template('errors/rate_limit.html',
                         reset_time=api_manager.daily_reset_time), 429

@bp.app_errorhandler(403)
def forbidden_error(error):
    return render_template('errors/403.html'), 403 